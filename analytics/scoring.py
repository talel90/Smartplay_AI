import numpy as np
import pandas as pd
import cv2
import os
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum
import joblib
from analytics.shot_counter import ShotCounter
from analytics.shot_classifier import ShotReportExporter

class RallyState(Enum):
    IDLE = "IDLE"
    IN_PLAY = "IN_PLAY"
    BOUNCED = "BOUNCED"
    POINT_ENDED = "POINT_ENDED"

@dataclass
class RallyEvent:
    frame: int
    type: str  # "bounce", "hit", "net", "out"
    side: str  # "top", "bottom"
    player_id: Optional[int] = None
    x_m: float = 0.0
    y_m: float = 0.0

class PadelScorer:
    """
    Automated Padel Scoring Engine using robust ShotCounter and trajectory analysis.
    """
    
    def __init__(self, reporter_output_path: Optional[str] = None):
        # Match Score
        self.score_top = 0
        self.score_bottom = 0
        self.score_labels = ["0", "15", "30", "40", "Game"]
        
        # Robust Shot Counter Integration (Balanced Stable Logic)
        self.shot_counter = ShotCounter(
            proximity_px=180,           
            cooldown_frames=25,
            direction_cos_threshold=0.0, # Neutral
            speed_change_threshold=1.6,  # Balanced
            min_ball_speed_px=1.5
        )
        
        # Shot Reporter (JSON Analytics)
        self.reporter = ShotReportExporter(
            output_path=reporter_output_path or "cache/shot_events.json"
        )
        
        # State
        self.player_shoots = {1: 0, 2: 0, 3: 0, 4: 0}
        self.last_shot_type = {}
        self.rally_events: List[RallyEvent] = []
        self.point_in_progress = True
        self.hit_cooldown = 0
        self.ball_history = []
        
        # FSM for Scoring
        self.state = RallyState.IDLE
        self.last_hitter_side = None
        self.last_bounce_side = None
        self.bounce_count = 0

    def reset_rally(self):
        self.rally_events = []
        self.point_in_progress = True
        self.state = RallyState.IDLE
        self.last_hitter_side = None
        self.last_bounce_side = None
        self.bounce_count = 0

    def process_frame(self, frame_idx: int, ball_pos_m: Optional[tuple], is_bounce: bool, players_pos_m: Dict[int, tuple], 
                      players_kp: Optional[Dict[int, any]] = None, ball_xy: Optional[tuple] = None, players_xy: Dict[int, tuple] = None):
        """
        Main logic to determine point status and player shoots.
        """
        # 1. Use the robust ShotCounter for hits (shoots)
        if ball_xy is None: return
        
        # Pass keypoints to the counter
        shot_data = self.shot_counter.process_frame(
            frame_idx=frame_idx,
            ball_xy=ball_xy,
            players_xy=players_xy,
            is_bounce=is_bounce,
            players_kp=players_kp
        )
        
        # Sync counts and types
        if shot_data:
            pid = shot_data["player_id"]
            stype = shot_data["type"]
            self.player_shoots = self.shot_counter.get_shot_counts()
            self.last_shot_type[pid] = stype
            
            # Log to JSON Report
            self.reporter.add_event(
                frame_idx=frame_idx,
                player_id=pid,
                shot_type=stype,
                confidence=1.0, # Rule-based is high confidence by default
                ball_speed=0.0 # Could be extracted if needed
            )
            
            print(f"PadelScorer: Player {pid} hit a {stype}")
            
            # Determine hitter side
            hitter_side = None
            if pid in players_pos_m:
                hitter_side = "top" if players_pos_m[pid][1] < 0 else "bottom"
            else:
                # Fallback to Team Labels if position is missing
                hitter_side = "top" if pid in [1, 2] else "bottom"
            
            event = RallyEvent(
                frame=frame_idx,
                type="hit",
                side=hitter_side,
                player_id=pid
            )
            self.rally_events.append(event)
            self._update_fsm(event)

        if ball_pos_m is None:
            return

        # Determine side (y=0 is net, y < 0 is TOP, y > 0 is BOTTOM)
        side = "top" if ball_pos_m[1] < 0 else "bottom"
        
        # 2. Handle ground bounces for scoring rules
        if is_bounce:
            event = RallyEvent(
                frame=frame_idx,
                type="bounce",
                side=side,
                x_m=ball_pos_m[0],
                y_m=ball_pos_m[1]
            )
            self.rally_events.append(event)
            
            # Log to JSON Report
            if hasattr(self, 'reporter'):
                self.reporter.add_bounce(
                    frame_idx=frame_idx,
                    x_m=ball_pos_m[0],
                    y_m=ball_pos_m[1],
                    side=side
                )
                
            self._update_fsm(event)

    def _update_fsm(self, event: RallyEvent):
        """
        Finite State Machine for Padel Rules.
        Rule: Point ends when ball bounces 2 times successively on the same side.
        """
        if not self.point_in_progress:
            if event.type == "hit":
                self.reset_rally()
                # Continue processing this hit
            else:
                return

        if event.type == "hit":
            self.state = RallyState.IN_PLAY
            self.last_hitter_side = event.side
            self.bounce_count = 0
            self.last_bounce_side = None # Reset side tracking on hit
            # print(f"FSM: Hit by {event.side}. Resetting bounce count.")

        elif event.type == "bounce":
            if self.last_hitter_side is None:
                return

            if event.side == self.last_bounce_side:
                self.bounce_count += 1
            else:
                self.last_bounce_side = event.side
                self.bounce_count = 1
            
            self.state = RallyState.BOUNCED
            # print(f"FSM: Bounce on {event.side} (Count: {self.bounce_count})")

            if self.bounce_count >= 2:
                # 2 successive bounces on the SAME side -> Side that let it bounce twice loses.
                winner = "top" if event.side == "bottom" else "bottom"
                # print(f"FSM: 2 Successive Bounces on {event.side}! Winner: {winner}")
                self._award_point(winner)

    def _check_point_end(self):
        """Deprecated in favor of _update_fsm, but kept for compatibility."""
        pass

    def _award_point(self, winner: str):
        if winner == "top":
            self.score_top += 1
        else:
            self.score_bottom += 1
        self.point_in_progress = False
        print(f"POINT ENDED! Winner: {winner.upper()}. Score: {self.get_score_str()}")

    def get_score_str(self) -> str:
        s_t = self.score_labels[min(self.score_top, 4)]
        s_b = self.score_labels[min(self.score_bottom, 4)]
        return f"TOP {s_t} - {s_b} BOTTOM"

    def draw_score(self, frame, frame_idx=0, players_detection=None):
        """
        Draw stats HUD, Match Score, and Player labels.
        """
        # 1. Draw the semi-transparent HUD (Shots, Speed, Dist)
        frame = self.shot_counter.draw_hud(frame)
        
        # 2. Draw Match Score (Prominent Box)
        score_txt = self.get_score_str()
        state_txt = f"STATE: {self.state.value}"
        (w, h), _ = cv2.getTextSize(score_txt, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
        (sw, sh), _ = cv2.getTextSize(state_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        
        cv2.rectangle(frame, (frame.shape[1] - w - 40, 10), (frame.shape[1] - 10, 60 + sh + 20), (0, 0, 0), -1)
        cv2.putText(frame, score_txt, (frame.shape[1] - w - 25, 45), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, state_txt, (frame.shape[1] - sw - 25, 45 + sh + 15), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if self.point_in_progress else (0, 0, 255), 2, cv2.LINE_AA)

        # 3. Draw Frame Index (Top Center)
        frame_txt = f"FRAME: {frame_idx}"
        cv2.putText(frame, frame_txt, (int(frame.shape[1]/2) - 100, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3, cv2.LINE_AA)

        # 4. Draw per-player badges
        if players_detection:
            for player in players_detection:
                pid = player.id
                x1, y1, x2, y2 = player.xyxy
                shots = self.player_shoots.get(pid, 0)
                stype = self.last_shot_type.get(pid, "")
                label = f"P{pid} {stype}: {shots}"
                (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(frame, (int(x1), int(y1) - lh - 15), (int(x1) + lw + 10, int(y1) - 5), (0, 0, 0), -1)
                cv2.rectangle(frame, (int(x1), int(y1) - lh - 15), (int(x1) + lw + 10, int(y1) - 5), (0, 255, 0), 2)
                cv2.putText(frame, label, (int(x1) + 5, int(y1) - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        return frame
