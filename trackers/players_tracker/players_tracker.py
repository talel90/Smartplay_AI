from typing import Iterable, Literal, Type, Optional
import json
from pathlib import Path
import numpy as np
import cv2
import torch
from ultralytics import YOLO
import supervision as sv
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans

from utils import converters
from trackers.tracker import Object, Tracker, NoPredictFrames


class Player:

    """
    Player detection in a given video frame
    
    Attributes:
        detection: player bounding box detection
        projection: player position in a 2D court projection
    """

    def __init__(
        self, 
        detection: sv.Detections, 
        projection: Optional[tuple[int, int]] = None,
        team_id: Optional[int] = None,
        mask: Optional[np.ndarray] = None,
    ):
        self.detection = detection
        self.projection = projection
        self.team_id = team_id
        self.mask = mask
        self.xyxy = detection.xyxy[0]
        self.id = (
            int(detection.tracker_id[0]) 
            if detection.tracker_id 
            else None
        )
        self.class_id = int(detection.class_id[0])
        self.confidence = float(detection.confidence[0])
        self.team_id = team_id
       
    @property
    def top_left(self) -> tuple[int, int]:
        return tuple(
            int(p)
            for p in self.xyxy[:2]
        )
    
    @property
    def bottom_right(self) -> tuple[int, int]:
        return tuple(
            int(p)
            for p in self.xyxy[2:]
        )
    
    @property
    def height(self) -> float:
        return self.bottom_right[1] - self.top_left[1]
    
    @property
    def width(self) -> float:
        return self.bottom_right[0] - self.top_left[0]
    
    @property
    def midpoint(self) -> tuple[int, int]:
        return (
            int(self.top_left[0] + self.width / 2),
            int(self.top_left[1] + self.height / 2),
        )
    
    @property
    def feet(self) -> tuple[int, int]:
        """
        Get player's court position from their segmentation mask (if available) 
        or bounding box.
        """
        if self.mask is not None:
            # Use the literal lowest part of the mask (the shoes)
            y_coords, x_coords = np.where(self.mask > 0)
            if len(y_coords) > 0:
                # Use percentile and mean to be robust against outliers
                foot_y = np.percentile(y_coords, 98) # Very bottom
                foot_x = np.mean(x_coords[y_coords > foot_y - 5])
                return (int(foot_x), int(foot_y))
                
        # Fallback to bounding box bottom center
        return (
            int(self.top_left[0] + self.width / 2),
            int(self.bottom_right[1]),
        )
    
    @classmethod
    def from_json(cls, x: dict):
        try:
            projection = x["projection"]
        except KeyError:
            projection = None
            
        detection = sv.Detections(
            xyxy=np.array([x["xyxy"]]),
            confidence=np.array([x["confidence"]]),
            tracker_id=np.array([x["id"]]),
            class_id=np.array([x["class_id"]]),
        )
        return cls(detection=detection, projection=projection)

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "xyxy": [float(p) for p in self.xyxy],
            "projection": self.projection,
            "class_id": self.class_id,
            "confidence": self.confidence,
        }

    def draw(
        self, 
        frame: np.ndarray, 
        video_info: sv.VideoInfo,
        annotator: Optional[str] = None, # Kept for signature compatibility
        show_confidence: bool = True,
    ) -> np.ndarray:
        """
        Draw player detection as a circle at their feet and optional segmentation mask
        """
        
        # Color for the player circle
        if self.team_id == 0:
            color = (0, 0, 255) # Red for Team 1
        elif self.team_id == 1:
            color = (255, 0, 0) # Blue for Team 2
        else:
            color = (0, 255, 0) # Green fallback

        # 1. Draw mask if available
        if self.mask is not None:
            # Create a semi-transparent overlay for the mask
            mask_layer = np.zeros_like(frame, dtype=np.uint8)
            mask_layer[self.mask > 0] = color
            frame = cv2.addWeighted(frame, 1.0, mask_layer, 0.4, 0)
            
            # Draw a thin contour around the mask
            contours, _ = cv2.findContours(
                self.mask.astype(np.uint8), 
                cv2.RETR_EXTERNAL, 
                cv2.CHAIN_APPROX_SIMPLE
            )
            cv2.drawContours(frame, contours, -1, color, 2)
        
        # 2. Draw circle at feet
        feet_pos = self.feet
        
        # Draw circle at feet
        cv2.circle(
            frame,
            feet_pos,
            12, # Radius
            color,
            -1 # Filled
        )
        
        # Draw player ID above the feet with a background box for clarity
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2
        label = f"Player {self.id}"
        if self.team_id is not None:
            label += f" (T{self.team_id+1})"
        if show_confidence:
            label += f" ({self.confidence:.2f})"
            
        # Get text size for background box
        (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
        
        # Position label slightly above the feet circle
        text_x = feet_pos[0] - text_width // 2
        text_y = feet_pos[1] - 25
        
        # Draw background rectangle
        cv2.rectangle(
            frame,
            (text_x - 5, text_y - text_height - 5),
            (text_x + text_width + 5, text_y + 5),
            color, # Use the same color as the feet circle
            -1 # Filled
        )
        
        # Draw white text on the box
        cv2.putText(
            frame,
            label,
            (text_x, text_y),
            font,
            font_scale,
            (255, 255, 255), # White text
            thickness
        )

        return frame
    
    def draw_projection(self, frame: np.ndarray) -> np.ndarray:
        if self.projection:
            cv2.circle(
                frame,
                self.projection,
                8,
                (0, 0, 255),
                -1,
            )

            cv2.putText(
                frame, 
                str(self.id),
                (
                    self.projection[0], 
                    self.projection[1] - 10,
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 0, 255),
                2,
            )

            return frame
        else:
            raise ValueError("Inexistent projection.")
    

class Players(Object):

    """
    Players detection in a given video frame
    """

    def __init__(self, players: list[Player]):
        super().__init__()
        self.players = players

    @classmethod
    def from_json(cls, x: list[dict]) -> "Players":
        return cls(
            players=[
                Player.from_json(player_json)
                for player_json in x
            ]
        )

    def serialize(self) -> list[dict]:
        return [
            player.serialize()
            for player in self.players
        ]

    def __len__(self) -> int:
        return len(self.players)

    def __iter__(self) -> Iterable[Player]:
        return (player for player in self.players)
    
    def __getitem__(self, i: int) -> Player:
        return self.players[i]
    
    def draw(
        self, 
        frame: np.ndarray, 
        video_info: sv.VideoInfo,
        annotator: Literal[
            "rectangle_bounding_box",
            "round_bounding_box",
            "corner_bounding_box",
            "ellipse"
        ] = "rectangle_bounding_box",
        show_confidence: bool = True,
    ) -> np.ndarray:
        """
        Draw players detection in a given frame

        Parameters:
            frame: frame of interest
            video_info: source video information like fps and resolution
            annotator: bounding box style
            show_confidence: True to write detection confidence
        """
    
        for player in self.players:
            frame = player.draw(
                frame, 
                video_info, 
                annotator, 
                show_confidence,
            )

        return frame


class PlayerTracker(Tracker):

    """
    Tracker of players object with Static Appearance ReID
    """

    CONF = 0.5
    IOU = 0.7
    IMGSZ = 1280

    def __init__(
        self, 
        model_path: str,
        polygon_zone: sv.PolygonZone,
        batch_size: int,
        annotator: Literal[
            "rectangle_bounding_box",
            "round_bounding_box",
            "corner_bounding_box",
            "ellipse"
        ] = "rectangle_bounding_box",
        show_confidence: bool = True,
        load_path: Optional[str | Path] = None,
        save_path: Optional[str | Path] = None,
    ):
        super().__init__(
            load_path=load_path,
            save_path=save_path,
        )

        self.model = YOLO(model_path)
        self.polygon_zone = polygon_zone
        self.batch_size = batch_size
        self.annotator = annotator
        self.show_confidence = show_confidence

    def video_info_post_init(self, video_info: sv.VideoInfo) -> "PlayerTracker":
        self.video_info = video_info
        
        # Static ID management state
        self.max_players = 4
        self.initialized = False
        
        # {stable_id: {"bbox": xyxy, "velocity": np.array([0,0]), "missed": 0, "embedding": np.array([r, g, b])}}
        self.registered_profiles = {} 
        return self

    def object(self) -> Type[Object]:
        return Players

    def draw_kwargs(self) -> dict:
        return {
            "video_info": self.video_info,
            "annotator": self.annotator,
            "show_confidence": self.show_confidence,
        }
    
    def __str__(self) -> str:
        return "players_tracker"
    
    def restart(self) -> None:
        """
        Reset the tracking results
        """
        self.results.restart()
        print(f"{self.__str__()}: Tracker reset")
        self.initialized = False
        self.registered_profiles = {}

    def processor(self, frame: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    def to(self, device: str) -> None:
        self.model.to(device)

    def _get_center(self, bbox):
        return np.array([(bbox[0]+bbox[2])/2.0, (bbox[1]+bbox[3])/2.0])

    def _get_embedding(self, frame_rgb, bbox):
        """Extract mean color from the top 40% of the bounding box (torso)"""
        x1, y1, x2, y2 = map(int, bbox)
        
        h, w = frame_rgb.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)
        
        if x2 <= x1 or y2 <= y1:
            return np.zeros(3)
            
        y2_torso = y1 + int(0.4 * (y2 - y1))
        torso_crop = frame_rgb[y1:y2_torso, x1:x2]
        
        if torso_crop.size == 0:
            return np.zeros(3)
            
        # Add a light blur to reduce noise
        torso_crop = cv2.GaussianBlur(torso_crop, (5, 5), 0)
        mean_color = np.mean(torso_crop, axis=(0, 1))
        return mean_color

    def predict_sample(self, sample: Iterable[np.ndarray], **kwargs) -> list[Players]:
        """
        Prediction over a sample of frames with static Appearance-based ReID.
        """

        frames_rgb = [
            self.processor(frame)
            for frame in sample
        ]

        results = self.model.predict(
            frames_rgb, 
            conf=self.CONF,
            iou=self.IOU,
            imgsz=self.IMGSZ,
            device=self.DEVICE,
            classes=[0],
            verbose=False
        )

        predictions = []
        for frame_idx, (result, frame_rgb) in enumerate(zip(results, frames_rgb)):
            raw_detections = sv.Detections.from_ultralytics(result)
            
            # Filter inside polygon zone
            in_zone = self.polygon_zone.trigger(raw_detections)
            filtered_detections = raw_detections[in_zone]
            
            # Extract detections for processing
            current_dets = []
            for i in range(len(filtered_detections)):
                bbox = filtered_detections.xyxy[i]
                conf = filtered_detections.confidence[i]
                class_id = filtered_detections.class_id[i]
                embedding = self._get_embedding(frame_rgb, bbox)
                current_dets.append({
                    "bbox": bbox, 
                    "conf": conf, 
                    "class_id": class_id,
                    "embedding": embedding
                })

            # 1. Initialization phase
            if not self.initialized:
                if len(current_dets) == self.max_players:
                    # Robust Padel Team Assignment: 2 Top, 2 Bottom
                    # Sort by Y-coordinate (top of bounding box)
                    current_dets = sorted(current_dets, key=lambda x: x["bbox"][1])
                    
                    for i, det in enumerate(current_dets):
                        sid = i + 1
                        # Top two players (smaller Y) are Team 0, Bottom two are Team 1
                        team_id = 0 if i < 2 else 1
                        
                        self.registered_profiles[sid] = {
                            "bbox": det["bbox"],
                            "velocity": np.array([0.0, 0.0]),
                            "predicted_bbox": det["bbox"],
                            "missed": 0,
                            "embedding": det["embedding"],
                            "team_id": team_id
                        }
                    self.initialized = True
                    print(f"[{self.__str__()}] Locked IDs 1-{self.max_players} based on court side (Top 2 vs Bottom 2)")
                else:
                    # Not initialized, return empty
                    predictions.append(Players([]))
                    continue
            
            # 2. Tracking Phase
            for sid, track in self.registered_profiles.items():
                if track["missed"] >= 0:
                    velocity = track["velocity"]
                    pred_bbox = track["bbox"].copy()
                    pred_bbox[0] += velocity[0]
                    pred_bbox[2] += velocity[0]
                    pred_bbox[1] += velocity[1]
                    pred_bbox[3] += velocity[1]
                    
                    pred_center = self._get_center(pred_bbox)
                    is_inside = cv2.pointPolygonTest(
                        self.polygon_zone.polygon, 
                        (float(pred_center[0]), float(pred_center[1])), 
                        False
                    ) >= 0
                    
                    if is_inside:
                        track["predicted_bbox"] = pred_bbox
                    else:
                        track["predicted_bbox"] = track["bbox"].copy()
                        track["velocity"] = np.array([0.0, 0.0])

            matched_sids = set()
            new_stable_detections_list = []
            
            num_tracks = self.max_players
            num_dets = len(current_dets)
            
            if num_tracks > 0 and num_dets > 0:
                cost_matrix = np.zeros((num_tracks, num_dets))
                track_sids = list(self.registered_profiles.keys())
                
                for r, sid in enumerate(track_sids):
                    track = self.registered_profiles[sid]
                    pred_center = self._get_center(track["predicted_bbox"])
                    track_emb = track["embedding"]
                    
                    for c, det in enumerate(current_dets):
                        det_center = self._get_center(det["bbox"])
                        det_emb = det["embedding"]
                        
                        spatial_dist = np.linalg.norm(pred_center - det_center)
                        color_dist = np.linalg.norm((track_emb - det_emb) / 255.0) * 100.0 # scale heavily
                        
                        # Penalize heavy spatial leaps (e.g. crossing net instantly)
                        if spatial_dist > 300.0:
                            cost_matrix[r, c] = 10000.0
                        else:
                            penalty = track["missed"] * 5.0 
                            cost_matrix[r, c] = spatial_dist + color_dist * 2.0 + penalty

                row_ind, col_ind = linear_sum_assignment(cost_matrix)
                
                matched_indices = []
                for r, c in zip(row_ind, col_ind):
                    if cost_matrix[r, c] < 10000.0:
                        sid = track_sids[r]
                        det = current_dets[c]
                        bbox = det["bbox"]
                        track = self.registered_profiles[sid]
                        
                        curr_center = self._get_center(bbox)
                        prev_center = self._get_center(track["bbox"])
                        inst_vel = curr_center - prev_center
                        
                        if track["missed"] > 5:
                            track["velocity"] = np.array([0.0, 0.0])
                        else:
                            alpha_vel = 0.5
                            track["velocity"] = alpha_vel * inst_vel + (1 - alpha_vel) * track["velocity"]
                        
                        # EMA on Appearance
                        alpha_emb = 0.1
                        track["embedding"] = alpha_emb * det["embedding"] + (1 - alpha_emb) * track["embedding"]
                        
                        track["bbox"] = bbox
                        track["predicted_bbox"] = bbox
                        track["missed"] = 0
                        matched_sids.add(sid)
                        
                        single_det = sv.Detections(
                            xyxy=np.array([bbox]),
                            confidence=np.array([det["conf"]]),
                            class_id=np.array([det["class_id"]]),
                            tracker_id=np.array([sid])
                        )
                        new_stable_detections_list.append(single_det)
                        matched_indices.append(c)

            # 3. Missing Players
            for sid, track in list(self.registered_profiles.items()):
                if sid not in matched_sids:
                    track["missed"] += 1
                    
                    # Hold slot for up to 90 frames (approx 3 seconds)
                    if track["missed"] < 90:
                        pred_bbox = track["predicted_bbox"]
                        track["bbox"] = pred_bbox
                        
                        pred_det = sv.Detections(
                            xyxy=np.array([pred_bbox]),
                            confidence=np.array([0.1]), # Very low confidence placeholder
                            class_id=np.array([0]),
                            tracker_id=np.array([sid])
                        )
                        # Optionally comment out the next line if you don't want to draw missing predicted players
                        new_stable_detections_list.append(pred_det)

            if new_stable_detections_list:
                final_detections = sv.Detections.merge(new_stable_detections_list)
            else:
                final_detections = sv.Detections.empty()

            predictions.append(
                Players(
                    [
                        Player(
                            detection=final_detections[i],
                            team_id=self.registered_profiles[int(final_detections.tracker_id[i])]["team_id"]
                            if final_detections.tracker_id is not None and final_detections.tracker_id[i] is not None
                            else None
                        )
                        for i in range(len(final_detections))
                        if final_detections.tracker_id is not None and final_detections.tracker_id[i] is not None
                    ]
                )
            )

        return predictions

    
    def predict_frames(self, frame_generator: Iterable[np.ndarray], **kwargs):
        raise NoPredictFrames()
        