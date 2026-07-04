import numpy as np
import pandas as pd
from typing import List, Dict, Optional

class BiomechanicalFeatureExtractor:
    """
    Advanced extractor for biomechanical features (angles, velocities, poses)
    to train powerful Deep Learning models.
    """
    
    def __init__(self, window_size: int = 15):
        self.window_size = window_size
        self.dataset = []

    def get_angle(self, p1, p2, p3):
        """Calculates the angle between three points (p1-p2-p3)."""
        if p1 is None or p2 is None or p3 is None:
            return 0
        v1 = np.array(p1) - np.array(p2)
        v2 = np.array(p3) - np.array(p2)
        
        # Avoid division by zero
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0
            
        cosine_angle = np.dot(v1, v2) / (norm1 * norm2)
        angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
        return np.degrees(angle)

    def extract_features(
        self, 
        frame_idx: int, 
        player_id: int,
        ball_history: List[dict],
        player_kp_history: List[dict],
        player_pos_m_history: List[dict],
    ) -> Optional[dict]:
        """
        Extracts a rich vector of biomechanical features for a 31-frame window.
        """
        if len(player_kp_history) < 2 * self.window_size + 1:
            return None
            
        features = {"frame": frame_idx, "player_id": player_id}
        
        # 1. Temporal Pose Sequence
        # We record the angles of the dominant arm (the one closest to the ball at impact)
        # to see the preparation and follow-through.
        
        # Find dominant hand at impact (middle of history)
        impact_kp = player_kp_history[self.window_size].get(player_id)
        impact_ball = ball_history[self.window_size]['xy']
        
        if not impact_kp or not impact_ball:
            return None
            
        # Determine if player is right or left handed for this shot based on proximity
        d_left = np.hypot(impact_ball[0] - impact_kp['left_hand'].xy[0], impact_ball[1] - impact_kp['left_hand'].xy[1])
        d_right = np.hypot(impact_ball[0] - impact_kp['right_hand'].xy[0], impact_ball[1] - impact_kp['right_hand'].xy[1])
        side = "left" if d_left < d_right else "right"
        
        for t in range(len(player_kp_history)):
            kp = player_kp_history[t].get(player_id)
            if kp:
                # Arm Angle
                shoulder = kp[f'{side}_shoulder'].xy
                elbow = kp[f'{side}_elbow'].xy
                wrist = kp[f'{side}_hand'].xy
                angle = self.get_angle(shoulder, elbow, wrist)
                features[f"arm_angle_{t-self.window_size}"] = angle
                
                # Shoulder Rotation (width in pixels as proxy)
                l_sh = kp['left_shoulder'].xy
                r_sh = kp['right_shoulder'].xy
                features[f"sh_width_{t-self.window_size}"] = abs(l_sh[0] - r_sh[0])
                
                # Ball Proximity
                b_xy = ball_history[t]['xy']
                if b_xy:
                    dist = np.hypot(b_xy[0] - wrist[0], b_xy[1] - wrist[1])
                    features[f"ball_dist_{t-self.window_size}"] = dist
                else:
                    features[f"ball_dist_{t-self.window_size}"] = 1000 # Max dist
            else:
                features[f"arm_angle_{t-self.window_size}"] = 0
                features[f"sh_width_{t-self.window_size}"] = 0
                features[f"ball_dist_{t-self.window_size}"] = 1000
                
        # 2. Global Court Position
        impact_pos = player_pos_m_history[self.window_size].get(player_id)
        if impact_pos:
            features["player_x_m"] = impact_pos[0]
            features["player_y_m"] = impact_pos[1]
            
        # 3. Relative Height
        features["impact_height"] = impact_kp['head'].xy[1] - impact_ball[1]
        
        return features
