"""
Shot Counter (Biomechanical Version)
======================================
Detects shots and classifies them (Smash, Bandeja, Forehand, Backhand) 
using player keypoints.
"""

from __future__ import annotations
import math
from collections import deque
from typing import Optional
import numpy as np
import cv2
from analytics.shot_classifier import PadelShotClassifier

# ── Constants ──────────────────────────────────────────────────────────────────
TEAM_LABELS   = {1: "A", 2: "A", 3: "B", 4: "B"}
PLAYER_DISPLAY = {1: "Player 1", 2: "Player 2", 3: "Player 3", 4: "Player 4"}

HUD_BG_COLOR, HUD_ALPHA = (15, 15, 15), 0.62
HUD_TEXT_COLOR = (240, 240, 240)
HUD_ACCENT_A, HUD_ACCENT_B, HUD_SHOT_COLOR = (90, 200, 90), (100, 160, 255), (255, 220, 0)

def _smooth_velocity(xys: list[tuple[float, float]]) -> Optional[tuple[float, float]]:
    if len(xys) < 2: return None
    dxs, dys = [], []
    for i in range(len(xys) - 1):
        dxs.append(xys[i + 1][0] - xys[i][0])
        dys.append(xys[i + 1][1] - xys[i][1])
    return (sum(dxs) / len(dxs), sum(dys) / len(dys))

def _speed(v: tuple[float, float]) -> float:
    return math.hypot(v[0], v[1])

def _cosine(v1: tuple[float, float], v2: tuple[float, float]) -> float:
    s1, s2 = _speed(v1), _speed(v2)
    if s1 < 1e-9 or s2 < 1e-9: return 1.0
    return (v1[0] * v2[0] + v1[1] * v2[1]) / (s1 * s2)

def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])

class ShotCounter:
    def __init__(self, proximity_px=180, cooldown_frames=25, velocity_window=5, direction_cos_threshold=0.1, speed_change_threshold=1.5, min_ball_speed_px=1.2, global_cooldown_frames=12):
        self.proximity_px = proximity_px
        self.cooldown_frames = cooldown_frames
        self.velocity_window = velocity_window
        self.direction_cos_threshold = direction_cos_threshold
        self.speed_change_threshold = speed_change_threshold
        self.min_ball_speed_px = min_ball_speed_px
        self.global_cooldown_frames = global_cooldown_frames
        
        self.shot_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        self.last_shot_type = {1: "", 2: "", 3: "", 4: ""}
        self._last_shot_frame = {pid: -9999 for pid in (1, 2, 3, 4)}
        self._global_ready_frame = 0
        W = velocity_window
        self._ball_history = deque(maxlen=W * 2)
        self._players_history = deque(maxlen=W * 2)
        self._kp_history = deque(maxlen=W * 2)
        self.classifier = PadelShotClassifier()

    def classify_shot(self, ball_xy, kp, post_vel, player_pxy, pid, frame_idx) -> str:
        """ 
        Advanced Rule-Based Classification.
        """
        label, conf = self.classifier.predict(ball_xy, kp, post_vel, player_pxy, pid, frame_idx)
        return label

    def process_frame(self, frame_idx, ball_xy, players_xy, is_bounce=False, players_kp=None):
        if ball_xy is None or not players_xy: return None
        self._ball_history.append((frame_idx, ball_xy[0], ball_xy[1], is_bounce))
        self._players_history.append(dict(players_xy))
        self._kp_history.append(dict(players_kp) if players_kp else {})
        W = self.velocity_window
        if len(self._ball_history) < W * 2: return None

        hist = list(self._ball_history)
        pre_vel = _smooth_velocity([(h[1], h[2]) for h in hist[:W]])
        post_vel = _smooth_velocity([(h[1], h[2]) for h in hist[W:]])
        if not pre_vel or not post_vel: return None
        pre_speed, post_speed = _speed(pre_vel), _speed(post_vel)
        if pre_speed < self.min_ball_speed_px or post_speed < self.min_ball_speed_px: return None

        cos = _cosine(pre_vel, post_vel)
        speed_ratio = post_speed / max(pre_speed, 0.1)
        
        # Core Hit Logic
        direction_ok = cos < self.direction_cos_threshold
        acceleration_ok = speed_ratio > self.speed_change_threshold
        
        if not (direction_ok or acceleration_ok): return None
        if frame_idx < self._global_ready_frame: return None
        if hist[W][3]: return None # Bounce filter

        mid_ball_xy = (hist[W][1], hist[W][2])
        mid_players = list(self._players_history)[W]
        mid_kps = list(self._kp_history)[W]
        
        best_dist, best_pid = float("inf"), None
        for pid, pxy in mid_players.items():
            d_center = _dist(mid_ball_xy, pxy)
            d_wrist = float("inf")
            kp = mid_kps.get(pid)
            if kp:
                wrists = []
                if hasattr(kp, 'keypoints_by_name'):
                    for name in ["left_wrist", "right_wrist", "left_hand", "right_hand"]:
                        w = kp.keypoints_by_name.get(name)
                        if w: wrists.append(w.xy)
                for wxy in wrists: d_wrist = min(d_wrist, _dist(mid_ball_xy, wxy))

            eff_dist = min(d_center, d_wrist)
            current_threshold = 150
            if post_speed > 3.0 and cos < 0.5:
                if mid_ball_xy[1] < 450: current_threshold = 250
                else: current_threshold = 200
            
            if d_wrist < 120: current_threshold = max(current_threshold, 180)

            per_cooldown_ok = frame_idx - self._last_shot_frame.get(pid, -9999) >= self.cooldown_frames
            if eff_dist <= current_threshold and per_cooldown_ok and eff_dist < best_dist:
                best_dist, best_pid = eff_dist, pid

        if best_pid:
            # Classification
            stype = self.classify_shot(
                mid_ball_xy, 
                mid_kps.get(best_pid), 
                post_vel, 
                mid_players.get(best_pid),
                best_pid,
                frame_idx
            )
            self.last_shot_type[best_pid] = stype
            
            self.shot_counts[best_pid] += 1
            self._last_shot_frame[best_pid] = frame_idx
            self._global_ready_frame = frame_idx + self.global_cooldown_frames
            return {"player_id": best_pid, "type": stype}
        return None

    def draw_hud(self, frame: np.ndarray, player_stats: Optional[dict] = None) -> np.ndarray:
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (480, 150), HUD_BG_COLOR, -1)
        frame = cv2.addWeighted(overlay, HUD_ALPHA, frame, 1 - HUD_ALPHA, 0)
        for i, pid in enumerate([1, 2, 3, 4]):
            ry = 45 + i * 25
            team = TEAM_LABELS.get(pid, "?")
            name = PLAYER_DISPLAY.get(pid, f"P{pid}")
            shots = self.shot_counts.get(pid, 0)
            last_t = self.last_shot_type.get(pid, "")
            stype_str = f"[{last_t}]" if last_t else ""
            
            color = HUD_ACCENT_A if team == "A" else HUD_ACCENT_B
            cv2.putText(frame, f"{team} | {name}: {shots} {stype_str}", (20, ry), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        return frame

    def get_shot_counts(self) -> dict[int, int]: return dict(self.shot_counts)
