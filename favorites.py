import json
import os
import logging
from typing import List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

class FavoritesManager:
    def __init__(self):
        self.favorites_file = "data/favorites.json"
        logger.info(f"Initializing FavoritesManager with file: {self.favorites_file}")
        self._ensure_data_dir()
        self._load_favorites()

    def _validate_composite_key(self, composite_key: str) -> bool:
        """Validate the format of a composite key (hall_number_code)."""
        try:
            if not composite_key or '_' not in composite_key:
                return False
            hall_number, code = composite_key.split('_')
            hall_number = int(hall_number)
            return 1 <= hall_number <= 5 and code.strip()
        except (ValueError, AttributeError):
            return False

    def _ensure_data_dir(self):
        """Ensure the data directory exists."""
        try:
            logger.info("Ensuring data directory exists")
            Path("data").mkdir(exist_ok=True)
            if not os.path.exists(self.favorites_file):
                logger.info(f"Creating new favorites file: {self.favorites_file}")
                with open(self.favorites_file, "w") as f:
                    json.dump({}, f)
            logger.info("Data directory and file check completed")
        except Exception as e:
            logger.error(f"Error ensuring data directory: {e}", exc_info=True)
            raise

    def _load_favorites(self) -> Dict:
        """Load favorites from file."""
        try:
            logger.info(f"Loading favorites from {self.favorites_file}")
            with open(self.favorites_file, "r") as f:
                data = json.load(f)
                logger.info(f"Loaded favorites for {len(data)} users")
                return data
        except FileNotFoundError:
            logger.warning("Favorites file not found, creating new one")
            self._ensure_data_dir()
            return {}
        except json.JSONDecodeError:
            logger.error("Corrupted favorites file, creating backup and new file")
            if os.path.exists(self.favorites_file):
                os.rename(self.favorites_file, f"{self.favorites_file}.bak")
            return {}
        except Exception as e:
            logger.error(f"Error loading favorites: {e}", exc_info=True)
            return {}

    def _save_favorites(self, favorites: Dict):
        """Save favorites to file."""
        try:
            logger.info(f"Saving favorites to {self.favorites_file}")
            # Create backup before saving
            if os.path.exists(self.favorites_file):
                os.replace(self.favorites_file, f"{self.favorites_file}.bak")
            with open(self.favorites_file, "w") as f:
                json.dump(favorites, f)
            logger.info("Favorites saved successfully")
        except Exception as e:
            logger.error(f"Error saving favorites: {e}", exc_info=True)
            # Try to restore from backup
            try:
                if os.path.exists(f"{self.favorites_file}.bak"):
                    os.replace(f"{self.favorites_file}.bak", self.favorites_file)
            except Exception as restore_error:
                logger.error(f"Failed to restore favorites from backup: {restore_error}", exc_info=True)
            raise

    def get_user_favorites(self, user_id: int) -> List[str]:
        """Get favorites for a specific user."""
        try:
            logger.info(f"Getting favorites for user {user_id}")
            favorites = self._load_favorites()
            user_favs = favorites.get(str(user_id), [])
            
            # Filter out invalid entries and remove duplicates
            valid_favs = []
            seen = set()
            for fav in user_favs:
                if self._validate_composite_key(fav) and fav not in seen:
                    valid_favs.append(fav)
                    seen.add(fav)
            
            # Save if we removed any invalid entries or duplicates
            if len(valid_favs) != len(user_favs):
                logger.warning(f"Removed {len(user_favs) - len(valid_favs)} invalid/duplicate favorites for user {user_id}")
                favorites[str(user_id)] = valid_favs
                self._save_favorites(favorites)
                
            logger.info(f"Found {len(valid_favs)} valid favorites for user {user_id}")
            return valid_favs
            
        except Exception as e:
            logger.error(f"Error getting user favorites: {e}", exc_info=True)
            return []

    def add_favorite(self, user_id: int, publisher_code: str) -> bool:
        """Add a publisher to user's favorites."""
        try:
            logger.info(f"Adding favorite {publisher_code} for user {user_id}")
            favorites = self._load_favorites()
            user_id_str = str(user_id)
            
            if user_id_str not in favorites:
                logger.info(f"Creating new favorites list for user {user_id}")
                favorites[user_id_str] = []
            
            if publisher_code not in favorites[user_id_str]:
                favorites[user_id_str].append(publisher_code)
                self._save_favorites(favorites)
                logger.info(f"Added {publisher_code} to favorites for user {user_id}")
                return True
            logger.info(f"Publisher {publisher_code} already in favorites for user {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error adding favorite: {e}", exc_info=True)
            return False

    def remove_favorite(self, user_id: int, publisher_code: str) -> bool:
        """Remove a publisher from user's favorites."""
        try:
            logger.info(f"Removing favorite {publisher_code} for user {user_id}")
            favorites = self._load_favorites()
            user_id_str = str(user_id)
            
            if user_id_str in favorites and publisher_code in favorites[user_id_str]:
                favorites[user_id_str].remove(publisher_code)
                self._save_favorites(favorites)
                logger.info(f"Removed {publisher_code} from favorites for user {user_id}")
                return True
            logger.info(f"Publisher {publisher_code} not found in favorites for user {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error removing favorite: {e}", exc_info=True)
            return False

    def toggle_favorite(self, user_id: int, composite_key: str) -> bool:
        """Toggle a publisher in user's favorites. Returns True if added, False if removed."""
        try:
            logger.info(f"Toggling favorite {composite_key} for user {user_id}")
            
            # Validate composite key
            if not self._validate_composite_key(composite_key):
                logger.error(f"Invalid composite key format: {composite_key}")
                return False
            
            favorites = self._load_favorites()
            user_id_str = str(user_id)
            
            if user_id_str not in favorites:
                logger.info(f"Creating new favorites list for user {user_id}")
                favorites[user_id_str] = []
            
            # Clean up invalid entries
            favorites[user_id_str] = [f for f in favorites[user_id_str] if self._validate_composite_key(f)]
            
            if composite_key in favorites[user_id_str]:
                favorites[user_id_str].remove(composite_key)
                self._save_favorites(favorites)
                logger.info(f"Removed {composite_key} from favorites for user {user_id}")
                return False
            else:
                favorites[user_id_str].append(composite_key)
                self._save_favorites(favorites)
                logger.info(f"Added {composite_key} to favorites for user {user_id}")
                return True
        except Exception as e:
            logger.error(f"Error toggling favorite: {e}", exc_info=True)
            return False

    def set_user_favorites(self, user_id: int, favorites_list: List[str]) -> bool:
        """Set the complete list of favorites for a user."""
        try:
            logger.info(f"Setting favorites for user {user_id}: {favorites_list}")
            favorites = self._load_favorites()
            user_id_str = str(user_id)
            favorites[user_id_str] = favorites_list
            self._save_favorites(favorites)
            logger.info(f"Successfully set favorites for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting favorites: {e}", exc_info=True)
            return False

    def clean_favorites(self, user_id: int, hall_manager) -> None:
        """Clean up favorites data by removing invalid entries and migrating old format."""
        try:
            logger.info(f"Cleaning favorites for user {user_id}")
            favorites = self._load_favorites()
            user_id_str = str(user_id)
            
            if user_id_str not in favorites:
                return
            
            user_favs = favorites[user_id_str]
            valid_favorites = set()  # Use set to avoid duplicates
            
            for fav in user_favs:
                try:
                    if '_' not in fav:
                        # Old format - try to find publisher in all halls
                        code = fav
                        for hall_num in range(1, 6):
                            publisher = hall_manager.get_publisher_by_code(code, hall_num)
                            if publisher:
                                composite_key = f"{hall_num}_{code}"
                                if self._validate_composite_key(composite_key):
                                    valid_favorites.add(composite_key)
                                    logger.info(f"Migrated old format {code} to {composite_key}")
                        continue
                    
                    # New format validation
                    if not self._validate_composite_key(fav):
                        logger.warning(f"Invalid favorite format: {fav}")
                        continue
                        
                    hall_number, code = fav.split('_')
                    hall_number = int(hall_number)
                    
                    # Verify publisher exists
                    publisher = hall_manager.get_publisher_by_code(code, hall_number)
                    if publisher:
                        valid_favorites.add(fav)
                    else:
                        logger.warning(f"Publisher not found for favorite: {fav}")
                        
                except Exception as e:
                    logger.error(f"Error processing favorite {fav}: {e}", exc_info=True)
                    continue
            
            # Convert set back to list and save if changed
            valid_favorites_list = sorted(list(valid_favorites))
            if valid_favorites_list != user_favs:
                logger.info(f"Updating favorites for user {user_id}: {valid_favorites_list}")
                favorites[user_id_str] = valid_favorites_list
                self._save_favorites(favorites)
                
        except Exception as e:
            logger.error(f"Error cleaning favorites: {e}", exc_info=True) 