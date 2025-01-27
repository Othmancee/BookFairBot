import json
from typing import Dict, List, Optional
import os
import logging

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class HallManager:
    def __init__(self):
        self.halls: Dict[int, List[Dict]] = {}
        self.load_halls()
        
    def load_halls(self) -> None:
        """Load all hall data from JSON files."""
        halls_dir = "halls"
        if not os.path.exists(halls_dir):
            logger.error(f"Halls directory '{halls_dir}' not found!")
            return
            
        for filename in os.listdir(halls_dir):
            if filename.startswith("hall") and filename.endswith(".json"):
                try:
                    hall_number = int(filename[4:-5])  # Extract number from "hallX.json"
                    with open(os.path.join(halls_dir, filename), 'r', encoding='utf-8') as f:
                        hall_data = json.load(f)
                        if "publishers" in hall_data:
                            self.halls[hall_number] = hall_data["publishers"]
                            logger.info(f"Loaded {len(hall_data['publishers'])} publishers from {filename}")
                        else:
                            logger.error(f"No publishers found in {filename}")
                except Exception as e:
                    logger.error(f"Error loading {filename}: {e}")
        
        logger.info(f"Total halls loaded: {len(self.halls)}")
        for hall_num, publishers in self.halls.items():
            logger.info(f"Hall {hall_num}: {len(publishers)} publishers")
    
    def get_hall_publishers(self, hall_number: int) -> List[Dict]:
        """Get all publishers in a specific hall."""
        return self.halls.get(hall_number, [])
    
    def get_section_publishers(self, hall_number: int, section: str) -> List[Dict]:
        """Get all publishers in a specific section of a hall."""
        publishers = self.get_hall_publishers(hall_number)
        return [pub for pub in publishers if pub.get('section', '').lower() == section.lower()]
    
    def get_publisher_by_code(self, code: str, hall_number: int = None) -> Dict:
        """Get a publisher by their code and optionally hall number."""
        if hall_number is not None:
            # Look in specific hall
            publishers = self.get_hall_publishers(hall_number)
            for pub in publishers:
                if pub['code'].lower() == code.lower():
                    return pub
            return None
        else:
            # Look in all halls (legacy support)
            for hall_publishers in self.halls.values():
                for pub in hall_publishers:
                    if pub['code'].lower() == code.lower():
                        return pub
            return None
    
    def search_publishers(self, query: str) -> List[Dict]:
        """Search for publishers by name or code."""
        if not query:
            return []
        
        results = []
        query = query.lower().strip()
        logger.info(f"Searching for: {query}")
        
        # Check if searching for a specific hall
        hall_match = None
        hall_query = query.replace('قاعة ', '').replace('hall ', '')
        if hall_query.isdigit():
            hall_match = int(hall_query)
        
        # Search in all halls (or specific hall if specified)
        for hall_number, hall_publishers in self.halls.items():
            # Skip if searching for specific hall and this isn't it
            if hall_match is not None and hall_number != hall_match:
                continue
            
            for pub in hall_publishers:
                matched = False
                
                # Check code (case-insensitive)
                pub_code = str(pub.get('code', '')).lower()
                if pub_code and query in pub_code:
                    logger.info(f"Found by code: {pub.get('nameAr')} ({pub_code}) in Hall {hall_number}")
                    matched = True
                
                # Check Arabic name
                name_ar = str(pub.get('nameAr', '')).lower()
                if not matched and name_ar and query in name_ar:
                    logger.info(f"Found by Arabic name: {pub.get('nameAr')} in Hall {hall_number}")
                    matched = True
                
                # Check English name
                name_en = str(pub.get('nameEn', '')).lower()
                if not matched and name_en and query in name_en:
                    logger.info(f"Found by English name: {pub.get('nameEn')} in Hall {hall_number}")
                    matched = True
                
                # Add to results if matched
                if matched or hall_match == hall_number:
                    results.append(pub)
        
        logger.info(f"Found {len(results)} results")
        return results
    
    def find_neighboring_publishers(self, hall_number: int, publisher: Dict, max_neighbors: int = 3) -> List[Dict]:
        """Find neighboring publishers in the same hall based on proximity."""
        publishers = self.get_hall_publishers(hall_number)
        if not publishers:
            return []

        # Get current publisher's position
        current_x = publisher['position']['x']
        current_y = publisher['position']['y']
        current_section = publisher.get('section', '')

        # Calculate distances to all other publishers in the same section
        neighbors = []
        for pub in publishers:
            if pub['code'] == publisher['code']:  # Skip self
                continue
                
            # Prioritize publishers in the same section
            if pub.get('section', '') != current_section:
                continue

            # Calculate Euclidean distance
            dx = pub['position']['x'] - current_x
            dy = pub['position']['y'] - current_y
            distance = (dx * dx + dy * dy) ** 0.5

            # Add to neighbors list with distance
            neighbors.append((distance, pub))

        # Sort by distance and take the closest ones
        neighbors.sort(key=lambda x: x[0])
        return [pub for _, pub in neighbors[:max_neighbors]]

    def get_adjacent_publishers(self, hall_number: int, section: str, code: str) -> List[Dict]:
        """Get publishers adjacent to the given publisher."""
        section_pubs = self.get_section_publishers(hall_number, section)
        
        # Find the index of the current publisher
        current_idx = -1
        for i, pub in enumerate(section_pubs):
            if pub['code'].lower() == code.lower():
                current_idx = i
                break
        
        if current_idx == -1:
            return []
        
        # Get up to 2 publishers before and after the current one
        start_idx = max(0, current_idx - 2)
        end_idx = min(len(section_pubs), current_idx + 3)
        
        adjacent = section_pubs[start_idx:current_idx] + section_pubs[current_idx + 1:end_idx]
        return adjacent

    def format_publisher_info(self, publisher: dict, include_neighbors: bool = False) -> str:
        """Format publisher information for display with proper RTL alignment."""
        info = []
        
        # Add Arabic name with icon on right
        name_ar = publisher.get('nameAr', 'بدون اسم')
        info.append(f"*{name_ar}* ")
        
        # Add English name if available
        if publisher.get('nameEn'):
            info.append(f"_{publisher.get('nameEn')}_")
        
        # Add hall and code info
        info.append(f"🏛 القاعة: {publisher.get('hall', 'غير متوفر')}")
        info.append(f"🏷️ الكود: `{publisher.get('code', 'غير متوفر')}`")
        
        # Add offers if available
        offers = publisher.get('offers', [])
        if offers:
            info.append("\n📢 *العروض:*")
            for offer in offers:
                info.append(f"• {offer}")
        
        # Add neighboring publishers if requested
        if include_neighbors:
            neighbors = self.find_neighboring_publishers(publisher.get('hall'), publisher)
            if neighbors:
                info.append("\n🏪 *الأجنحة المجاورة:*")
                for neighbor in neighbors:
                    info.append(f"• {neighbor.get('nameAr', 'بدون اسم')} ({neighbor.get('code', '??')})")
        
        return "\n".join(info) 