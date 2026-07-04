import numpy as np
import pandas as pd
from typing import List, Dict, Optional
import os

class ShotFeatureExtractor:
    """
    Extracts time-series features around ball-wrist impact for shot classification.
    """
    
    def __init__(self, window_size: int = 10):
        self.window_size = window_size # Frames before and after impact
        self.dataset = []

    def get_hand_keypoint(self, player_keypoints, side: str = "closest", ball_xy: tuple = (0,0)):
        """
        Extracts the wrist/hand keypoint from the player.
        """
        try:
            lh = player_keypoints["left_hand"].xy
            rh = player_keypoints["right_hand"].xy
            
            if side == "closest":
                dist_l = np.hypot(ball_xy[0] - lh[0], ball_xy[1] - lh[1])
                dist_r = np.hypot(ball_xy[0] - rh[0], ball_xy[1] - rh[1])
                return lh if dist_l < dist_r else rh
            return rh # Default to right hand
        except:
            return None

    def extract_features(
        self, 
        frame_idx: int, 
        player_id: int,
        ball_history: List[dict], # List of {'xy': (x,y), 'xy_m': (x,y)}
        player_kp_history: List[dict], # List of {'keypoints': PlayerKeypoints}
        player_pos_m_history: List[dict],
    ) -> Optional[dict]:
        """
        Calculates feature vector for a window around frame_idx.
        """
        if len(ball_history) < 2 * self.window_size + 1:
            return None
            
        features = {"frame": frame_idx, "player_id": player_id}
        
        proximities = []
        for i in range(len(ball_history)):
            b_xy = ball_history[i]['xy']
            p_kp = player_kp_history[i].get(player_id)
            
            if b_xy and p_kp:
                hand_xy = self.get_hand_keypoint(p_kp, ball_xy=b_xy)
                if hand_xy:
                    dist = np.hypot(b_xy[0] - hand_xy[0], b_xy[1] - hand_xy[1])
                    proximities.append(dist)
                else:
                    proximities.append(np.nan)
            else:
                proximities.append(np.nan)
        
        # Fill NaNs
        proximities = pd.Series(proximities).interpolate().tolist()
        
        if any(np.isnan(proximities)):
            return None
            
        # Time series features
        for idx, dist in enumerate(proximities):
            features[f"prox_{idx - self.window_size}"] = dist
            
        # Aggregated features
        features["min_dist"] = np.min(proximities)
        features["mean_dist"] = np.mean(proximities)
        
        # Relative height at impact (y in frame)
        impact_ball_y = ball_history[self.window_size]['xy'][1]
        impact_player_head_y = player_kp_history[self.window_size].get(player_id)['head'].xy[1]
        features["rel_height"] = impact_player_head_y - impact_ball_y # Positive if ball is above head
        
        # Court position
        impact_player_pos_m = player_pos_m_history[self.window_size].get(player_id)
        if impact_player_pos_m:
            features["player_y_m"] = impact_player_pos_m[1]
            features["player_x_m"] = impact_player_pos_m[0]
            
        return features

    def save_to_csv(self, output_path: str = "shot_features.csv"):
        if not self.dataset:
            return
        df = pd.DataFrame(self.dataset)
        df.to_csv(output_path, index=False)
        print(f"Features saved to {output_path}")
