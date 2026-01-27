"""
Simple AI Detector - Simulates AI-based cargo and person detection.
For demo purposes - compares images and detects persons.
"""
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class DetectionResult:
    """Result of AI detection."""
    cargo_change_detected: bool
    cargo_change_percent: float
    persons_detected: int
    alert_level: str  # 'normal', 'warning', 'critical'
    details: str


class SimpleAIDetector:
    """
    Simple AI detector for cargo monitoring.
    Uses image comparison and color-based person detection.
    """
    
    def __init__(self):
        self.baseline_image = None
        self.cargo_change_threshold = 15.0  # Percent change to trigger alert
        self.critical_threshold = 30.0  # Percent change for critical alert
        
    def set_baseline(self, image: np.ndarray):
        """Set the baseline image for comparison."""
        self.baseline_image = image.copy()
    
    def detect_cargo_change(self, current_image: np.ndarray) -> Tuple[bool, float]:
        """
        Compare current image with baseline to detect cargo reduction.
        Returns (change_detected, change_percentage)
        """
        if self.baseline_image is None:
            return False, 0.0
        
        # Convert to grayscale for comparison
        baseline_gray = np.mean(self.baseline_image, axis=2)
        current_gray = np.mean(current_image, axis=2)
        
        # Calculate absolute difference
        diff = np.abs(baseline_gray.astype(float) - current_gray.astype(float))
        
        # Calculate change percentage
        change_percent = (np.sum(diff) / diff.size) * 100 / 255  # Normalize to 0-100
        
        change_detected = change_percent > self.cargo_change_threshold
        
        return change_detected, round(change_percent, 2)
    
    def detect_persons(self, image: np.ndarray) -> int:
        """
        Detect persons in the image using color-based detection.
        For demo - detects red and blue colored objects as persons.
        In real scenario, would use YOLO or similar.
        """
        person_count = 0
        
        # Define color ranges for person detection (RGB)
        # Red person (around #e74c3c)
        red_mask = (
            (image[:, :, 0] > 180) & 
            (image[:, :, 1] < 100) & 
            (image[:, :, 2] < 100)
        )
        red_pixels = np.sum(red_mask)
        
        # Blue person (around #3498db)
        blue_mask = (
            (image[:, :, 0] < 100) & 
            (image[:, :, 1] > 100) & 
            (image[:, :, 2] > 180)
        )
        blue_pixels = np.sum(blue_mask)
        
        # Threshold for person detection
        pixel_threshold = 500
        
        if red_pixels > pixel_threshold:
            person_count += 1
        if blue_pixels > pixel_threshold:
            person_count += 1
        
        return person_count
    
    def analyze_frame(self, current_image: np.ndarray) -> DetectionResult:
        """
        Perform full analysis on a camera frame.
        Returns comprehensive detection result.
        """
        # Detect cargo change
        cargo_changed, change_percent = self.detect_cargo_change(current_image)
        
        # Detect persons
        person_count = self.detect_persons(current_image)
        
        # Determine alert level
        if cargo_changed and person_count > 0:
            alert_level = 'critical'
            details = f"CRITICAL: Cargo reduced by {change_percent:.1f}% with {person_count} person(s) detected!"
        elif cargo_changed:
            alert_level = 'critical' if change_percent > self.critical_threshold else 'warning'
            details = f"Cargo change detected: {change_percent:.1f}% reduction"
        elif person_count > 0:
            alert_level = 'warning'
            details = f"Unauthorized person(s) detected: {person_count}"
        else:
            alert_level = 'normal'
            details = "All clear - no anomalies detected"
        
        return DetectionResult(
            cargo_change_detected=cargo_changed,
            cargo_change_percent=change_percent,
            persons_detected=person_count,
            alert_level=alert_level,
            details=details
        )
    
    def get_detection_summary(self, result: DetectionResult) -> dict:
        """Get a summary dict for dashboard display."""
        return {
            'cargo_change': result.cargo_change_detected,
            'change_percent': result.cargo_change_percent,
            'persons': result.persons_detected,
            'alert': result.alert_level,
            'message': result.details
        }


if __name__ == "__main__":
    # Test the detector
    from simulator import CameraSimulator
    
    cam = CameraSimulator()
    detector = SimpleAIDetector()
    
    # Set baseline with normal cargo
    normal = cam.generate_normal_cargo_image()
    detector.set_baseline(normal)
    
    # Test with theft scenario
    theft = cam.generate_theft_image(5)
    result = detector.analyze_frame(theft)
    
    print(f"Cargo changed: {result.cargo_change_detected}")
    print(f"Change percent: {result.cargo_change_percent}%")
    print(f"Persons detected: {result.persons_detected}")
    print(f"Alert level: {result.alert_level}")
    print(f"Details: {result.details}")
