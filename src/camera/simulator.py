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
    
    def _draw_open_truck_bed(self, draw: ImageDraw):
        """Draw view from camera mounted at top of truck cabin, looking down at cargo bed."""
        # Sky/trees in background (top portion)
        if self.is_night_mode:
            # Night sky
            draw.rectangle([0, 0, self.width, 100], fill='#0a0a1a')
        else:
            # Day sky with hint of trees
            draw.rectangle([0, 0, self.width, 60], fill='#87CEEB')  # Sky blue
            draw.rectangle([0, 60, self.width, 100], fill='#228B22')  # Trees
        
        # Truck cabin top (where camera is mounted) - at very top
        cabin_color = '#1a1a1a' if self.is_night_mode else '#2c3e50'
        draw.rectangle([0, 0, self.width, 40], fill=cabin_color)
        
        # Camera position indicator (red dot like in reference)
        draw.ellipse([self.width//2 - 8, 15, self.width//2 + 8, 31], fill='#ff0000', outline='#aa0000')
        
        # Truck bed floor (perspective - wider at bottom)
        bed_color = '#2a2a2a' if self.is_night_mode else '#3d3d3d'
        draw.polygon([
            (80, 100),   # Top left
            (self.width - 80, 100),  # Top right
            (self.width - 20, self.height - 40),  # Bottom right
            (20, self.height - 40)   # Bottom left
        ], fill=bed_color, outline='#555555')
        
        # Truck side rails (left and right)
        rail_color = '#1a1a1a' if self.is_night_mode else '#2c3e50'
        # Left rail
        draw.polygon([(20, self.height - 40), (80, 100), (95, 100), (35, self.height - 40)], fill=rail_color)
        # Right rail  
        draw.polygon([(self.width - 20, self.height - 40), (self.width - 80, 100), 
                     (self.width - 95, 100), (self.width - 35, self.height - 40)], fill=rail_color)
        
        # "OVERSIZE LOAD" banner at bottom (like reference)
        draw.rectangle([50, self.height - 50, self.width - 50, self.height - 25], fill='#FFD700')
        draw.text((self.width//2 - 60, self.height - 47), "OVERSIZE LOAD", fill='#000000')
    
    def _draw_steel_rebars(self, draw: ImageDraw, bundles: int = 6, highlight_missing: bool = False, missing_count: int = 0):
        """Draw realistic long steel TMT rebar bundles as seen from above/behind."""
        # Rebar colors
        if self.is_night_mode:
            steel_color = '#4a4a5a'
            steel_highlight = '#6a6a7a'
            strap_color = '#333344'
        else:
            steel_color = '#71797E'  # Steel gray
            steel_highlight = '#A9A9A9'
            strap_color = '#2c3e50'
        
        # Each bundle is a group of long rebars running lengthwise
        # Viewed from behind, we see the ends of the rebars (circles)
        # And the long bars going into the distance (lines converging to vanishing point)
        
        bundle_width = 70
        bundle_start_x = 100
        actual_bundles = bundles - missing_count
        
        for b in range(bundles):
            bx = bundle_start_x + b * (bundle_width + 15)
            
            if b >= actual_bundles:
                # Missing bundle - show empty space with red X
                if highlight_missing:
                    draw.rectangle([bx, 120, bx + bundle_width, self.height - 60], outline='#ff0000', width=2)
                    draw.line([bx, 120, bx + bundle_width, self.height - 60], fill='#ff0000', width=2)
                    draw.line([bx + bundle_width, 120, bx, self.height - 60], fill='#ff0000', width=2)
                continue
            
            # Draw long rebar lines (perspective - converge toward top)
            for rod in range(8):
                # Start position at bottom (closer to camera)
                start_x = bx + 8 + rod * 7
                start_y = self.height - 70
                
                # End position at top (further from camera) - converge to center
                convergence = 0.6
                center_x = self.width // 2
                end_x = start_x + int((center_x - start_x) * (1 - convergence))
                end_y = 110
                
                # Draw rebar line
                draw.line([(start_x, start_y), (end_x, end_y)], fill=steel_color, width=3)
                draw.line([(start_x + 1, start_y), (end_x + 1, end_y)], fill=steel_highlight, width=1)
            
            # Bundle straps (horizontal bands)
            for strap_y in [150, 220, 290, 360]:
                if strap_y < self.height - 80:
                    # Calculate strap width based on perspective
                    perspective_factor = (strap_y - 100) / (self.height - 170)
                    strap_width = int(bundle_width * (0.7 + 0.3 * perspective_factor))
                    strap_x = bx + (bundle_width - strap_width) // 2
                    draw.rectangle([strap_x, strap_y, strap_x + strap_width, strap_y + 6], fill=strap_color)
            
            # Bundle end circles (cross-section view at bottom)
            for rod in range(8):
                cx = bx + 8 + rod * 7
                cy = self.height - 65
                draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=steel_color, outline=steel_highlight)
        
        # Weight indicator at bottom
        label_color = '#ffffff' if self.is_night_mode else '#333333'
        weight = actual_bundles * 830
        draw.text((100, self.height - 22), f"TMT 500D | {actual_bundles}/{bundles} BUNDLES | {weight}kg", fill=label_color)
    
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
    
    def _draw_timestamp(self, draw: ImageDraw, monitoring_mode: str = "active"):
        """Add timestamp with mode indicators."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mode_text = "🌙 IR" if self.is_night_mode else "☀️ DAY"
        
        draw.rectangle([0, 0, 320, 25], fill='black')
        draw.text((5, 5), f"CAM-01 | {timestamp} | {mode_text} | {monitoring_mode.upper()}", fill='white')
    
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
    
    def generate_normal_cargo_image(self, monitoring_mode: str = "active") -> Tuple[np.ndarray, List[DetectedPerson]]:
        """Generate realistic image of steel rebars on open bed truck."""
        img = Image.new('RGB', (self.width, self.height), color='#2a2a2a')
        draw = ImageDraw.Draw(img)
        
        # Draw open truck bed
        self._draw_open_truck_bed(draw)
        
        # Draw steel rebar bundles (6 full bundles)
        self._draw_steel_rebars(draw, bundles=6, highlight_missing=False)
        
        # Cargo zone bounding box
        zone_color = '#00ff00' if monitoring_mode == 'continuous' else '#ffaa00'
        draw.rectangle([90, 130, self.width - 70, 360], outline=zone_color, width=2)
        
        # Status overlay
        status_text = "MONITORING" if monitoring_mode == 'continuous' else "CHECK"
        status_color = '#27ae60' if monitoring_mode == 'continuous' else '#f5a623'
        draw.rectangle([self.width - 160, 60, self.width - 10, 85], fill=status_color)
        draw.text((self.width - 150, 65), f"{status_text}", fill='white')
        
        self._draw_timestamp(draw, monitoring_mode)
        self._draw_power_indicator(draw)
        
        return np.array(img), []
    
    def generate_theft_image(self, bundles_stolen: int = 2) -> Tuple[np.ndarray, List[DetectedPerson]]:
        """Generate theft image showing stolen rebars with persons near truck."""
        img = Image.new('RGB', (self.width, self.height), color='#2a2a2a')
        draw = ImageDraw.Draw(img)
        
        # Draw open truck bed
        self._draw_open_truck_bed(draw)
        
        # Draw steel rebars with missing bundles highlighted
        self._draw_steel_rebars(draw, bundles=6, highlight_missing=True, missing_count=bundles_stolen)
        
        # Cargo zone with ALERT
        draw.rectangle([90, 130, self.width - 70, 360], outline='#ff0000', width=3)
        
        # Draw persons (thieves) near the truck
        detected_persons = []
        # Person 1 - near rear of truck
        person1 = self._draw_person_with_bbox(draw, 30, 250, 1, '#e74c3c')
        # Person 2 - on the side
        person2 = self._draw_person_with_bbox(draw, self.width - 70, 260, 2, '#e74c3c')
        detected_persons.extend([person1, person2])
        
        # Alert overlay
        draw.rectangle([self.width - 200, 60, self.width - 10, 85], fill='#e74c3c')
        draw.text((self.width - 190, 65), f"⚠ {len(detected_persons)} PERSONS", fill='white')
        
        # THEFT warning
        draw.rectangle([10, 60, 180, 85], fill='#e74c3c')
        draw.text((20, 65), f"-{bundles_stolen} BUNDLES", fill='white')
        
        self._draw_timestamp(draw, "ALERT")
        self._draw_power_indicator(draw)
        
        # Recording indicator
        draw.ellipse([10, 30, 25, 45], fill='#ff0000')  # Red recording dot
        draw.text((30, 30), "REC", fill='#ff0000')
        
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
