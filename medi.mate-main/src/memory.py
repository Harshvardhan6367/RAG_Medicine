import json
import os
from datetime import datetime
import uuid
from src.config import Config
from src.utils import setup_logger

logger = setup_logger(__name__)

class MemoryManager:
    """
    Manages chat history and sessions - Local JSON Storage.
    """
    def __init__(self):
        self.sessions_file = os.path.join(Config.DATA_DIR, "sessions.json")
        self.messages_file = os.path.join(Config.DATA_DIR, "messages.json")
        self._ensure_data_files()
        logger.info("MemoryManager initialized with local storage")

    def _ensure_data_files(self):
        """Ensures the data directory and files exist."""
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        if not os.path.exists(self.sessions_file):
            with open(self.sessions_file, 'w') as f:
                json.dump({"sessions": []}, f)
        if not os.path.exists(self.messages_file):
            with open(self.messages_file, 'w') as f:
                json.dump({"messages": []}, f)

    def _load_sessions(self):
        """Loads sessions from the JSON file."""
        try:
            with open(self.sessions_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"sessions": []}

    def _save_sessions(self, data):
        """Saves sessions to the JSON file."""
        with open(self.sessions_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def _load_messages(self):
        """Loads messages from the JSON file."""
        try:
            with open(self.messages_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"messages": []}

    def _save_messages(self, data):
        """Saves messages to the JSON file."""
        with open(self.messages_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def get_or_create_session(self, user_id, prescription_id, title=None, filename=None, details=None):
        """
        Retrieves an existing session for the (user, prescription) pair, 
        or creates a new one if it doesn't exist.
        """
        data = self._load_sessions()
        
        # Check if session exists
        existing_session = next(
            (s for s in data["sessions"] 
             if s["user_id"] == user_id and s["prescription_id"] == prescription_id),
            None
        )
        
        if existing_session:
            # Update fields if provided and missing
            updated = False
            if title and not existing_session.get("title"):
                existing_session["title"] = title
                updated = True
            if filename and not existing_session.get("filename"):
                existing_session["filename"] = filename
                updated = True
            if details and not existing_session.get("details"):
                existing_session["details"] = details
                updated = True
            
            if updated:
                self._save_sessions(data)
            return existing_session["session_id"]
            
        # Create new session
        session_id = str(uuid.uuid4())
        new_session = {
            "session_id": session_id,
            "user_id": user_id,
            "prescription_id": prescription_id,
            "summary": "",
            "created_at": datetime.utcnow().isoformat(),
            "last_active": datetime.utcnow().isoformat()
        }
        if title:
            new_session["title"] = title
        if filename:
            new_session["filename"] = filename
        if details:
            new_session["details"] = details
            
        data["sessions"].append(new_session)
        self._save_sessions(data)
        logger.info(f"Created new session {session_id} for user {user_id} on prescription {prescription_id}")
        return session_id

    def get_session_details(self, session_id):
        """Retrieves details (medicine summary) for a session."""
        data = self._load_sessions()
        session = next((s for s in data["sessions"] if s["session_id"] == session_id), None)
        return session.get("details", "") if session else ""

    def get_prescription_by_filename(self, user_id, filename):
        """Checks if a user has already uploaded a file with this name."""
        data = self._load_sessions()
        session = next(
            (s for s in data["sessions"] 
             if s["user_id"] == user_id and s.get("filename") == filename),
            None
        )
        if session:
            return session["prescription_id"]
        return None

    def add_message(self, session_id, role, content):
        """Adds a message to the session history."""
        data = self._load_messages()
        data["messages"].append({
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        self._save_messages(data)
        self.update_last_active(session_id)

    def get_history(self, session_id, limit=10):
        """Retrieves recent messages for a session."""
        data = self._load_messages()
        session_messages = [m for m in data["messages"] if m["session_id"] == session_id]
        # Sort by timestamp
        session_messages.sort(key=lambda x: x["timestamp"])
        return session_messages[-limit:]

    def get_summary(self, session_id):
        """Retrieves the summary for a session."""
        data = self._load_sessions()
        session = next((s for s in data["sessions"] if s["session_id"] == session_id), None)
        return session.get("summary", "") if session else ""

    def update_summary(self, session_id, new_summary):
        """Updates the session summary."""
        data = self._load_sessions()
        for session in data["sessions"]:
            if session["session_id"] == session_id:
                session["summary"] = new_summary
                session["last_active"] = datetime.utcnow().isoformat()
                break
        self._save_sessions(data)

    def update_last_active(self, session_id):
        """Updates the last active timestamp."""
        data = self._load_sessions()
        for session in data["sessions"]:
            if session["session_id"] == session_id:
                session["last_active"] = datetime.utcnow().isoformat()
                break
        self._save_sessions(data)
    
    def get_user_prescriptions(self, user_id):
        """Returns list of dicts {id, title} that the user has interacted with."""
        data = self._load_sessions()
        
        # Filter sessions for this user, excluding GLOBAL
        user_sessions = [
            s for s in data["sessions"] 
            if s["user_id"] == user_id and s["prescription_id"] != "GLOBAL"
        ]
        
        # Sort by last_active descending
        user_sessions.sort(key=lambda x: x.get("last_active", ""), reverse=True)
        
        results = []
        seen_ids = set()
        for session in user_sessions:
            p_id = session["prescription_id"]
            if p_id not in seen_ids:
                results.append({
                    "id": p_id,
                    "title": session.get("title", f"Prescription {p_id[:8]}...")
                })
                seen_ids.add(p_id)
        return results

    def get_all_sessions(self):
        """Returns all sessions sorted by last active."""
        data = self._load_sessions()
        sessions = data["sessions"]
        sessions.sort(key=lambda x: x.get("last_active", ""), reverse=True)
        return sessions

    def save_otc_result(self, session_id, otc_result):
        """Saves the OTC analysis result to the session."""
        data = self._load_sessions()
        for session in data["sessions"]:
            if session["session_id"] == session_id:
                session["otc_result"] = otc_result
                break
        self._save_sessions(data)

    def get_otc_result(self, session_id):
        """Retrieves the OTC analysis result for a session."""
        data = self._load_sessions()
        session = next((s for s in data["sessions"] if s["session_id"] == session_id), None)
        return session.get("otc_result") if session else None
