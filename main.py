"""
PADEL pipeline entrypoint.

Court keypoints are taken from ``manual_keypoints_selection`` first (loads existing JSON
or opens the OpenCV click UI), then analysis runs without a second keypoints window.

Diagram (order of the 12 clicks):

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

Run keypoints only: ``python manual_keypoints_selection.py``

Force new OpenCV calibration even if JSON exists: ``python main.py --force-keypoints``.
"""

import argparse

from config import COLLECT_DATA_PATH, INPUT_VIDEO_PATH, OUTPUT_VIDEO_PATH
from manual_keypoints_selection import run_manual_keypoints_selection
from run_analysis import run_analysis


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Padel full tracking pipeline")
    parser.add_argument(
        "--force-keypoints",
        action="store_true",
        help="Always open manual_keypoints_selection GUI, ignoring existing cache JSON.",
    )
    args = parser.parse_args()

    run_manual_keypoints_selection(force_new=args.force_keypoints)
    run_analysis(
        INPUT_VIDEO_PATH,
        OUTPUT_VIDEO_PATH,
        collect_data_path=COLLECT_DATA_PATH,
        summary_json_path="summary.json",
        allow_interactive_keypoints=False,
    )
