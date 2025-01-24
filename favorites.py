import json
import os
from typing import List, Dict
from pathlib import Path

class FavoritesManager:
    def __init__(self):
        self.favorites_file = "data/favorites.json"
        self._ensure_data_dir()
        self._load_favorites()

    def _ensure_data_dir(self):
        """Ensure the data directory exists."""
        Path("data").mkdir(exist_ok=True)
        if not os.path.exists(self.favorites_file):
            with open(self.favorites_file, "w") as f:
                json.dump({}, f)

    def _load_favorites(self) -> Dict:
        """Load favorites from file."""
        try:
            with open(self.favorites_file, "r") as f:
                return json.load(f)
        except:
            return {}

    def _save_favorites(self, favorites: Dict):
        """Save favorites to file."""
        with open(self.favorites_file, "w") as f:
            json.dump(favorites, f)

    def get_user_favorites(self, user_id: int) -> List[str]:
        """Get favorites for a specific user."""
        favorites = self._load_favorites()
        return favorites.get(str(user_id), [])

    def add_favorite(self, user_id: int, publisher_code: str) -> bool:
        """Add a publisher to user's favorites."""
        favorites = self._load_favorites()
        user_id_str = str(user_id)
        
        if user_id_str not in favorites:
            favorites[user_id_str] = []
        
        if publisher_code not in favorites[user_id_str]:
            favorites[user_id_str].append(publisher_code)
            self._save_favorites(favorites)
            return True
        return False

    def remove_favorite(self, user_id: int, publisher_code: str) -> bool:
        """Remove a publisher from user's favorites."""
        favorites = self._load_favorites()
        user_id_str = str(user_id)
        
        if user_id_str in favorites and publisher_code in favorites[user_id_str]:
            favorites[user_id_str].remove(publisher_code)
            self._save_favorites(favorites)
            return True
        return False

    def toggle_favorite(self, user_id: int, publisher_code: str) -> bool:
        """Toggle a publisher in user's favorites. Returns True if added, False if removed."""
        favorites = self._load_favorites()
        user_id_str = str(user_id)
        
        if user_id_str not in favorites:
            favorites[user_id_str] = []
        
        if publisher_code in favorites[user_id_str]:
            favorites[user_id_str].remove(publisher_code)
            self._save_favorites(favorites)
            return False
        else:
            favorites[user_id_str].append(publisher_code)
            self._save_favorites(favorites)
            return True 