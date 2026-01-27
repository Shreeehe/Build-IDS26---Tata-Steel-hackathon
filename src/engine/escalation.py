"""
Alert Escalation System - 4-level SOP-based alert escalation.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Dict, List, Optional, Callable
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.stop_analyzer import StopEvent
from engine.weight_analyzer import WeightAlert


class AlertLevel(IntEnum):
    """Alert escalation levels based on SOP."""
    NORMAL = 0
    WATCHLIST = 1  # L1: Log only
    WARNING = 2    # L2: SMS to driver, await confirmation
    CRITICAL = 3   # L3: Auto-call, alert control center
    EMERGENCY = 4  # L4: Security team, police, lock cargo


@dataclass
class Alert:
    """Unified alert object."""
    alert_id: str
    truck_id: str
    timestamp: datetime
    level: AlertLevel
    source: str  # 'stop_analyzer', 'weight_analyzer', 'combined'
    title: str
    description: str
    latitude: float
    longitude: float
    actions_taken: List[str] = field(default_factory=list)
    escalation_history: List[dict] = field(default_factory=list)
    is_resolved: bool = False
    resolution_time: Optional[datetime] = None
    resolution_notes: str = ""


class EscalationEngine:
    """
    SOP-based alert escalation system.
    
    Escalation Logic:
    - L1 (Watchlist): Minor anomalies, log only
    - L2 (Warning): Suspicious activity, SMS driver for confirmation
    - L3 (Critical): No response from driver OR confirmed threat, alert control center
    - L4 (Emergency): Confirmed theft, dispatch security
    """
    
    # Escalation timeouts
    L2_TIMEOUT_MIN = 5   # Wait 5 min for driver response
    L3_TIMEOUT_MIN = 3   # Wait 3 min before escalating to L4
    
    def __init__(self):
        self.active_alerts: Dict[str, Alert] = {}  # alert_id -> Alert
        self.alert_history: List[Alert] = []
        self.alert_counter = 0
        
        # Callbacks for actions (can be overridden)
        self.on_sms_driver: Optional[Callable] = None
        self.on_call_driver: Optional[Callable] = None
        self.on_alert_control_center: Optional[Callable] = None
        self.on_dispatch_security: Optional[Callable] = None
    
    def _generate_alert_id(self) -> str:
        """Generate unique alert ID."""
        self.alert_counter += 1
        return f"ALT-{datetime.now().strftime('%Y%m%d')}-{self.alert_counter:04d}"
    
    def process_stop_event(self, event: StopEvent) -> Optional[Alert]:
        """Process a stop event and generate appropriate alert."""
        if not event.is_suspicious:
            return None
        
        # Determine initial level based on stop characteristics
        if event.is_authorized:
            # Authorized zone but exceeded duration
            level = AlertLevel.WATCHLIST
            title = "Extended Stop at Authorized Location"
        else:
            # Unauthorized stop
            if event.duration_minutes >= 15:
                level = AlertLevel.WARNING
                title = "Suspicious Unauthorized Stop"
            else:
                level = AlertLevel.WATCHLIST
                title = "Unauthorized Stop Detected"
        
        alert = Alert(
            alert_id=self._generate_alert_id(),
            truck_id=event.truck_id,
            timestamp=event.start_time,
            level=level,
            source='stop_analyzer',
            title=title,
            description=event.reason,
            latitude=event.latitude,
            longitude=event.longitude,
            actions_taken=[]
        )
        
        self._execute_level_actions(alert)
        self.active_alerts[alert.alert_id] = alert
        return alert
    
    def process_weight_alert(self, weight_alert: WeightAlert) -> Optional[Alert]:
        """Process a weight alert and generate appropriate alert."""
        if not weight_alert.is_suspicious:
            return None
        
        # Determine level based on severity
        if weight_alert.severity == 'critical':
            level = AlertLevel.CRITICAL
            title = "CRITICAL: Potential Pilferage Detected"
        elif weight_alert.severity == 'high':
            level = AlertLevel.WARNING
            title = "Suspicious Weight Drop"
        else:
            level = AlertLevel.WATCHLIST
            title = "Weight Anomaly Detected"
        
        alert = Alert(
            alert_id=self._generate_alert_id(),
            truck_id=weight_alert.truck_id,
            timestamp=weight_alert.timestamp,
            level=level,
            source='weight_analyzer',
            title=title,
            description=weight_alert.reason,
            latitude=weight_alert.latitude,
            longitude=weight_alert.longitude,
            actions_taken=[]
        )
        
        self._execute_level_actions(alert)
        self.active_alerts[alert.alert_id] = alert
        return alert
    
    def process_combined_event(self, stop_event: StopEvent, weight_alert: WeightAlert) -> Alert:
        """
        Process combined stop + weight anomaly (SOP trigger condition).
        This is the KEY condition from the problem statement:
        "if a weight drop is detected outside a geofenced zone, trigger security protocol"
        """
        # This is the critical SOP condition - immediate L4 escalation
        level = AlertLevel.EMERGENCY
        
        alert = Alert(
            alert_id=self._generate_alert_id(),
            truck_id=stop_event.truck_id,
            timestamp=weight_alert.timestamp,
            level=level,
            source='combined',
            title="🚨 EMERGENCY: Weight Drop During Unauthorized Stop",
            description=(
                f"SOP TRIGGERED: Weight drop of {weight_alert.weight_drop_kg:.1f}kg "
                f"detected while truck stopped at unauthorized location for "
                f"{stop_event.duration_minutes:.1f} minutes. "
                f"Immediate security protocol initiated."
            ),
            latitude=stop_event.latitude,
            longitude=stop_event.longitude,
            actions_taken=[]
        )
        
        self._execute_level_actions(alert)
        self.active_alerts[alert.alert_id] = alert
        return alert
    
    def _execute_level_actions(self, alert: Alert):
        """Execute actions based on alert level."""
        actions = []
        
        if alert.level >= AlertLevel.WATCHLIST:
            actions.append("📋 Logged to system audit trail")
        
        if alert.level >= AlertLevel.WARNING:
            actions.append("📱 SMS sent to driver requesting confirmation")
            if self.on_sms_driver:
                self.on_sms_driver(alert)
        
        if alert.level >= AlertLevel.CRITICAL:
            actions.append("📞 Auto-call initiated to driver")
            actions.append("🏢 Control center notified")
            if self.on_call_driver:
                self.on_call_driver(alert)
            if self.on_alert_control_center:
                self.on_alert_control_center(alert)
        
        if alert.level >= AlertLevel.EMERGENCY:
            actions.append("🚔 Security team dispatched")
            actions.append("📍 Nearest police station notified")
            actions.append("🔒 Cargo lock signal sent (if available)")
            if self.on_dispatch_security:
                self.on_dispatch_security(alert)
        
        alert.actions_taken = actions
        alert.escalation_history.append({
            'timestamp': datetime.now().isoformat(),
            'level': alert.level.name,
            'actions': actions
        })
    
    def escalate_alert(self, alert_id: str, reason: str = "No response") -> Optional[Alert]:
        """Escalate an existing alert to the next level."""
        if alert_id not in self.active_alerts:
            return None
        
        alert = self.active_alerts[alert_id]
        
        if alert.level < AlertLevel.EMERGENCY:
            new_level = AlertLevel(alert.level + 1)
            alert.level = new_level
            alert.description += f" [ESCALATED: {reason}]"
            self._execute_level_actions(alert)
            return alert
        
        return alert
    
    def resolve_alert(self, alert_id: str, notes: str = "") -> Optional[Alert]:
        """Mark an alert as resolved."""
        if alert_id not in self.active_alerts:
            return None
        
        alert = self.active_alerts.pop(alert_id)
        alert.is_resolved = True
        alert.resolution_time = datetime.now()
        alert.resolution_notes = notes
        self.alert_history.append(alert)
        return alert
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all currently active alerts."""
        return list(self.active_alerts.values())
    
    def get_alerts_by_level(self, level: AlertLevel) -> List[Alert]:
        """Get all active alerts of a specific level."""
        return [a for a in self.active_alerts.values() if a.level == level]
    
    def get_alert_summary(self) -> dict:
        """Get summary of current alert status."""
        return {
            'total_active': len(self.active_alerts),
            'by_level': {
                'normal': len([a for a in self.active_alerts.values() if a.level == AlertLevel.NORMAL]),
                'watchlist': len([a for a in self.active_alerts.values() if a.level == AlertLevel.WATCHLIST]),
                'warning': len([a for a in self.active_alerts.values() if a.level == AlertLevel.WARNING]),
                'critical': len([a for a in self.active_alerts.values() if a.level == AlertLevel.CRITICAL]),
                'emergency': len([a for a in self.active_alerts.values() if a.level == AlertLevel.EMERGENCY]),
            },
            'total_resolved': len(self.alert_history)
        }
