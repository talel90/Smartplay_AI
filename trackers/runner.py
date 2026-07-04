""" 
Implementation of a runner to extract results from an arbitrary list of trackers 
"""

from typing import Optional
from tqdm import tqdm
import timeit
from copy import deepcopy
from pathlib import Path
import cv2
import numpy as np
import supervision as sv

from trackers.players_tracker.players_tracker import Players
from trackers.ball_tracker.ball_tracker import Ball
from trackers.players_keypoints_tracker.players_keypoints_tracker import PlayersKeypoints
from trackers.keypoints_tracker.keypoints_tracker import Keypoints
from trackers.tracker import Tracker
from analytics import ProjectedCourt, DataAnalytics
from analytics.scoring import PadelScorer
from analytics.shot_feature_extractor import ShotFeatureExtractor


class TrackingRunner:

    """
    Abstraction that implements a memory efficient pipeline to run
    a sequence of trackers over a sequence of video frames

    Attributes:
        trackers: sequence of trackers of interest
        video_path: source video path
        inference_path: path where to save the inference results
        start: indicates the starting position from which video should generate frames
        stride: indicates the interval at which frames are returned
        end: indicates the ending position at which video should stop generating frames.
             If None, video will be read to the end.   
        collect_data: True to collect data from projected court
    """

    def __init__(
        self, 
        trackers: list[Tracker],
        video_path: str | Path,
        inference_path: str | Path,
        start: int = 0,
        end: Optional[int] = None,
        collect_data: bool = False,
        scorer_reporter_path: Optional[str] = None,
    ) -> None:
    
        self.video_path = video_path
        self.inference_path = inference_path
        self.start = start
        self.stride = 1
        self.end = end
        self.video_info = sv.VideoInfo.from_video_path(video_path=video_path)

        if self.end is None:
            self.total_frames = self.video_info.total_frames
        else:
            self.total_frames = self.end - self.start

        self.trackers = {}
        self.is_fixed_keypoints = False
        for tracker in trackers:
            self.trackers[str(tracker)] = tracker.video_info_post_init(self.video_info)

            if tracker.object() == Keypoints:
                self.is_fixed_keypoints = not(
                    tracker.fixed_keypoints_detection is None
                )
        
        if self.is_fixed_keypoints:
            print("-"*40)
            print("runner: Using fixed court keypoints")
            print("-"*40)

        self.projected_court = ProjectedCourt(self.video_info)
        if collect_data:
            print("runner: Ready for data collection")
            self.data_analytics = DataAnalytics()
            self.scorer = PadelScorer(reporter_output_path=scorer_reporter_path)
            self.shot_extractor = ShotFeatureExtractor(window_size=10)
            self.history_size = 21 # 10 before, 1 impact, 10 after
            self.ball_buffer = []
            self.player_pos_m_buffer = []
            self.player_kp_buffer = []
            self.pending_hits = [] # List of (impact_frame_idx, player_id)
            self.persistent_bounces = [] # List of (x, y) for permanent markers
        else:
            self.data_analytics = None
            self.scorer = None
    
    def restart(self) -> None:
        """
        Restart all trackers and data
        """
        for tracker in self.trackers.values():
            tracker.restart()
        
        if self.data_analytics:
            self.data_analytics.restart()

    def draw_and_collect_data(self) -> None:
        """
        Draw tracker results and 2D court projections accross all video frames.
        Collect data for further analysis.
        """

        print(f"runner: Writing results into {str(self.inference_path)}")

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(
            self.inference_path,
            fourcc,
            float(self.video_info.fps),
            self.video_info.resolution_wh,
        )

        frame_generator = sv.get_video_frames_generator(
            self.video_path,
            start=self.start,
            stride=self.stride,
            end=self.end,
        )

        for frame_index, frame in tqdm(enumerate(frame_generator)):
    
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            cv2.putText(
                frame_rgb,
                f"Frame: {frame_index + 1}",
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 0),
                1,
            )

            players_detection = None
            ball_detection = None
            keypoints_detection = None
            players_kp_detection = None
            for tracker in self.trackers.values():
                
                try:
                    prediction = tracker.results[frame_index]
                except IndexError as e:
                    print(f"runner: {str(tracker)} frame {frame_index}")
                    raise(e)
                
                frame_rgb = prediction.draw(frame_rgb, **tracker.draw_kwargs())

                if tracker.object() == Players:
                    players_detection = deepcopy(prediction)
                elif tracker.object() == Ball:
                    ball_detection = deepcopy(prediction)
                elif tracker.object() == Keypoints:
                    keypoints_detection = deepcopy(prediction)
                elif tracker.object() == PlayersKeypoints:
                    players_kp_detection = deepcopy(prediction)
               
            output_frame, self.data_analytics = self.projected_court.draw_projections_and_collect_data(
                frame_rgb,
                keypoints_detection=keypoints_detection,
                players_detection=players_detection,
                ball_detection=ball_detection,
                data_analytics=self.data_analytics,
                is_fixed_keypoints=self.is_fixed_keypoints,
            )

            # --- DRAW PERMANENT MARKS ON FLOOR ---
            for bx, by in self.persistent_bounces:
                # Small yellow dot for permanent history
                cv2.circle(output_frame, (bx, by), 4, (0, 255, 255), -1, cv2.LINE_AA)

            # SCORING LOGIC
            if self.scorer and ball_detection:
                ball_pos_m = None
                if ball_detection.projection:
                    ball_pos_m = self.projected_court.court_keypoints.shift_point_origin(
                        ball_detection.projection, dimension="meters"
                    )
                
                players_pos_m = {}
                if players_detection:
                    for p in players_detection:
                        if p.projection:
                            players_pos_m[p.id] = self.projected_court.court_keypoints.shift_point_origin(
                                p.projection, dimension="meters"
                            )

                prev_shoots = {pid: s for pid, s in self.scorer.player_shoots.items()}
                # Collect current keypoints for players
                current_kp_map = {}
                if players_kp_detection and players_detection:
                    for p in players_detection:
                        best_kp = None
                        min_d = float('inf')
                        for pk in players_kp_detection:
                            # Use neck or nose as reference to link KP to player bbox
                            ref = pk.keypoints_by_name.get('nose') or pk.keypoints_by_name.get('neck')
                            if ref:
                                d = np.hypot(ref.xy[0] - p.xyxy[0], ref.xy[1] - p.xyxy[1])
                                if d < min_d:
                                    min_d = d
                                    best_kp = pk
                        current_kp_map[p.id] = best_kp

                # Calculate player centers for ShotCounter
                players_xy = {}
                if players_detection:
                    for p in players_detection:
                        x1, y1, x2, y2 = p.xyxy
                        players_xy[p.id] = ((x1 + x2) / 2, (y1 + y2) / 2)
                # FILTER BOUNCES TO COURT BOUNDARIES ONLY
                is_bounce = getattr(ball_detection, "is_bounce", False)
                if is_bounce and ball_pos_m:
                    # Padel court is 10m x 20m. Origin is center.
                    # Allowed: X: [-5.1, 5.1], Y: [-10.1, 10.1] (with line buffer)
                    in_court = (-5.2 <= ball_pos_m[0] <= 5.2) and (-10.2 <= ball_pos_m[1] <= 10.2)
                    if not in_court:
                        ball_detection.is_bounce = False
                        is_bounce = False
                    else:
                        # VALID COURT BOUNCE -> DRAW AND SAVE
                        bx, by = ball_detection.xy
                        self.persistent_bounces.append((int(bx), int(by)))
                        cv2.circle(output_frame, (int(bx), int(by)), 25, (0, 255, 255), 3, cv2.LINE_AA)
                        cv2.circle(output_frame, (int(bx), int(by)), 12, (0, 255, 255), 2, cv2.LINE_AA)
                        cv2.circle(output_frame, (int(bx), int(by)), 6, (0, 255, 255), -1)
                        cv2.putText(output_frame, "BOUNCE", (int(bx) + 20, int(by) - 20), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 3, cv2.LINE_AA)

                self.scorer.process_frame(
                    frame_idx=frame_index,
                    ball_pos_m=ball_pos_m,
                    is_bounce=is_bounce,
                    players_pos_m=players_pos_m,
                    players_kp=current_kp_map,
                    ball_xy=ball_detection.xy if ball_detection else None,
                    players_xy=players_xy
                )
                
                # Check if a new shoot was detected
                for pid, s in self.scorer.player_shoots.items():
                    if s > prev_shoots.get(pid, 0):
                        # Hit detected at frame_index!
                        self.pending_hits.append((frame_index, pid))

            # UPDATE BUFFERS AND CLASSIFY
            if self.scorer:
                # Update rolling buffers
                self.ball_buffer.append({'xy': ball_detection.xy if ball_detection else None})
                
                # Map KPs to IDs (Simple proximity to player center)
                current_kp_map = {}
                if players_kp_detection and players_detection:
                    for p in players_detection:
                        best_kp = None
                        min_d = float('inf')
                        for pk in players_kp_detection:
                            ref = pk.keypoints_by_name.get('neck')
                            if ref:
                                d = np.hypot(ref.xy[0] - p.xyxy[0], ref.xy[1] - p.xyxy[1])
                                if d < min_d:
                                    min_d = d
                                    best_kp = pk
                        current_kp_map[p.id] = best_kp
                self.player_kp_buffer.append(current_kp_map)
                
                current_pos_m_map = {}
                if players_detection:
                    for p in players_detection:
                        if p.projection:
                            current_pos_m_map[p.id] = self.projected_court.court_keypoints.shift_point_origin(p.projection, dimension="meters")
                self.player_pos_m_buffer.append(current_pos_m_map)

                if len(self.ball_buffer) > self.history_size:
                    self.ball_buffer.pop(0)
                    self.player_kp_buffer.pop(0)
                    self.player_pos_m_buffer.pop(0)

                # Process pending hits (wait until we have 10 future frames)
                for hit_frame, pid in self.pending_hits[:]:
                    # We need to wait until the current frame_index is hit_frame + 10
                    # so that hit_frame is in the middle of our 21-frame buffer.
                    if frame_index >= hit_frame + self.history_size // 2:
                        # Extract features for the hit
                        # The buffer now contains [hit_frame-10, ..., hit_frame, ..., hit_frame+10]
                        feat = self.shot_extractor.extract_features(
                            hit_frame, pid, 
                            self.ball_buffer, self.player_kp_buffer, self.player_pos_m_buffer
                        )
                        
                        if feat and self.scorer.clf:
                            # Perform inference
                            input_data = [feat[c] for c in self.scorer.feature_cols]
                            shot_label = self.scorer.clf.predict([input_data])[0]
                            self.scorer.last_shot_type[pid] = shot_label
                            print(f"Frame {hit_frame}: Classified Player {pid} shot as {shot_label}")
                        
                        self.pending_hits.remove((hit_frame, pid))
            
            if self.scorer:
                output_frame = self.scorer.draw_score(
                    output_frame, 
                    frame_idx=frame_index, 
                    players_detection=players_detection
                )

            """ CAREFUL HERE (READ THE CODE CAREFULLY)"""

            if self.data_analytics is not None:
                self.data_analytics.step(1)

            out.write(cv2.cvtColor(output_frame, cv2.COLOR_BGR2RGB))
        
        out.release()

        # Remove extra frame
        self.data_analytics.frames = self.data_analytics.frames[:-1]

        # assertion_txt = f"lenght data analytics: {len(self.data_analytics)} / total frames {self.total_frames}"
        # assert len(self.data_analytics) == self.total_frames, assertion_txt

        print("runner: Done.") 


    def run(self) -> None:
        """
        Run trackers object prediction for every frame in the frame generator

        Parameters:
            drop_last: True to drop the last sample if its incomplete
        """

        print(f"runner: Running {self.total_frames} frames")

        for tracker in self.trackers.values():

            if len(tracker) != 0:
                print(f"{tracker.__str__()}: {len(tracker)} predictions stored")
                

                continue

                """ FIX TOTAL FRAMES / TOTAL PREDICTIONS MISMATCH """


                #if len(tracker) == self.total_frames:
                #    print(
                #        f"""{tracker.__str__()}: \
                #        match between number of predictions and total frames 
                #        """
                #    )
                #    continue
                #else:
                #    print(
                #        f"""{tracker.__str__()}: \
                #        unmatch between number of predictions and total frames 
                #        """
                #   )
                #    tracker.restart()
                #    print(f"{tracker.__str__()}: WARNING restarted tracker")

            tracker.to(tracker.DEVICE)
            print(f"{str(tracker)}: Running on {tracker.DEVICE} ...")

            frame_generator = sv.get_video_frames_generator(
                self.video_path,
                start=self.start,
                stride=self.stride,
                end=self.end,
            )

            t0 = timeit.default_timer()
            # Collect all objects predictions for a given video
            tracker.predict_and_update(
                frame_generator, 
                total_frames=self.total_frames,
            )
            t1 = timeit.default_timer()

            tracker.to("cpu")

            print(f"{str(tracker)}: {t1 - t0} inference time.")

            tracker.save_predictions()
        
        self.draw_and_collect_data()

        

    

    


        



    
    


