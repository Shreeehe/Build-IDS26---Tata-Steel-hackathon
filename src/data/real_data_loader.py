"""
Data loader for real truck delivery data from Kaggle dataset.
Converts the dataset format to our internal event format.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
import random

from .geofences import is_in_authorized_zone, AUTHORIZED_ZONES


class RealDataLoader:
    """Load and process real truck delivery data."""
    
    def __init__(self, data_path: str = None):
        self.data_path = data_path or "data/Delivery truck trip data.xlsx"
        self.df = None
        self._load_data()
    
    def _load_data(self):
        """Load the Excel data."""
        if os.path.exists(self.data_path):
            self.df = pd.read_excel(self.data_path)
            # Clean column names
            self.df.columns = self.df.columns.str.strip()
            print(f"Loaded {len(self.df)} records from {self.data_path}")
        else:
            print(f"Data file not found: {self.data_path}")
            self.df = pd.DataFrame()
    
    def get_unique_trucks(self) -> List[str]:
        """Get list of unique truck/vehicle IDs."""
        if self.df.empty:
            return []
        return self.df['vehicle_no'].dropna().unique().tolist()
    
    def get_unique_trips(self) -> List[str]:
        """Get list of unique booking IDs."""
        if self.df.empty:
            return []
        return self.df['BookingID'].dropna().unique().tolist()
    
    def get_trip_data(self, booking_id: str) -> pd.DataFrame:
        """Get all GPS pings for a specific trip."""
        if self.df.empty:
            return pd.DataFrame()
        return self.df[self.df['BookingID'] == booking_id].copy()
    
    def convert_to_events(self, booking_id: str, inject_pilferage: bool = False) -> List[dict]:
        """
        Convert a trip's data to our event format.
        Optionally inject a pilferage scenario for demo purposes.
        """
        trip_df = self.get_trip_data(booking_id)
        if trip_df.empty:
            return []
        
        # Sort by ping time
        trip_df = trip_df.sort_values('Data_Ping_time')
        
        events = []
        initial_weight = 25000  # Assumed initial weight
        current_weight = initial_weight
        prev_lat, prev_lon = None, None
        pilferage_injected = False
        
        for idx, row in trip_df.iterrows():
            try:
                timestamp = pd.to_datetime(row['Data_Ping_time'])
                lat = float(row['Curr_lat']) if pd.notna(row['Curr_lat']) else None
                lon = float(row['Curr_lon']) if pd.notna(row['Curr_lon']) else None
                
                if lat is None or lon is None:
                    continue
                
                # Calculate speed based on position change
                speed = 0.0
                is_moving = True
                if prev_lat is not None and prev_lon is not None:
                    from .geofences import haversine_distance
                    distance = haversine_distance(prev_lat, prev_lon, lat, lon)
                    # Assume 1-minute intervals between pings
                    speed = distance * 60  # km/h
                    is_moving = speed > 5  # Consider stopped if < 5 km/h
                
                # Check if in authorized zone
                in_zone, zone = is_in_authorized_zone(lat, lon)
                
                # Weight simulation with optional pilferage
                weight_change = random.uniform(-2, 2)  # Normal noise
                
                # Inject pilferage scenario
                if inject_pilferage and not pilferage_injected:
                    progress = len(events) / max(len(trip_df), 1)
                    if progress > 0.4 and progress < 0.6 and not is_moving and not in_zone:
                        # Perfect pilferage conditions - unauthorized stop
                        current_weight -= 500  # Steal 500kg
                        weight_change = -500
                        pilferage_injected = True
                
                events.append({
                    'timestamp': timestamp.isoformat(),
                    'truck_id': str(row['vehicle_no']),
                    'booking_id': str(booking_id),
                    'latitude': round(lat, 6),
                    'longitude': round(lon, 6),
                    'speed_kmh': round(max(0, speed), 1),
                    'is_moving': is_moving,
                    'weight_kg': round(current_weight + weight_change, 1),
                    'weight_change_kg': round(weight_change, 1),
                    'in_authorized_zone': in_zone,
                    'zone_name': zone.name if zone else None,
                    'current_location': str(row.get('Current_Location', '')),
                    'origin': str(row.get('Origin_Location', '')),
                    'destination': str(row.get('Destination_Location', '')),
                    'driver_name': str(row.get('Driver_Name', 'Unknown')),
                    'alert_level': 0,
                    'scenario': 'pilferage' if pilferage_injected else 'real_data'
                })
                
                prev_lat, prev_lon = lat, lon
                
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
        
        return events
    
    def get_sample_journey(self, inject_pilferage: bool = True) -> List[dict]:
        """Get a sample journey for demo purposes."""
        if self.df.empty:
            return []
        
        # Get trips with multiple GPS pings
        trip_counts = self.df.groupby('BookingID').size()
        multi_ping_trips = trip_counts[trip_counts >= 10].index.tolist()
        
        if not multi_ping_trips:
            # Fallback to any trip
            multi_ping_trips = self.get_unique_trips()[:5]
        
        if multi_ping_trips:
            booking_id = random.choice(multi_ping_trips)
            return self.convert_to_events(booking_id, inject_pilferage=inject_pilferage)
        
        return []


def generate_hybrid_data(use_real_data: bool = True, inject_pilferage: bool = True) -> List[dict]:
    """
    Generate data using real dataset if available, otherwise use simulator.
    """
    if use_real_data:
        loader = RealDataLoader()
        events = loader.get_sample_journey(inject_pilferage=inject_pilferage)
        if events:
            return events
    
    # Fallback to simulator
    from .simulator import TransitSimulator
    sim = TransitSimulator(truck_id="TS-JH-1001", initial_weight_kg=25000)
    if inject_pilferage:
        return sim.generate_pilferage_scenario()
    return sim.generate_normal_journey()


if __name__ == "__main__":
    # Test the loader
    loader = RealDataLoader()
    print(f"Unique trucks: {len(loader.get_unique_trucks())}")
    print(f"Unique trips: {len(loader.get_unique_trips())}")
    
    events = loader.get_sample_journey(inject_pilferage=True)
    print(f"Generated {len(events)} events")
    if events:
        print("Sample event:", events[0])
