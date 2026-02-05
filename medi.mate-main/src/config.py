import os
from dotenv import load_dotenv

# Load environment variables from .env (project root)
load_dotenv()

class Config:
    """
    Central configuration class.
    """

    # ========================
    # API KEYS
    # ========================
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    # ========================
    # GEMINI SETTINGS
    # ========================
    GEMINI_MODEL_NAME = "gemini-2.5-flash-lite"

    # ========================
    # PATHS
    # ========================
    BASE_DIR = os.getcwd()
    DATA_DIR = os.path.join(BASE_DIR, "data")
    INPUT_DIR = os.path.join(DATA_DIR, "input")
    PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

    # ========================
    # VALIDATION
    # ========================
    @staticmethod
    def validate():
        if not Config.GOOGLE_API_KEY:
            raise ValueError(
                "❌ GOOGLE_API_KEY is missing. "
                "Check that .env exists in project root and contains a valid key."
            )
