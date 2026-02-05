import bcrypt
import json
import os
from datetime import datetime
from src.config import Config
from src.utils import setup_logger

logger = setup_logger(__name__)

class AuthManager:
    """
    Manages User Authentication (Login/Register) - Local JSON Storage.
    """
    def __init__(self):
        self.data_file = os.path.join(Config.DATA_DIR, "users.json")
        self._ensure_data_file()
        logger.info("AuthManager initialized with local storage")

    def _ensure_data_file(self):
        """Ensures the data directory and users file exist."""
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w') as f:
                json.dump({"users": []}, f)

    def _load_users(self):
        """Loads users from the JSON file."""
        try:
            with open(self.data_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"users": []}

    def _save_users(self, data):
        """Saves users to the JSON file."""
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def register_user(self, username, password):
        """Registers a new user."""
        data = self._load_users()
        
        # Check if username exists
        if any(user["username"] == username for user in data["users"]):
            return False, "Username already exists."
        
        # Hash password
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        data["users"].append({
            "username": username,
            "password_hash": hashed.decode('utf-8'),  # Store as string for JSON
            "created_at": datetime.utcnow().isoformat()
        })
        
        self._save_users(data)
        logger.info(f"Registered user: {username}")
        return True, "User registered successfully."

    def login_user(self, username, password):
        """Authenticates a user."""
        data = self._load_users()
        
        user = next((u for u in data["users"] if u["username"] == username), None)
        if not user:
            return False, "Invalid username or password."
        
        # Convert stored hash back to bytes for bcrypt comparison
        stored_hash = user['password_hash'].encode('utf-8')
        
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            logger.info(f"User logged in: {username}")
            return True, "Login successful."
        else:
            return False, "Invalid username or password."
