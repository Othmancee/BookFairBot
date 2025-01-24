from typing import Dict, List, Optional
import io
import os

class MapManager:
    def __init__(self):
        self.halls = {
            1: {"name": "القاعة 1", "sections": ["A", "B", "C"]},
            2: {"name": "القاعة 2", "sections": ["A", "B", "C"]},
            3: {"name": "القاعة 3", "sections": ["A", "B", "C"]},
            4: {"name": "القاعة 4", "sections": ["A", "B", "C"]},
            5: {"name": "القاعة 5", "sections": ["A", "B", "C"]}
        }
        
        # SVG dimensions and styling
        self.svg_width = 1200
        self.svg_height = 1600
        self.margin = 50
        self.styles = """
            <style>
                .booth { 
                    stroke: #333; 
                    stroke-width: 1; 
                    transition: all 0.3s ease;
                }
                .booth:hover { 
                    opacity: 0.8; 
                    cursor: pointer; 
                }
                .booth.highlighted { 
                    stroke: #ffd700;  /* Gold stroke */
                    stroke-width: 3; 
                    filter: drop-shadow(0 0 5px rgba(255, 215, 0, 0.7));
                    opacity: 1;
                }
                .booth-dimmed { 
                    opacity: 0.3;  /* More dimmed */
                    filter: grayscale(30%);
                }
                .booth-label { 
                    font-family: Arial, sans-serif; 
                    font-size: 12px; 
                    fill: #000;
                    pointer-events: none;
                    text-anchor: middle;  /* Horizontal centering */
                    dominant-baseline: central;  /* Vertical centering */
                }
                .section-label {
                    font-family: Arial, sans-serif;
                    font-size: 16px;
                    fill: #666;
                    font-weight: bold;
                    text-anchor: middle;
                }
                .hall-title {
                    font-family: Arial, sans-serif;
                    font-size: 24px;
                    fill: #333;
                    font-weight: bold;
                    text-anchor: middle;
                }
            </style>
        """

    def create_hall_map(self, hall_number: int, publishers: List[Dict], highlight_code: Optional[str] = None) -> str:
        """Create an SVG map visualization for a specific hall."""
        try:
            # Calculate bounds for scaling
            x_coords = [float(p['position']['x']) for p in publishers]
            y_coords = [float(p['position']['y']) for p in publishers]
            min_x = min(x_coords)
            max_x = max(x_coords)
            min_y = min(y_coords)
            max_y = max(y_coords)
            
            # Calculate scaling factors to fit the map
            content_width = max_x - min_x + 100  # Add padding
            content_height = max_y - min_y + 100  # Add padding
            scale_x = (self.svg_width - 2 * self.margin) / content_width
            scale_y = (self.svg_height - 2 * self.margin) / content_height
            scale = min(scale_x, scale_y)  # Use the same scale for both axes
            
            # Function to transform coordinates
            def transform(x: float, y: float) -> tuple[float, float]:
                new_x = (x - min_x) * scale + self.margin
                new_y = (y - min_y) * scale + self.margin
                return new_x, new_y
            
            # Start SVG document with styles
            svg = [
                f'<?xml version="1.0" encoding="UTF-8"?>',
                f'<svg width="{self.svg_width}" height="{self.svg_height}" xmlns="http://www.w3.org/2000/svg">',
                self.styles,  # Use the predefined styles
                
                # Add white background
                f'<rect width="{self.svg_width}" height="{self.svg_height}" fill="white"/>',
                
                # Add title
                f'<text x="{self.svg_width/2}" y="{self.margin}" class="hall-title">{self.halls[hall_number]["name"]}</text>'
            ]

            # Group publishers by section for better organization
            sections = {}
            for pub in publishers:
                section = pub.get('section', '')
                if section not in sections:
                    sections[section] = []
                sections[section].append(pub)
            
            # Draw sections and publishers
            for section, pubs in sections.items():
                # Add section label if we have publishers in this section
                if pubs:
                    # Find section center
                    x_coords = [float(p['position']['x']) for p in pubs]
                    y_coords = [float(p['position']['y']) for p in pubs]
                    section_x = sum(x_coords) / len(x_coords)
                    section_y = min(y_coords) - 20  # Place label above booths
                    
                    # Transform section label coordinates
                    label_x, label_y = transform(section_x, section_y)
                    
                    svg.append(
                        f'<text x="{label_x}" y="{label_y}" class="section-label">قسم {section}</text>'
                    )
                
                # Draw publishers in this section
                for pub in pubs:
                    x = float(pub['position']['x'])
                    y = float(pub['position']['y'])
                    width = float(pub['width']) * scale
                    height = float(pub['height']) * scale
                    code = pub.get('code', '')
                    color = pub.get('color', '#f7931b')  # Use publisher's color or default
                    
                    # Transform booth coordinates
                    booth_x, booth_y = transform(x, y)
                    
                    # Determine booth classes
                    classes = ['booth']
                    if highlight_code:
                        if code == highlight_code:
                            classes.append('highlighted')
                            # Add glow effect for highlighted booth
                            svg.append(
                                f'<rect x="{booth_x-5}" y="{booth_y-5}" '
                                f'width="{width+10}" height="{height+10}" '
                                'class="highlight-glow"/>'
                            )
                        else:
                            classes.append('booth-dimmed')
                    
                    # Draw booth - always as rectangle unless explicitly marked as circle
                    if pub.get('is_circle', False):  # Only circles if explicitly marked
                        radius = min(width, height) / 2
                        svg.append(
                            f'<circle cx="{booth_x + radius}" cy="{booth_y + radius}" r="{radius}" '
                            f'class="{" ".join(classes)}" fill="{color}">'
                            f'<title>{pub.get("nameAr", "")} ({code})</title></circle>'
                        )
                    else:  # Default to rectangle
                        svg.append(
                            f'<rect x="{booth_x}" y="{booth_y}" width="{width}" height="{height}" '
                            f'class="{" ".join(classes)}" fill="{color}">'
                            f'<title>{pub.get("nameAr", "")} ({code})</title></rect>'
                        )
                    
                    # Make highlighted booth's label more prominent
                    label_classes = ['booth-label']
                    if highlight_code and code == highlight_code:
                        label_classes.append('highlighted')
                        svg.append(
                            f'<text x="{booth_x + width/2}" y="{booth_y + height/2}" '
                            f'class="{" ".join(label_classes)}" '
                            f'style="font-weight: bold; font-size: 14px">{code}</text>'
                        )
                    else:
                        svg.append(
                            f'<text x="{booth_x + width/2}" y="{booth_y + height/2}" '
                            f'class="{" ".join(label_classes)}">{code}</text>'
                        )
            
            # Close SVG
            svg.append('</svg>')
            
            return '\n'.join(svg)
            
        except Exception as e:
            print(f"Error creating map: {e}")
            return None

    def get_hall_info(self, hall_number: int) -> Optional[Dict]:
        """Get information about a specific hall."""
        return self.halls.get(hall_number)

    def save_hall_map(self, hall_number: int, publishers: List[Dict], highlight_code: str = None, output_dir: str = "maps") -> Optional[str]:
        """Generate and save a hall map as SVG file."""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate SVG
            svg_content = self.create_hall_map(hall_number, publishers, highlight_code)
            if not svg_content:
                return None
            
            # Save to file
            output_path = os.path.join(output_dir, f"hall{hall_number}.svg")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            
            return output_path
            
        except Exception as e:
            print(f"Error saving map: {e}")
            return None

    def get_section_publishers(self, hall_number: int, section: str, publishers: List[Dict]) -> List[Dict]:
        """Get all publishers in a specific hall section."""
        return [p for p in publishers 
                if p['hall'] == hall_number and p['section'] == section] 