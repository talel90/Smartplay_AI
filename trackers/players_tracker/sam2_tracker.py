import numpy as np
import torch
import cv2
from typing import Iterable, Optional, Type
from pathlib import Path
import supervision as sv
from ultralytics import SAM

from trackers.tracker import Object, Tracker
from trackers.players_tracker.players_tracker import Player, Players, PlayerTracker

class SAM2PlayerTracker(PlayerTracker):
    """
    Advanced Player Tracker using YOLO for robust ID management 
    and Ultralytics-native SAM2 for pixel-perfect masks.
    """

    def __init__(
        self, 
        model_path: str,
        sam2_weights: str,
        sam2_config: Optional[str], # Kept for signature compatibility
        polygon_zone: sv.PolygonZone,
        batch_size: int,
        device: str = "cuda",
        **kwargs
    ):
        super().__init__(
            model_path=model_path,
            polygon_zone=polygon_zone,
            batch_size=batch_size,
            **kwargs
        )
        
        # Load the SAM2 model via Ultralytics (much more robust than raw hydra init)
        # Note: Ultralytics SAM2 expects sam2_s.pt or similar. 
        # The file we downloaded 'sam2_hiera_small.pt' is compatible.
        self.sam2_model = SAM(sam2_weights)
        self.sam2_initialized = False

    def init_video_state(self, video_path: str):
        """Native Ultralytics SAM handles state automatically during .track()"""
        self.sam2_initialized = False

    def predict_sample(self, sample: Iterable[np.ndarray], **kwargs) -> list[Players]:
        """
        Prediction over a sample of frames with YOLO StaticID + SAM2 masks.
        """
        # 1. Get YOLO + StaticID detections from parent
        yolo_frames_predictions = super().predict_sample(sample, **kwargs)
        
        final_predictions = []
        for i, (players_obj, frame) in enumerate(zip(yolo_frames_predictions, sample)):
            if not self.initialized or len(players_obj.players) == 0:
                final_predictions.append(players_obj)
                continue

            # 2. Extract bounding boxes from YOLO to prompt SAM2
            # Boxes format: [x1, y1, x2, y2]
            prompt_bboxes = [p.xyxy for p in players_obj.players]
            
            # 3. Prompt SAM2 to get masks
            # Note: persist=True and using the same frame sequence maintains temporal memory
            # Inside ultralytics SAM.track()
            # We use .predict instead of .track if we want to manually feed YOLO boxes as prompts
            sam2_results = self.sam2_model.predict(
                frame,
                bboxes=prompt_bboxes,
                verbose=False,
                device=self.DEVICE
            )
            
            if len(sam2_results) > 0 and sam2_results[0].masks is not None:
                # Map masks back to players (they should be in the same order as prompt_bboxes)
                all_masks = sam2_results[0].masks.data.cpu().numpy() # (N, H, W)
                
                for j, player in enumerate(players_obj.players):
                    if j < len(all_masks):
                        player.mask = all_masks[j].astype(bool)
            
            final_predictions.append(players_obj)

        return final_predictions

    def __str__(self) -> str:
        return "sam2_players_tracker"
