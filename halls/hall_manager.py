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
        """Get all publishers in a specific hall section."""
        return [p for p in self.get_hall_publishers(hall_number) 
                if p.get('section') == section]
    
    def get_publisher_by_code(self, code: str) -> Optional[Dict]:
        """Find a publisher by their code across all halls."""
        code = code.strip().upper()  # Normalize code format
        for hall_publishers in self.halls.values():
            for publisher in hall_publishers:
                if publisher.get('code', '').upper() == code:
                    return publisher
        return None
    
    def search_publishers(self, query: str) -> list:
        """Search for publishers by name (Arabic/English) or code."""
        if not query:
            return []
            
        results = []
        query = query.lower().strip()
        logger.info(f"Searching for: {query}")
        
        for hall_num, hall_publishers in self.halls.items():
            for publisher in hall_publishers:
                # Check code (case-insensitive)
                pub_code = str(publisher.get('code') or '').lower()
                if pub_code and query in pub_code:
                    logger.info(f"Found by code: {publisher.get('nameAr')} ({pub_code})")
                    results.append(publisher)
                    continue
                
                # Check Arabic name
                name_ar = str(publisher.get('nameAr') or '').lower()
                if name_ar and query in name_ar:
                    logger.info(f"Found by Arabic name: {publisher.get('nameAr')}")
                    results.append(publisher)
                    continue
                
                # Check English name if it exists
                name_en = str(publisher.get('nameEn') or '').lower()
                if name_en and query in name_en:
                    logger.info(f"Found by English name: {publisher.get('nameEn')}")
                    results.append(publisher)
                    continue
                
                # Check hall number
                hall_query = query.replace('قاعة ', '').replace('hall ', '')
                if hall_query.isdigit() and int(hall_query) == publisher.get('hall'):
                    logger.info(f"Found by hall number: {publisher.get('nameAr')} (Hall {publisher.get('hall')})")
                    results.append(publisher)
                    continue
        
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

    def format_publisher_info(self, publisher: dict, include_neighbors: bool = False) -> str:
        """Format publisher information for display with proper RTL alignment."""
        info = []
        
        # Add Arabic name with icon on right
        name_ar = publisher.get('nameAr', 'بدون اسم')
        info.append(f"*{name_ar}* 📚")
        
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