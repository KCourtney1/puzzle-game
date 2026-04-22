import os
from dotenv import load_dotenv

# --- Configuration ---
MAX_WINDOW_SIZE = 900
GRID_SIZE = 3
FPS = 600
FLASH_TIME = FPS//10
MAX_VIDEO_FRAMES = 15000
VALID_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.mp4'}

load_dotenv()
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")