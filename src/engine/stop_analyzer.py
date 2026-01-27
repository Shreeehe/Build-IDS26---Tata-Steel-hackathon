"""
Stop Analyzer - Detects suspicious stops vs authorized rest stops.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.geofences import is_in_authorized_zone, get_max_stop_duration


@dataclass
class StopEvent:
    """Represents a detected stop event."""
    truck_id: str
    start_time: datetime
    end_time: Optional[datetime]
    latitude: float
    longitude: float
    duration_minutes: float
    is_authorized: bool
    zone_name: Optional[str]
    is_suspicious: bool
    reason: str


class StopAnalyzer:
    """Analyzes truck stops to identify suspicious behavior."""
    
    # Thresholds
    MIN_STOP_DURATION_MIN = 3  # Minimum duration to consider as a stop (not just traffic)
    SUSPICIOUS_UNAUTHORIZED_STOP_MIN = 10  # Unauthorized stop > 10 min is suspicious
    
    def __init__(self):
        self.active_stops: Dict[str, dict] = {}  # truck_id -> stop info
        self.completed_stops: List[StopEvent] = []
    
    def process_reading(self, reading: dict) -> Optional[StopEvent]:
        """Process a single GPS/weight reading and detect stops."""
        truck_id = reading['truck_id']
        timestamp = datetime.fromisoformat(reading['timestamp'])
        is_moving = reading['is_moving']
        lat = reading['latitude']
        lon = reading['longitude']
        
        # Check if truck just stopped
        if not is_moving and truck_id not in self.active_stops:
            # Start tracking this stop
            in_zone, zone = is_in_authorized_zone(lat, lon)
            self.active_stops[truck_id] = {
                'start_time': timestamp,
                'latitude': lat,
                'longitude': lon,
                'in_authorized_zone': in_zone,
                'zone_name': zone.name if zone else None,
                'max_allowed_duration': zone.max_stop_duration_min if zone else 0
            }
            return None
        
        # Check if truck resumed movement (stop ended)
        elif is_moving and truck_id in self.active_stops:
            stop_info = self.active_stops.pop(truck_id)
            duration = (timestamp - stop_info['start_time']).total_seconds() / 60
            
            # Ignore very short stops (traffic, etc.)
            if duration < self.MIN_STOP_DURATION_MIN:
                return None
            
            # Determine if suspicious
            is_suspicious = False
            reason = ""
            
            if not stop_info['in_authorized_zone']:
                if duration >= self.SUSPICIOUS_UNAUTHORIZED_STOP_MIN:
                    is_suspicious = True
                    reason = f"Unauthorized stop of {duration:.1f} min (threshold: {self.SUSPICIOUS_UNAUTHORIZED_STOP_MIN} min)"
            else:
                if duration > stop_info['max_allowed_duration']:
                    is_suspicious = True
                    reason = f"Stop exceeded allowed duration: {duration:.1f} min > {stop_info['max_allowed_duration']} min"
            
            if not is_suspicious:
                if stop_info['in_authorized_zone']:
                    reason = f"Authorized stop at {stop_info['zone_name']}"
                else:
                    reason = f"Brief unauthorized stop ({duration:.1f} min < {self.SUSPICIOUS_UNAUTHORIZED_STOP_MIN} min)"
            
            stop_event = StopEvent(
                truck_id=truck_id,
                start_time=stop_info['start_time'],
                end_time=timestamp,
                latitude=stop_info['latitude'],
                longitude=stop_info['longitude'],
                duration_minutes=duration,
                is_authorized=stop_info['in_authorized_zone'],
                zone_name=stop_info['zone_name'],
                is_suspicious=is_suspicious,
                reason=reason
            )
            
            self.completed_stops.append(stop_event)
            return stop_event
        
        # Check ongoing stops for suspicious duration
        elif not is_moving and truck_id in self.active_stops:
            stop_info = self.active_stops[truck_id]
            duration = (timestamp - stop_info['start_time']).total_seconds() / 60
            
            # Check if unauthorized stop is becoming suspicious
            if not stop_info['in_authorized_zone'] and duration >= self.SUSPICIOUS_UNAUTHORIZED_STOP_MIN:
                # Return a warning (stop still ongoing)
                return StopEvent(
                    truck_id=truck_id,
                    start_time=stop_info['start_time'],
                    end_time=None,  # Still ongoing
                    latitude=stop_info['latitude'],
                    longitude=stop_info['longitude'],
                    duration_minutes=duration,
                    is_authorized=False,
                    zone_name=None,
                    is_suspicious=True,
                    reason=f"ONGOING: Unauthorized stop now at {duration:.1f} min"
                )
        
        return None
    
    def get_active_stops(self) -> Dict[str, dict]:
        """Get all currently active (ongoing) stops."""
        return self.active_stops
    
    def get_suspicious_stops(self) -> List[StopEvent]:
        """Get all suspicious stops detected so far."""
        return [s for s in self.completed_stops if s.is_suspicious]
