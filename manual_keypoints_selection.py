"""
Select the 12 padel court keypoints on the first frame of a video (OpenCV GUI).

Uses paths from config.py by default. Saves to FIXED_COURT_KEYPOINTS_SAVE_PATH.

Court diagram (same order as main.py):

        k11--------------------k12
        |                       |
        k8-----------k9--------k10
        |            |          |
        |            |          |
        |            |          |
        k6----------------------k7
        |            |          |
        |            |          |
        |            |          |
        k3-----------k4---------k5
        |                       |
        k1----------------------k2

Usage:
    python manual_keypoints_selection.py           # load existing JSON or click to define
    python manual_keypoints_selection.py --force  # always open click UI
    python manual_keypoints_selection.py --video path/to.mp4 --output path/to.json
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, List, Optional, Sequence, Tuple

import cv2
import supervision as sv

import config

EXPECTED_KEYPOINTS = 12


def run_manual_keypoints_selection(
    video_path: Optional[str] = None,
    save_path: Optional[str] = None,
    *,
    force_new: bool = False,
) -> List[Any]:
    """
    Load keypoints from JSON if present (unless ``force_new``), otherwise open the click UI.

    Returns the list of points as stored in JSON (typically 12 ``[x, y]`` pairs).
    """
    video_path = video_path or config.INPUT_VIDEO_PATH
    save_path = save_path if save_path is not None else config.FIXED_COURT_KEYPOINTS_SAVE_PATH

    if save_path and os.path.isfile(save_path) and not force_new:
        with open(save_path, "r", encoding="utf-8") as f:
            selected = json.load(f)
        print(f"manual_keypoints_selection: Loaded {len(selected)} keypoints from {save_path}")
        if len(selected) != EXPECTED_KEYPOINTS:
            print(
                f"manual_keypoints_selection: WARNING expected {EXPECTED_KEYPOINTS} points, got {len(selected)}"
            )
        return selected

    video_info = sv.VideoInfo.from_video_path(video_path=video_path)
    w_img, h_img = video_info.width, video_info.height

    display_w, display_h = 1280, 720
    if video_info.width < display_w and video_info.height < display_h:
        display_w, display_h = video_info.width, video_info.height

    first_frame_generator = sv.get_video_frames_generator(
        video_path,
        start=0,
        stride=1,
        end=1,
    )
    img = next(first_frame_generator)
    img_display = cv2.resize(img, (display_w, display_h))

    selected: List[Tuple[int, int]] = []

    def click_event(event, x, y, flags, params):
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        original_x = int(x * (w_img / display_w))
        original_y = int(y * (h_img / display_h))
        selected.append((original_x, original_y))
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(
            img_display,
            f"{original_x},{original_y}",
            (x, y),
            font,
            0.5,
            (255, 0, 0),
            2,
        )
        cv2.imshow("frame", img_display)

    print(f"manual_keypoints_selection: Click {EXPECTED_KEYPOINTS} court keypoints, then press any key.")
    cv2.imshow("frame", img_display)
    cv2.setMouseCallback("frame", click_event)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    if len(selected) != EXPECTED_KEYPOINTS:
        print(
            f"manual_keypoints_selection: WARNING expected {EXPECTED_KEYPOINTS} clicks, got {len(selected)}"
        )

    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump([list(p) if isinstance(p, tuple) else p for p in selected], f)
        print(f"manual_keypoints_selection: Saved keypoints to {save_path}")

    return selected


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Padel court keypoints — first-frame manual selection.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore existing JSON and open the selection window.",
    )
    parser.add_argument("--video", type=str, default=None, help="Video path (default: config.INPUT_VIDEO_PATH).")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON path (default: config.FIXED_COURT_KEYPOINTS_SAVE_PATH).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    run_manual_keypoints_selection(
        video_path=args.video,
        save_path=args.output,
        force_new=args.force,
    )


if __name__ == "__main__":
    main()
