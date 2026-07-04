""" General configurations for main.py """
import os

# Base directory (where this config file is located)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_path(rel_path):
    return os.path.join(BASE_DIR, rel_path)

# Input video path
INPUT_VIDEO_PATH = get_path("input/rally_001.mp4")

# Inference video path
OUTPUT_VIDEO_PATH = "results_new.mp4"

# True to collect 2d projection data
COLLECT_DATA = True
# Collected data path
COLLECT_DATA_PATH = "data_new.csv"

# Maximum number of frames to be analysed
MAX_FRAMES = None

# True to use the model (YOLO) to detect keypoints dynamically every frame
# False to use the fixed/manual selection at the start
DYNAMIC_COURT_KEYPOINTS = False

# Fixed court keypoints
FIXED_COURT_KEYPOINTS_LOAD_PATH = get_path("cache/fixed_keypoints_detection.json")
FIXED_COURT_KEYPOINTS_SAVE_PATH = get_path("cache/fixed_keypoints_detection.json")

# Players tracker
PLAYERS_TRACKER_MODEL = get_path("weights/yolo26m.pt")
PLAYERS_TRACKER_BATCH_SIZE = 4
PLAYERS_TRACKER_ANNOTATOR = "rectangle_bounding_box"
PLAYERS_TRACKER_LOAD_PATH = None
PLAYERS_TRACKER_SAVE_PATH = get_path("cache/players_detections.json")

# Players keypoints tracker
PLAYERS_KEYPOINTS_TRACKER_MODEL = get_path("weights/player_keypoints_detection.pt")
PLAYERS_KEYPOINTS_TRACKER_TRAIN_IMAGE_SIZE = 1280
PLAYERS_KEYPOINTS_TRACKER_BATCH_SIZE = 8
PLAYERS_KEYPOINTS_TRACKER_LOAD_PATH = None
PLAYERS_KEYPOINTS_TRACKER_SAVE_PATH = get_path("cache/players_keypoints_detections.json")

# Ball tracker
BALL_TRACKER_MODEL = get_path("weights/ball_detection.pt")
BALL_TRACKER_INPAINT_MODEL = None # Disabled for maximum speed
BALL_TRACKER_BATCH_SIZE = 4 # Optimized for speed and stability
BALL_TRACKER_MEDIAN_MAX_SAMPLE_NUM = 400
BALL_TRACKER_LOAD_PATH = None
BALL_TRACKER_SAVE_PATH = get_path("cache/ball_detections.json")

# Court keypoints tracker
KEYPOINTS_TRACKER_MODEL = get_path("weights/court_keypoints_detection.pt")
KEYPOINTS_TRACKER_BATCH_SIZE = 8
KEYPOINTS_TRACKER_MODEL_TYPE = "yolo"
KEYPOINTS_TRACKER_LOAD_PATH = None
KEYPOINTS_TRACKER_SAVE_PATH = None # get_path("cache/keypoints_detections.json")

# SAM2 Tracker (Advanced Segmentation)
USE_SAM2 = True # Set to False if you don't have enough GPU memory
SAM2_MODEL_CONFIG = None # Ultralytics SAM handles config internally
SAM2_MODEL_WEIGHTS = get_path("weights/sam2_s.pt")

