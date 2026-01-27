"""
Traffic and Historical Data Services
Simulated API responses for traffic status and theft history
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
import random


@dataclass
class TrafficStatus:
    """Traffic status from simulated API."""
    condition: str  # 'light', 'moderate', 'heavy', 'jam'
    delay_minutes: int
    reason: Optional[str]
    color: str  # For UI display
    icon: str


@dataclass 
class TheftRecord:
    """Historical theft record."""
    date: datetime
    location: str
    latitude: float
    longitude: float
    weight_stolen_kg: float
    value_inr: float
    recovered: bool
    description: str


class TrafficService:
    """Simulated Google Maps Traffic API."""
    
    # High-risk routes (theft hotspots)
    HIGH_RISK_ROUTES = [
        {"name": "NH6 Near Kharagpur", "lat": 22.35, "lon": 87.32, "risk_factor": 0.8},
        {"name": "Bypass Road Kolaghat", "lat": 22.43, "lon": 87.88, "risk_factor": 0.6},
        {"name": "Industrial Area Jamshedpur", "lat": 22.80, "lon": 86.20, "risk_factor": 0.4},
    ]
    
    def get_traffic_status(self, lat: float, lon: float) -> TrafficStatus:
        """Get traffic status for a location (simulated)."""
        # Simulate varying traffic conditions
        hour = datetime.now().hour
        
        # Rush hour simulation
        if 8 <= hour <= 10 or 17 <= hour <= 20:
            conditions = ['moderate', 'heavy', 'jam']
            weights = [0.3, 0.5, 0.2]
        elif 22 <= hour or hour <= 5:
            conditions = ['light', 'light', 'light']
            weights = [1.0, 0, 0]
        else:
            conditions = ['light', 'moderate', 'heavy']
            weights = [0.5, 0.4, 0.1]
        
        condition = random.choices(conditions, weights)[0]
        
        traffic_data = {
            'light': TrafficStatus('light', 0, None, '#27ae60', '🟢'),
            'moderate': TrafficStatus('moderate', 10, 'Normal traffic', '#f39c12', '🟡'),
            'heavy': TrafficStatus('heavy', 25, 'Congestion ahead', '#e67e22', '🟠'),
            'jam': TrafficStatus('jam', 45, 'Traffic jam - accident reported', '#e74c3c', '🔴'),
        }
        
        return traffic_data.get(condition, traffic_data['light'])
    
    def get_route_risk(self, lat: float, lon: float) -> dict:
        """Calculate route risk based on location."""
        min_distance = float('inf')
        nearest_hotspot = None
        
        for hotspot in self.HIGH_RISK_ROUTES:
            dist = ((lat - hotspot['lat'])**2 + (lon - hotspot['lon'])**2)**0.5
            if dist < min_distance:
                min_distance = dist
                nearest_hotspot = hotspot
        
        if min_distance < 0.5 and nearest_hotspot:
            return {
                'risk_level': 'high',
                'risk_score': nearest_hotspot['risk_factor'],
                'hotspot': nearest_hotspot['name'],
                'color': '#e74c3c'
            }
        elif min_distance < 1.0:
            return {
                'risk_level': 'medium',
                'risk_score': 0.4,
                'hotspot': None,
                'color': '#f39c12'
            }
        else:
            return {
                'risk_level': 'low',
                'risk_score': 0.1,
                'hotspot': None,
                'color': '#27ae60'
            }


class HistoricalDataService:
    """Historical theft data and fleet statistics."""
    
    def __init__(self):
        self._generate_sample_data()
    
    def _generate_sample_data(self):
        """Generate sample historical data."""
        self.theft_records: List[TheftRecord] = [
            TheftRecord(
                date=datetime.now() - timedelta(days=45),
                location="NH6 Near Kharagpur",
                latitude=22.35, longitude=87.32,
                weight_stolen_kg=750,
                value_inr=375000,
                recovered=False,
                description="Unauthorized stop at 2:30 AM, 750kg rebars stolen"
            ),
            TheftRecord(
                date=datetime.now() - timedelta(days=30),
                location="Bypass Road Kolaghat",
                latitude=22.43, longitude=87.88,
                weight_stolen_kg=500,
                value_inr=250000,
                recovered=True,
                description="Driver colluded, cargo recovered from nearby warehouse"
            ),
            TheftRecord(
                date=datetime.now() - timedelta(days=15),
                location="Industrial Zone Durgapur",
                latitude=23.50, longitude=87.32,
                weight_stolen_kg=1200,
                value_inr=600000,
                recovered=False,
                description="Night theft during driver rest, caught on CCTV"
            ),
            TheftRecord(
                date=datetime.now() - timedelta(days=7),
                location="Toll Plaza NH2",
                latitude=22.58, longitude=88.12,
                weight_stolen_kg=400,
                value_inr=200000,
                recovered=True,
                description="Quick response alert, thieves caught"
            ),
        ]
        
        self.fleet_stats = {
            'total_trucks': 156,
            'active_trucks': 48,
            'trips_today': 23,
            'alerts_today': 2,
            'thefts_this_month': 1,
            'thefts_last_month': 3,
            'recovery_rate': 0.42,
            'total_loss_ytd': 1825000,
            'prevented_loss': 4500000,
        }
    
    def get_fleet_stats(self) -> dict:
        """Get current fleet statistics."""
        return self.fleet_stats
    
    def get_recent_thefts(self, limit: int = 5) -> List[TheftRecord]:
        """Get recent theft incidents."""
        return sorted(self.theft_records, key=lambda x: x.date, reverse=True)[:limit]
    
    def get_theft_hotspots(self) -> List[dict]:
        """Get theft hotspot locations."""
        from collections import Counter
        locations = [t.location for t in self.theft_records]
        counts = Counter(locations)
        return [{'location': loc, 'count': cnt} for loc, cnt in counts.most_common(5)]
    
    def get_monthly_stats(self) -> dict:
        """Get monthly theft statistics."""
        return {
            'current_month': {
                'incidents': 1,
                'weight_kg': 400,
                'value_inr': 200000,
                'recovered': 1
            },
            'last_month': {
                'incidents': 3,
                'weight_kg': 2450,
                'value_inr': 1225000,
                'recovered': 1
            },
            'ytd': {
                'incidents': 12,
                'weight_kg': 8500,
                'value_inr': 4250000,
                'recovered': 5
            }
        }


# Global instances
traffic_service = TrafficService()
historical_service = HistoricalDataService()
