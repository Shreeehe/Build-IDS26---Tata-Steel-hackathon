"""
Enhanced Weight Analyzer with proper weight management.
Tracks initial weight, packaging weight, and smart thresholds.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.geofences import is_in_authorized_zone


@dataclass
class WeightProfile:
    """Weight profile for a truck at trip start."""
    truck_id: str
    total_weight_kg: float
    packaging_weight_kg: float  # Tarp, straps, etc.
    actual_cargo_kg: float
    timestamp: datetime
    destination: str = ""
    
    @property
    def cargo_weight(self) -> float:
        return self.total_weight_kg - self.packaging_weight_kg


@dataclass
class WeightAlert:
    """Represents a weight anomaly alert."""
    truck_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    previous_weight_kg: float
    current_weight_kg: float
    weight_drop_kg: float
    is_in_authorized_zone: bool
    zone_name: Optional[str]
    is_suspicious: bool
    severity: str
    reason: str


class EnhancedWeightAnalyzer:
    """
    Enhanced weight analyzer with:
    - Initial weight tagging with date
    - Packaging weight accounting
    - Smart threshold logic
    - Noise tolerance
    """
    
    # Thresholds
    SENSOR_NOISE_KG = 10  # Normal sensor fluctuation
    ACCEPTABLE_LOSS_KG = 20  # Acceptable loss (vibration, settling)
    SUSPICIOUS_DROP_KG = 50  # Suspicious weight drop
    CRITICAL_DROP_KG = 200  # Critical theft indicator
    
    def __init__(self):
        self.weight_profiles: Dict[str, WeightProfile] = {}
        self.previous_weights: Dict[str, float] = {}
        self.weight_alerts: List[WeightAlert] = []
        self.total_detected_loss: Dict[str, float] = {}
    
    def register_trip(self, truck_id: str, total_weight: float, 
                      packaging_weight: float = 50.0, destination: str = "") -> WeightProfile:
        """
        Register a new trip with initial weight tagging.
        Called at trip start (factory/warehouse).
        """
        actual_cargo = total_weight - packaging_weight
        
        profile = WeightProfile(
            truck_id=truck_id,
            total_weight_kg=total_weight,
            packaging_weight_kg=packaging_weight,
            actual_cargo_kg=actual_cargo,
            timestamp=datetime.now(),
            destination=destination
        )
        
        self.weight_profiles[truck_id] = profile
        self.previous_weights[truck_id] = total_weight
        self.total_detected_loss[truck_id] = 0.0
        
        return profile
    
    def get_weight_status(self, truck_id: str, current_weight: float) -> dict:
        """Get current weight status compared to initial."""
        if truck_id not in self.weight_profiles:
            return {'status': 'unknown', 'message': 'Trip not registered'}
        
        profile = self.weight_profiles[truck_id]
        expected_weight = profile.total_weight_kg
        actual_cargo = profile.actual_cargo_kg
        
        weight_loss = expected_weight - current_weight
        cargo_remaining = actual_cargo - weight_loss
        cargo_percent = (cargo_remaining / actual_cargo) * 100 if actual_cargo > 0 else 100
        
        if weight_loss <= self.ACCEPTABLE_LOSS_KG:
            status = 'normal'
            message = 'Weight within acceptable range'
        elif weight_loss <= self.SUSPICIOUS_DROP_KG:
            status = 'warning'
            message = f'Minor weight loss: {weight_loss:.1f} kg'
        elif weight_loss <= self.CRITICAL_DROP_KG:
            status = 'alert'
            message = f'Suspicious weight loss: {weight_loss:.1f} kg'
        else:
            status = 'critical'
            message = f'CRITICAL weight loss: {weight_loss:.1f} kg'
        
        return {
            'status': status,
            'message': message,
            'initial_weight': expected_weight,
            'current_weight': current_weight,
            'weight_loss': weight_loss,
            'cargo_remaining_kg': cargo_remaining,
            'cargo_remaining_percent': cargo_percent,
            'packaging_weight': profile.packaging_weight_kg
        }
    
    def process_reading(self, reading: dict) -> Optional[WeightAlert]:
        """Process a weight reading and detect anomalies."""
        truck_id = reading['truck_id']
        timestamp = datetime.fromisoformat(reading['timestamp'])
        current_weight = reading['weight_kg']
        lat = reading['latitude']
        lon = reading['longitude']
        is_moving = reading['is_moving']
        
        # Auto-register if first reading
        if truck_id not in self.previous_weights:
            self.register_trip(truck_id, current_weight)
            return None
        
        previous_weight = self.previous_weights[truck_id]
        weight_change = current_weight - previous_weight
        
        # Update previous weight
        self.previous_weights[truck_id] = current_weight
        
        # Ignore small changes (sensor noise)
        if abs(weight_change) < self.SENSOR_NOISE_KG:
            return None
        
        # Only concerned with weight DROPS
        if weight_change >= 0:
            return None
        
        weight_drop = abs(weight_change)
        self.total_detected_loss[truck_id] = self.total_detected_loss.get(truck_id, 0) + weight_drop
        
        in_zone, zone = is_in_authorized_zone(lat, lon)
        
        # Determine severity based on location and amount
        is_suspicious = False
        severity = 'low'
        reason = ""
        
        # KEY SOP RULE: Weight drop outside authorized zone
        if not in_zone:
            if weight_drop >= self.CRITICAL_DROP_KG:
                is_suspicious = True
                severity = 'critical'
                reason = f"CRITICAL: {weight_drop:.1f}kg drop OUTSIDE authorized zone!"
            elif weight_drop >= self.SUSPICIOUS_DROP_KG:
                is_suspicious = True
                severity = 'high'
                reason = f"Suspicious: {weight_drop:.1f}kg drop outside authorized zone"
            else:
                severity = 'medium'
                reason = f"Minor drop: {weight_drop:.1f}kg outside zone (monitoring)"
        else:
            if zone and zone.zone_type == 'destination':
                severity = 'low'
                reason = f"Expected unloading at destination ({zone.name})"
            else:
                severity = 'medium'
                reason = f"Weight drop at {zone.name if zone else 'zone'} - verify"
        
        # Extra check: Weight drop while stopped outside zone
        if not is_moving and not in_zone and weight_drop >= self.SUSPICIOUS_DROP_KG:
            is_suspicious = True
            severity = 'critical'
            reason = f"THEFT ALERT: {weight_drop:.1f}kg drop while STOPPED outside zone!"
        
        alert = WeightAlert(
            truck_id=truck_id,
            timestamp=timestamp,
            latitude=lat,
            longitude=lon,
            previous_weight_kg=previous_weight,
            current_weight_kg=current_weight,
            weight_drop_kg=weight_drop,
            is_in_authorized_zone=in_zone,
            zone_name=zone.name if zone else None,
            is_suspicious=is_suspicious,
            severity=severity,
            reason=reason
        )
        
        self.weight_alerts.append(alert)
        return alert
    
    def get_trip_summary(self, truck_id: str) -> dict:
        """Get weight summary for a trip."""
        if truck_id not in self.weight_profiles:
            return {}
        
        profile = self.weight_profiles[truck_id]
        current = self.previous_weights.get(truck_id, profile.total_weight_kg)
        total_loss = self.total_detected_loss.get(truck_id, 0)
        
        return {
            'initial_total': profile.total_weight_kg,
            'packaging': profile.packaging_weight_kg,
            'initial_cargo': profile.actual_cargo_kg,
            'current_weight': current,
            'total_detected_loss': total_loss,
            'alerts_count': len([a for a in self.weight_alerts if a.truck_id == truck_id]),
            'suspicious_alerts': len([a for a in self.weight_alerts 
                                      if a.truck_id == truck_id and a.is_suspicious])
        }
