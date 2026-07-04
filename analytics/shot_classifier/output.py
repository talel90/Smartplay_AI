import json
import os
from datetime import datetime
from typing import List, Dict

class ShotReportExporter:
    def __init__(self, output_path: str = "cache/shot_events.json"):
        self.output_path = output_path
        self.events = []
        self.bounces = []

    def add_event(self, frame_idx: int, player_id: int, shot_type: str, confidence: float, ball_speed: float):
        event = {
            "frame": frame_idx,
            "timestamp_sec": round(frame_idx / 30, 2),
            "player_id": player_id,
            "shot_type": shot_type,
            "confidence": round(confidence, 2),
            "ball_speed_px": round(ball_speed, 2)
        }
        self.events.append(event)

    def add_bounce(self, frame_idx: int, x_m: float, y_m: float, side: str):
        bounce = {
            "frame": frame_idx,
            "timestamp_sec": round(frame_idx / 30, 2),
            "x_m": round(x_m, 2),
            "y_m": round(y_m, 2),
            "side": side
        }
        self.bounces.append(bounce)

    def save(self):
        # Create summary
        summary = {}
        for event in self.events:
            pid = f"player_{event['player_id']}"
            stype = event["shot_type"]
            if pid not in summary: summary[pid] = {}
            summary[pid][stype] = summary[pid].get(stype, 0) + 1

        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_shots": len(self.events),
                "total_bounces": len(self.bounces)
            },
            "summary": summary,
            "shot_events": self.events,
            "bounce_events": self.bounces
        }

        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        with open(self.output_path, "w") as f:
            json.dump(report, f, indent=4)
        
        print(f"Report: Saved {len(self.events)} shots and {len(self.bounces)} bounces to {self.output_path}")
