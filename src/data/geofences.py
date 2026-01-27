"""
Geofence definitions for authorized zones.
"""
from dataclasses import dataclass
from typing import List, Tuple
import math


@dataclass
class GeofenceZone:
    """Represents an authorized zone (rest stop, warehouse, etc.)"""
    name: str
    latitude: float
    longitude: float
    radius_km: float  # Radius in kilometers
    zone_type: str  # 'warehouse', 'rest_stop', 'checkpoint', 'destination'
    max_stop_duration_min: int = 60  # Max allowed stop duration in minutes


# Authorized zones for the route (Jamshedpur → Kolkata corridor)
AUTHORIZED_ZONES: List[GeofenceZone] = [
    GeofenceZone(
        name="Tata Steel Jamshedpur Plant",
        latitude=22.8046,
        longitude=86.2029,
        radius_km=2.0,
        zone_type="warehouse",
        max_stop_duration_min=120
    ),
    GeofenceZone(
        name="Kharagpur Rest Stop",
        latitude=22.3460,
        longitude=87.3236,
        radius_km=0.5,
        zone_type="rest_stop",
        max_stop_duration_min=30
    ),
    GeofenceZone(
        name="Kolaghat Checkpoint",
        latitude=22.4351,
        longitude=87.8863,
        radius_km=0.3,
        zone_type="checkpoint",
        max_stop_duration_min=15
    ),
    GeofenceZone(
        name="Howrah Distribution Center",
        latitude=22.5958,
        longitude=88.2636,
        radius_km=1.5,
        zone_type="destination",
        max_stop_duration_min=180
    ),
]


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers."""
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def is_in_authorized_zone(latitude: float, longitude: float) -> Tuple[bool, GeofenceZone | None]:
    """Check if a location is within any authorized zone."""
    for zone in AUTHORIZED_ZONES:
        distance = haversine_distance(latitude, longitude, zone.latitude, zone.longitude)
        if distance <= zone.radius_km:
            return True, zone
    return False, None


def get_max_stop_duration(latitude: float, longitude: float) -> int:
    """Get maximum allowed stop duration for a location (in minutes)."""
    is_authorized, zone = is_in_authorized_zone(latitude, longitude)
    if is_authorized and zone:
        return zone.max_stop_duration_min
    return 0  # No stop allowed outside authorized zones
