"""
Data simulator for GPS and weight sensor streams.
Generates realistic transit data with normal and pilferage scenarios.
"""
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Generator
import math

from .geofences import AUTHORIZED_ZONES, haversine_distance, is_in_authorized_zone


@dataclass
class GPSReading:
    """Single GPS reading from a truck."""
    truck_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    speed_kmh: float
    is_moving: bool


@dataclass
class WeightReading:
    """Single weight sensor reading."""
    truck_id: str
    timestamp: datetime
    weight_kg: float
    weight_change_kg: float  # Change from previous reading


@dataclass
class TruckState:
    """Current state of a truck."""
    truck_id: str
    latitude: float
    longitude: float
    speed_kmh: float
    weight_kg: float
    is_moving: bool
    stop_start_time: datetime | None = None
    last_update: datetime = field(default_factory=datetime.now)


class TransitSimulator:
    """Simulates truck transit from origin to destination."""
    
    # Route waypoints (Jamshedpur → Kolkata)
    ROUTE_WAYPOINTS = [
        (22.8046, 86.2029),  # Jamshedpur (start)
        (22.6500, 86.5000),  # En route
        (22.5000, 86.8000),  # En route
        (22.3460, 87.3236),  # Kharagpur (rest stop)
        (22.4000, 87.6000),  # En route
        (22.4351, 87.8863),  # Kolaghat (checkpoint)
        (22.5000, 88.0000),  # En route
        (22.5958, 88.2636),  # Howrah (destination)
    ]
    
    def __init__(self, truck_id: str = "TS-JH-1234", initial_weight_kg: float = 25000.0):
        self.truck_id = truck_id
        self.initial_weight = initial_weight_kg
        self.current_weight = initial_weight_kg
        self.waypoint_index = 0
        self.current_lat = self.ROUTE_WAYPOINTS[0][0]
        self.current_lon = self.ROUTE_WAYPOINTS[0][1]
        self.speed = 0.0
        self.is_moving = False
        self.stop_start = None
        self.events: List[dict] = []
        self.current_time = datetime.now()
        
    def _interpolate_position(self, progress: float) -> tuple[float, float]:
        """Interpolate position between waypoints."""
        if self.waypoint_index >= len(self.ROUTE_WAYPOINTS) - 1:
            return self.ROUTE_WAYPOINTS[-1]
        
        start = self.ROUTE_WAYPOINTS[self.waypoint_index]
        end = self.ROUTE_WAYPOINTS[self.waypoint_index + 1]
        
        lat = start[0] + (end[0] - start[0]) * progress
        lon = start[1] + (end[1] - start[1]) * progress
        return lat, lon
    
    def generate_normal_journey(self, duration_hours: float = 4.0) -> List[dict]:
        """Generate a normal journey without any pilferage."""
        events = []
        readings_per_hour = 60  # One reading per minute
        total_readings = int(duration_hours * readings_per_hour)
        
        for i in range(total_readings):
            self.current_time += timedelta(minutes=1)
            progress = i / total_readings
            
            # Move through waypoints
            self.waypoint_index = min(int(progress * (len(self.ROUTE_WAYPOINTS) - 1)), 
                                      len(self.ROUTE_WAYPOINTS) - 2)
            segment_progress = (progress * (len(self.ROUTE_WAYPOINTS) - 1)) % 1
            
            self.current_lat, self.current_lon = self._interpolate_position(segment_progress)
            
            # Check if at authorized stop
            in_zone, zone = is_in_authorized_zone(self.current_lat, self.current_lon)
            
            # Simulate stops at authorized zones
            if in_zone and zone and zone.zone_type in ['rest_stop', 'checkpoint']:
                self.speed = 0.0
                self.is_moving = False
            else:
                self.speed = random.uniform(40, 60)  # Normal highway speed
                self.is_moving = True
            
            # Weight stays constant (no pilferage)
            weight_change = random.uniform(-2, 2)  # Minor sensor noise
            
            events.append({
                'timestamp': self.current_time.isoformat(),
                'truck_id': self.truck_id,
                'latitude': round(self.current_lat, 6),
                'longitude': round(self.current_lon, 6),
                'speed_kmh': round(self.speed, 1),
                'is_moving': self.is_moving,
                'weight_kg': round(self.current_weight + weight_change, 1),
                'weight_change_kg': round(weight_change, 1),
                'in_authorized_zone': in_zone,
                'zone_name': zone.name if zone else None,
                'alert_level': 0,  # No alert
                'scenario': 'normal'
            })
        
        return events
    
    def generate_pilferage_scenario(self, 
                                    pilferage_at_progress: float = 0.5,
                                    weight_stolen_kg: float = 500.0,
                                    stop_duration_min: int = 20) -> List[dict]:
        """Generate a journey with a pilferage event."""
        events = []
        duration_hours = 4.0
        readings_per_hour = 60
        total_readings = int(duration_hours * readings_per_hour)
        pilferage_reading = int(pilferage_at_progress * total_readings)
        pilferage_end = pilferage_reading + stop_duration_min
        
        for i in range(total_readings):
            self.current_time += timedelta(minutes=1)
            progress = i / total_readings
            
            # Move through waypoints
            self.waypoint_index = min(int(progress * (len(self.ROUTE_WAYPOINTS) - 1)), 
                                      len(self.ROUTE_WAYPOINTS) - 2)
            segment_progress = (progress * (len(self.ROUTE_WAYPOINTS) - 1)) % 1
            
            self.current_lat, self.current_lon = self._interpolate_position(segment_progress)
            
            in_zone, zone = is_in_authorized_zone(self.current_lat, self.current_lon)
            
            # Pilferage scenario
            if pilferage_reading <= i < pilferage_end:
                self.speed = 0.0
                self.is_moving = False
                
                # Weight drops during pilferage
                if i == pilferage_reading + 5:  # Weight drops 5 min into stop
                    self.current_weight -= weight_stolen_kg
                    weight_change = -weight_stolen_kg
                else:
                    weight_change = random.uniform(-2, 2)
                
                events.append({
                    'timestamp': self.current_time.isoformat(),
                    'truck_id': self.truck_id,
                    'latitude': round(self.current_lat, 6),
                    'longitude': round(self.current_lon, 6),
                    'speed_kmh': 0.0,
                    'is_moving': False,
                    'weight_kg': round(self.current_weight + random.uniform(-2, 2), 1),
                    'weight_change_kg': round(weight_change, 1),
                    'in_authorized_zone': in_zone,
                    'zone_name': zone.name if zone else None,
                    'alert_level': 0,  # Will be calculated by engine
                    'scenario': 'pilferage',
                    'stop_duration_min': i - pilferage_reading + 1
                })
            else:
                # Normal movement
                if in_zone and zone and zone.zone_type in ['rest_stop', 'checkpoint']:
                    self.speed = 0.0
                    self.is_moving = False
                else:
                    self.speed = random.uniform(40, 60)
                    self.is_moving = True
                
                weight_change = random.uniform(-2, 2)
                
                events.append({
                    'timestamp': self.current_time.isoformat(),
                    'truck_id': self.truck_id,
                    'latitude': round(self.current_lat, 6),
                    'longitude': round(self.current_lon, 6),
                    'speed_kmh': round(self.speed, 1),
                    'is_moving': self.is_moving,
                    'weight_kg': round(self.current_weight + weight_change, 1),
                    'weight_change_kg': round(weight_change, 1),
                    'in_authorized_zone': in_zone,
                    'zone_name': zone.name if zone else None,
                    'alert_level': 0,
                    'scenario': 'pilferage' if i > pilferage_reading else 'normal'
                })
        
        return events


def generate_demo_data() -> List[dict]:
    """Generate demo data with both normal and pilferage scenarios."""
    all_events = []
    
    # Normal journey
    sim1 = TransitSimulator(truck_id="TS-JH-1001", initial_weight_kg=25000)
    all_events.extend(sim1.generate_normal_journey())
    
    # Pilferage scenario
    sim2 = TransitSimulator(truck_id="TS-JH-1002", initial_weight_kg=25000)
    all_events.extend(sim2.generate_pilferage_scenario(
        pilferage_at_progress=0.4,
        weight_stolen_kg=800,
        stop_duration_min=25
    ))
    
    return all_events


if __name__ == "__main__":
    import json
    events = generate_demo_data()
    print(json.dumps(events[:10], indent=2))
