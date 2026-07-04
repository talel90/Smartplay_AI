import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class ShotFeatures:
    player_id: int
    frame_idx: int
    
    # Ball Trajectory
    ball_speed: float
    ball_vertical_vel: float # positive is DOWN
    ball_angle: float
    
    # Biomechanics
    rel_height: float # positive is ABOVE head
    arm_extension: float # px distance shoulder to wrist
    is_overhead: bool
    
    # Court Context
    is_top_player: bool
    is_ball_right_of_player: bool
    near_net: bool = False
    
class FeatureExtractor:
    def __init__(self, frame_height: int = 1080):
        self.frame_height = frame_height

    def get_dist(self, p1, p2):
        return np.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def extract(self, ball_xy, kp, post_vel, player_pxy, net_y=540) -> Optional[ShotFeatures]:
        if not kp or not hasattr(kp, 'keypoints_by_name'):
            return None

        # 1. Get Keypoints
        head = kp.keypoints_by_name.get("nose") or kp.keypoints_by_name.get("head")
        l_shoulder = kp.keypoints_by_name.get("left_shoulder")
        r_shoulder = kp.keypoints_by_name.get("right_shoulder")
        l_wrist = kp.keypoints_by_name.get("left_wrist")
        r_wrist = kp.keypoints_by_name.get("right_wrist")

        if not head or not l_shoulder or not r_shoulder:
            return None

        # 2. Body Geometry
        shoulder_y = (l_shoulder.xy[1] + r_shoulder.xy[1]) / 2
        shoulder_x = (l_shoulder.xy[0] + r_shoulder.xy[0]) / 2
        
        # Closest wrist to ball at impact
        d_lw = self.get_dist(ball_xy, l_wrist.xy) if l_wrist else 9999
        d_rw = self.get_dist(ball_xy, r_wrist.xy) if r_wrist else 9999
        dominant_wrist = l_wrist if d_lw < d_rw else r_wrist
        dominant_shoulder = l_shoulder if d_lw < d_rw else r_shoulder
        
        arm_ext = 0
        if dominant_wrist:
            arm_ext = self.get_dist(dominant_shoulder.xy, dominant_wrist.xy)

        # 3. Ball Trajectory
        v_speed = np.hypot(post_vel[0], post_vel[1])
        v_vert = post_vel[1] # positive = moving down
        v_angle = np.degrees(np.arctan2(post_vel[1], post_vel[0]))

        # 4. Context
        is_overhead = ball_xy[1] < head.xy[1] - 20
        is_top = shoulder_y < net_y
        is_right = ball_xy[0] > shoulder_x
        
        # Simple "Near Net" check (within 15% of net line)
        near_net = abs(shoulder_y - net_y) < (self.frame_height * 0.15)

        return ShotFeatures(
            player_id=0, # set by caller
            frame_idx=0, # set by caller
            ball_speed=v_speed,
            ball_vertical_vel=v_vert,
            ball_angle=v_angle,
            rel_height=head.xy[1] - ball_xy[1],
            arm_extension=arm_ext,
            is_overhead=is_overhead,
            is_top_player=is_top,
            is_ball_right_of_player=is_right,
            near_net=near_net
        )
