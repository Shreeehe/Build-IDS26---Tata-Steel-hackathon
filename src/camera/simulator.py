"""
Enhanced Camera Simulator with Bounding Boxes, Night Mode, and Obstruction Detection
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class BoundingBox:
    """Represents a detected object bounding box."""
    x1: int
    y1: int
    x2: int
    y2: int
    label: str
    confidence: float
    color: str = "#00ff00"


@dataclass
class DetectedPerson:
    """Detected person with bounding box."""
    id: int
    bbox: BoundingBox
    activity: str = "standing"  # standing, crouching, lifting


class EnhancedCameraSimulator:
    """
    Enhanced camera simulator with:
    - Bounding box detection visualization
    - Night vision (IR) mode
    - Obstruction detection
    - Power saving states
    """
    
    def __init__(self, width: int = 640, height: int = 480):
        self.width = width
        self.height = height
        self.baseline_bundle_count = 15
        self.is_night_mode = False
        self.is_powered = True
        self.power_mode = "active"  # active, standby, sleep
        self.ir_enabled = False
        
    def set_night_mode(self, enabled: bool):
        """Toggle night/IR vision mode."""
        self.is_night_mode = enabled
        self.ir_enabled = enabled
    
    def set_power_mode(self, mode: str):
        """Set power mode: active, standby, sleep."""
        self.power_mode = mode
        self.is_powered = mode != "sleep"
    
    def _get_background_color(self) -> str:
        """Get background based on day/night mode."""
        if self.is_night_mode:
            return '#1a1a2e'  # Dark blue-ish for night
        return '#3a3a3a'
    
    def _get_cargo_color(self) -> str:
        """Get cargo color based on day/night mode."""
        if self.is_night_mode:
            return '#4a4a5e'  # Grayish for IR
        return '#8B4513'  # Brown for day
    
    def _draw_bounding_box(self, draw: ImageDraw, bbox: BoundingBox):
        """Draw a labeled bounding box."""
        # Draw rectangle
        draw.rectangle(
            [bbox.x1, bbox.y1, bbox.x2, bbox.y2],
            outline=bbox.color,
            width=3
        )
        
        # Draw label background
        label_text = f"{bbox.label} ({bbox.confidence:.0%})"
        text_bbox = draw.textbbox((bbox.x1, bbox.y1 - 20), label_text)
        draw.rectangle(
            [text_bbox[0] - 2, text_bbox[1] - 2, text_bbox[2] + 2, text_bbox[3] + 2],
            fill=bbox.color
        )
        draw.text((bbox.x1, bbox.y1 - 20), label_text, fill='black')
    
    def _draw_rebar_bundles(self, draw: ImageDraw, count: int, start_x: int = 50):
        """Draw rebar bundles."""
        cargo_color = self._get_cargo_color()
        bundles_per_row = 5
        
        for i in range(count):
            row = i // bundles_per_row
            col = i % bundles_per_row
            x = start_x + col * 110
            y = 120 + row * 80
            
            draw.rectangle([x, y, x + 90, y + 60], fill=cargo_color, outline='#4a2c0a')
            
            # Draw rebar lines
            line_color = '#a0a0a0' if self.is_night_mode else '#696969'
            for j in range(6):
                line_y = y + 8 + j * 9
                draw.line([x + 5, line_y, x + 85, line_y], fill=line_color, width=2)
    
    def _draw_timestamp(self, draw: ImageDraw):
        """Add timestamp with mode indicators."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mode_text = "🌙 IR" if self.is_night_mode else "☀️ DAY"
        
        draw.rectangle([0, 0, 280, 25], fill='black')
        draw.text((5, 5), f"CAM-01 | {timestamp} | {mode_text}", fill='white')
    
    def _draw_power_indicator(self, draw: ImageDraw):
        """Draw power/battery indicator."""
        battery_levels = {"active": 87, "standby": 92, "sleep": 95}
        battery = battery_levels.get(self.power_mode, 87)
        
        # Battery icon position (top right)
        bx, by = self.width - 80, 5
        
        # Battery outline
        draw.rectangle([bx, by, bx + 50, by + 18], outline='white', width=1)
        draw.rectangle([bx + 50, by + 5, bx + 54, by + 13], fill='white')
        
        # Battery fill
        fill_width = int(48 * battery / 100)
        fill_color = '#27ae60' if battery > 50 else '#f39c12' if battery > 20 else '#e74c3c'
        draw.rectangle([bx + 2, by + 2, bx + 2 + fill_width, by + 16], fill=fill_color)
        
        draw.text((bx, by + 20), f"{battery}%", fill='white')
    
    def _draw_person_with_bbox(self, draw: ImageDraw, x: int, y: int, 
                                person_id: int, color: str) -> DetectedPerson:
        """Draw a person figure with bounding box."""
        person_color = '#8888aa' if self.is_night_mode else color
        
        # Head
        draw.ellipse([x, y, x + 30, y + 30], fill=person_color, outline='black')
        # Body
        draw.rectangle([x + 5, y + 32, x + 25, y + 80], fill=person_color, outline='black')
        # Legs
        draw.rectangle([x + 5, y + 82, x + 13, y + 110], fill=person_color, outline='black')
        draw.rectangle([x + 17, y + 82, x + 25, y + 110], fill=person_color, outline='black')
        
        # Create bounding box
        bbox = BoundingBox(
            x1=x - 5,
            y1=y - 5,
            x2=x + 35,
            y2=y + 115,
            label=f"Person {person_id}",
            confidence=0.94 - (person_id * 0.02),
            color='#00ff00'
        )
        
        self._draw_bounding_box(draw, bbox)
        
        return DetectedPerson(id=person_id, bbox=bbox, activity="standing")
    
    def generate_normal_cargo_image(self) -> Tuple[np.ndarray, List[DetectedPerson]]:
        """Generate image of normal full cargo."""
        bg_color = self._get_background_color()
        img = Image.new('RGB', (self.width, self.height), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # Truck bed outline
        draw.rectangle([30, 100, self.width - 30, self.height - 50], 
                       outline='#666666', width=3)
        
        # Full cargo
        self._draw_rebar_bundles(draw, 15)
        
        # Status overlay
        draw.rectangle([self.width - 180, self.height - 40, self.width - 10, self.height - 10], 
                       fill='#27ae60')
        draw.text((self.width - 170, self.height - 35), "CARGO: NORMAL", fill='white')
        
        self._draw_timestamp(draw)
        self._draw_power_indicator(draw)
        
        return np.array(img), []
    
    def generate_theft_image(self, bundles_stolen: int = 5) -> Tuple[np.ndarray, List[DetectedPerson]]:
        """Generate theft image with persons and bounding boxes."""
        bg_color = self._get_background_color()
        img = Image.new('RGB', (self.width, self.height), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # Truck bed outline
        draw.rectangle([30, 100, self.width - 30, self.height - 50], 
                       outline='#666666', width=3)
        
        # Reduced cargo
        remaining = max(0, 15 - bundles_stolen)
        self._draw_rebar_bundles(draw, remaining)
        
        # Empty spots (stolen cargo areas)
        for i in range(remaining, 15):
            row = i // 5
            col = i % 5
            x = 50 + col * 110
            y = 120 + row * 80
            draw.rectangle([x, y, x + 90, y + 60], outline='#ff0000', width=2)
            draw.line([x, y, x + 90, y + 60], fill='#ff0000', width=1)
            draw.line([x + 90, y, x, y + 60], fill='#ff0000', width=1)
        
        # Draw persons with bounding boxes
        detected_persons = []
        person1 = self._draw_person_with_bbox(draw, 480, 150, 1, '#e74c3c')
        person2 = self._draw_person_with_bbox(draw, 540, 180, 2, '#3498db')
        detected_persons.extend([person1, person2])
        
        # Alert overlay
        draw.rectangle([self.width - 280, self.height - 40, self.width - 10, self.height - 10], 
                       fill='#e74c3c')
        draw.text((self.width - 270, self.height - 35), 
                  f"⚠ ALERT: {len(detected_persons)} PERSONS DETECTED", fill='white')
        
        self._draw_timestamp(draw)
        self._draw_power_indicator(draw)
        
        # Recording indicator
        draw.rectangle([0, 25, 150, 50], fill='#e74c3c')
        draw.text((5, 30), "🔴 RECORDING", fill='white')
        
        return np.array(img), detected_persons
    
    def generate_obstruction_image(self) -> np.ndarray:
        """Generate image showing camera obstruction."""
        bg_color = '#1a1a1a'
        img = Image.new('RGB', (self.width, self.height), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # Static noise pattern
        for _ in range(500):
            x = np.random.randint(0, self.width)
            y = np.random.randint(0, self.height)
            gray = np.random.randint(50, 100)
            draw.point((x, y), fill=(gray, gray, gray))
        
        # Warning overlay
        draw.rectangle([self.width//2 - 150, self.height//2 - 30, 
                        self.width//2 + 150, self.height//2 + 30], 
                       fill='#e74c3c')
        draw.text((self.width//2 - 140, self.height//2 - 15), 
                  "⚠ CAMERA OBSTRUCTED", fill='white')
        
        self._draw_timestamp(draw)
        
        return np.array(img)
    
    def generate_standby_image(self) -> np.ndarray:
        """Generate standby mode image."""
        img = Image.new('RGB', (self.width, self.height), color='#1a1a1a')
        draw = ImageDraw.Draw(img)
        
        # Standby message
        draw.text((self.width//2 - 80, self.height//2 - 10), 
                  "📷 CAMERA STANDBY", fill='#666666')
        draw.text((self.width//2 - 100, self.height//2 + 20), 
                  "Activates on alert trigger", fill='#444444')
        
        self._draw_timestamp(draw)
        self._draw_power_indicator(draw)
        
        return np.array(img)


def is_night_time() -> bool:
    """Check if current time is night (6 PM - 6 AM)."""
    hour = datetime.now().hour
    return hour >= 18 or hour <= 6


if __name__ == "__main__":
    cam = EnhancedCameraSimulator()
    
    # Test day mode
    normal_img, _ = cam.generate_normal_cargo_image()
    Image.fromarray(normal_img).save("test_normal_day.png")
    
    # Test theft with bounding boxes
    theft_img, persons = cam.generate_theft_image(5)
    Image.fromarray(theft_img).save("test_theft_bbox.png")
    print(f"Detected {len(persons)} persons")
    
    # Test night mode
    cam.set_night_mode(True)
    night_img, _ = cam.generate_theft_image(5)
    Image.fromarray(night_img).save("test_theft_night.png")
    
    # Test obstruction
    obstruction_img = cam.generate_obstruction_image()
    Image.fromarray(obstruction_img).save("test_obstruction.png")
    
    print("Test images saved!")
