from typing import Literal, Iterable, Optional, Type
from collections import deque
import json
from dataclasses import dataclass
from pathlib import Path
import math
from tqdm import tqdm
import numpy as np
import cv2
from PIL import Image, ImageDraw
from torch.utils.data import DataLoader, IterableDataset
import torch
import supervision as sv


def detect_bounce_frames(
    y_px: np.ndarray,
    visibility: np.ndarray | None = None,
    min_gap_frames: int = 6,
    prominence_px: float = 3.0,
) -> list[int]:
    """
    Robust bounce detection using a sliding window.
    Handles missing frames by using the last known position.
    """
    n = len(y_px)
    if n < 5: return []

    y = np.asarray(y_px, dtype=np.float64).copy()
    vis = np.ones(n, dtype=bool) if visibility is None else np.asarray(visibility) > 0.5
    
    # Fill gaps in Y for peak detection
    for i in range(1, n):
        if not vis[i]: y[i] = y[i-1]

    candidates = []
    # Use a small window to find peaks (maximum Y on screen)
    W = 3
    for i in range(W, n - W):
        if not vis[i]: continue
        
        # Check if i is a local maximum in its neighborhood
        is_max = True
        for j in range(i - W, i + W + 1):
            if i == j: continue
            if y[i] < y[j]:
                is_max = False
                break
        
        if is_max:
            # Check prominence
            left_prom = y[i] - np.min(y[i-W:i])
            right_prom = y[i] - np.min(y[i+1:i+W+1])
            if min(left_prom, right_prom) >= prominence_px:
                candidates.append(i)

    # Filter overlaps
    final = []
    candidates.sort(key=lambda x: y[x], reverse=True)
    for c in candidates:
        if all(abs(c - f) >= min_gap_frames for f in final):
            final.append(c)
    
    return sorted(final)

from trackers.ball_tracker.models import TrackNet, TrackNetV3, InpaintNet
from trackers.ball_tracker.dataset import BallTrajectoryDataset
from trackers.ball_tracker.iterable import BallTrajectoryIterable
from trackers.ball_tracker.predict import predict, predict_modified
from trackers.tracker import Object, Tracker, NoPredictSample



def get_model(
    model_name: Literal["TrackNet", "InpaintNet"], 
    seq_len: int = None, 
    bg_mode: Literal["", "subtract", "subtract_concat", "concat"] = None,
) -> torch.nn.Module:
    """ 
    Create model by name and the configuration parameter.

    Parameters:
        model_name: type of model to create
            Choices:
                - 'TrackNet': Return TrackNet model
                - 'InpaintNet': Return InpaintNet model
        
        seq_len: length of TrackNet input sequence 
        bg_mode: background mode of TrackNet
            Choices:
                - '': return TrackNet with L x 3 input channels (RGB)
                - 'subtract': return TrackNet with L x 1 input channel 
                    (Difference frame)
                - 'subtract_concat': return TrackNet with L x 4 input channels
                    (RGB + Difference frame)
                - 'concat': return TrackNet with (L+1) x 3 input channels (RGB)

    Returns:
        model with specified configuration
    """

    if model_name == 'TrackNet':
        if bg_mode == 'subtract':
            model = TrackNet(in_dim=seq_len, out_dim=seq_len)
        elif bg_mode == 'subtract_concat':
            model = TrackNet(in_dim=seq_len*4, out_dim=seq_len)
        elif bg_mode == 'concat':
            model = TrackNet(in_dim=(seq_len+1)*3, out_dim=seq_len)
        else:
            model = TrackNet(in_dim=seq_len*3, out_dim=seq_len)
    elif model_name == 'TrackNetV3':
        if bg_mode == 'concat':
            model = TrackNetV3(in_dim=(seq_len+1)*3, out_dim=seq_len)
        else:
            model = TrackNetV3(in_dim=seq_len*3, out_dim=seq_len)
    elif model_name == 'InpaintNet':
        model = InpaintNet()
    else:
        raise ValueError('Invalid model name.')
    
    return model


def get_ensemble_weight(
    seq_len: int, 
    eval_mode: Literal["average", "weight"],
) -> torch.Tensor:
    """ 
    Get weight for temporal ensemble.

    Parameters:
        seq_len: Length of input sequence
        eval_mode: Mode of temporal ensemble
            Choices:
                - 'average': return uniform weight
                - 'weight': return positional weight
        
        Returns:
            weight for temporal ensemble
    """

    if eval_mode == 'average':
        weight = torch.ones(seq_len) / seq_len
    elif eval_mode == 'weight':
        weight = torch.ones(seq_len)
        for i in range(math.ceil(seq_len/2)):
            weight[i] = (i+1)
            weight[seq_len-i-1] = (i+1)
        weight = weight / weight.sum()
    else:
        raise ValueError('Invalid mode')
    
    return weight


def generate_inpaint_mask(pred_dict: dict, th_h: float=30) -> list:
    """ 
    Generate inpaint mask form predicted trajectory.

    Parameters:
        pred_dict: prediction result
            Format: {'Frame':[], 'X':[], 'Y':[], 'Visibility':[]}
        th_h: height threshold (pixels) for y coordinate
        
    Returns:
        inpaint mask
    """
    y = np.array(pred_dict.get('Y', pred_dict.get('y', [])))
    vis_pred = np.array(pred_dict.get('Visibility', pred_dict.get('visibility', [])))
    inpaint_mask = np.zeros_like(y)
    i = 0 # index that ball start to disappear
    j = 0 # index that ball start to appear
    threshold = th_h
    while j < len(vis_pred):
        while i < len(vis_pred)-1 and vis_pred[i] == 1:
            i += 1
        j = i
        while j < len(vis_pred)-1 and vis_pred[j] == 0:
            j += 1
        if j == i:
            break
        elif i == 0 and y[j] > threshold:
            # start from the first frame that ball disappear
            inpaint_mask[:j] = 1
        elif (i > 1 and y[i-1] > threshold) and (j < len(vis_pred) and y[j] > threshold):
            inpaint_mask[i:j] = 1
        else:
            # ball is out of the field of camera view 
            pass
        i = j
    
    return inpaint_mask.tolist()


class Ball(Object):

    """
    Ball detection in a given video frame

    Attributes:
        frame: frame associated with the given ball detection
        xy: ball position coordinates
        visibility: 1 if the ball is visible in the given frame
        projection: ball position 2d court projection 
    """

    def __init__(
        self, 
        frame: int, 
        xy: tuple[float, float], 
        visibility: Literal[0,1],
        projection: Optional[tuple[int, int]] = None,
        is_predicted: bool = False,
        is_bounce: bool = False,
        zone: str = "na",
    ):
        super().__init__()

        self.frame = frame
        self.xy = xy
        self.visibility = visibility
        self.projection = projection
        self.is_predicted = is_predicted
        self.is_bounce = is_bounce
        self.zone = zone

    @classmethod
    def from_json(cls, x: dict):
        return cls(**x)

    def serialize(self) -> dict:
        return {
            "frame": self.frame,
            "xy": self.xy,
            "visibility": self.visibility,
            "projection": self.projection,
            "is_predicted": self.is_predicted,
            "is_bounce": self.is_bounce,
            "zone": self.zone,
        }
    def asint(self) -> tuple[int, int]:
        if math.isnan(self.xy[0]) or math.isnan(self.xy[1]):
            return (0, 0)
        return tuple(int(v) for v in self.xy)

    # Class-level deque to store ball trajectory for drawing the "queue" (tail)
    trajectory = deque(maxlen=10)

    def draw(self, frame: np.ndarray) -> np.ndarray:
        """
        Draw ball detection as a circle with a trajectory tail.
        Green for real detections, Orange for predicted/interpolated.
        """
        if self.visibility == 0 and not self.is_predicted:
            return frame
            
        if math.isnan(self.xy[0]) or math.isnan(self.xy[1]):
            return frame

        # Store current position in trajectory
        current_pos = self.asint()
        # Avoid drawing at (0,0) or NaN
        if current_pos[1] < 5: 
            return frame
            
        Ball.trajectory.append(current_pos)

        # 1. Draw the trajectory "queue" (tail) in CYAN
        for i in range(len(Ball.trajectory) - 1):
            if Ball.trajectory[i] is not None and Ball.trajectory[i+1] is not None:
                # Basic distance check to avoid drawing across the whole screen on jumps
                dist = np.sqrt((Ball.trajectory[i][0]-Ball.trajectory[i+1][0])**2 + 
                               (Ball.trajectory[i][1]-Ball.trajectory[i+1][1])**2)
                if dist < 150:
                    cv2.line(
                        frame,
                        Ball.trajectory[i],
                        Ball.trajectory[i+1],
                        (255, 255, 0), # Cyan/Yellow-ish
                        2
                    )

        # 2. Draw the main ball circle
        # Green (0,255,0) for real, Orange (0,165,255) for predicted
        color = (0, 255, 0) if not self.is_predicted else (0, 165, 255)
        
        cv2.circle(
            frame,
            current_pos,
            7, 
            color,
            -1, 
        )

        # 3. Draw Bounce Marker
        if self.is_bounce:
            cv2.circle(frame, current_pos, 15, (255, 0, 255), 3) # Magenta ring
            cv2.putText(frame, "BOUNCE", (current_pos[0]-25, current_pos[1]-20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
        
        # Add "Real" label if requested or just high visibility
        if not self.is_predicted and self.visibility == 1:
             cv2.putText(frame, "Ball", (int(current_pos[0]+10), int(current_pos[1])), 
                         cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        return frame
    
    def draw_projection(self, frame: np.ndarray) -> np.ndarray:
        
        cv2.circle(
            frame,
            self.projection,
            6,
            (255, 255, 0),
            -1,
        )

        return frame


class BallTracker(Tracker):

    """
    Tracker of ball object

    Attributes:
        tracking_model_path: tracknet model path
        inpainting_model_path: inpainting model path
        median_max_sample_num: maximum number of frames to sample for 
            generating median image
        median: background estimation
        load_path: serializable tracker results path 
        save_path: path to save serializable tracker results

    Note: 
        its important to filter frames of interest before feeding the 
        video to the model
    """

    EVAL_MODE: str = "weight"
    TRAJECTORY_LENGTH: int = 8
    
    HEIGHT: int = 288
    WIDTH: int = 512
    SIGMA: float = 2.5
    IMG_FORMAT = 'png'
    
    def __init__(
        self, 
        tracking_model_path: str,
        inpainting_model_path: str,
        batch_size: int,
        median_max_sample_num: int = 1800, 
        median: Optional[np.ndarray] = None,
        load_path: Optional[str | Path] = None,
        save_path: Optional[str | Path] = None,
    ):
        super().__init__(
            load_path=load_path,
            save_path=save_path,
        )

        self.DELTA_T: float = 1 / math.sqrt(self.HEIGHT**2 + self.WIDTH**2)
        self.COOR_TH = self.DELTA_T * 50

        tracknet_ckpt = torch.load(tracking_model_path)
        self.tracknet_seq_len = tracknet_ckpt['param_dict']['seq_len']

        assert self.tracknet_seq_len == self.TRAJECTORY_LENGTH

        self.bg_mode = tracknet_ckpt['param_dict']['bg_mode']

        self.tracknet = get_model(
            "TrackNet", 
            self.tracknet_seq_len,
            self.bg_mode,
        )
        self.tracknet.load_state_dict(tracknet_ckpt['model'])
        self.tracknet.eval()

        if inpainting_model_path:
            inpaintnet_ckpt = torch.load(inpainting_model_path)
            self.inpaintnet_seq_len = inpaintnet_ckpt['param_dict']['seq_len']
            self.inpaintnet = get_model('InpaintNet')
            self.inpaintnet.load_state_dict(inpaintnet_ckpt['model'])
        else:
            self.inpaintnet = None

        self.batch_size = batch_size
        self.median_max_sample_num = median_max_sample_num
        self.median = median
        
        # Robust tracking config from 'ball_only'
        self.ROBUST_CONFIG = {
            "LEFT_MARGIN_FRAC": 0.18, # Side glass margins
            "RIGHT_MARGIN_FRAC": 0.12,
            "TOP_MARGIN_FRAC": 0.15,
            "MEDIAN_WINDOW": 5,
            "MEDIAN_DIST_MAX": 70, # Max deviation from local median path
            "MAX_PIXELS_PER_FRAME": 35.0, # Velocity threshold
            "SMOOTH_WINDOW": 3,
            "INTERP_METHOD": "quadratic", # Parabolic physics
        }
    
    def video_info_post_init(self, video_info: sv.VideoInfo) -> "BallTracker":
        self.video_info = video_info
        return self
    
    def object(self) -> Type[Object]:
        return Ball
    
    def draw_kwargs(self) -> dict:
        return {}
    
    def __str__(self) -> str:
        return "ball_tracker"
    
    def restart(self) -> None:
        self.results.restart()

    def processor(self, frame: np.ndarray):
        pass
    
    def draw_traj(self, img, traj, radius=3, color='red') -> np.ndarray:
        """ Draw trajectory on the image.

            Args:
                img (numpy.ndarray): Image with shape (H, W, C)
                traj (deque): Trajectory to draw

            Returns:
                img (numpy.ndarray): Image with trajectory drawn
        """
        # img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)   
        img = Image.fromarray(img)
        
        for i in range(len(traj)):
            if traj[i] is not None:
                draw_x = traj[i][0]
                draw_y = traj[i][1]
                bbox =  (draw_x - radius, draw_y - radius, draw_x + radius, draw_y + radius)
                draw = ImageDraw.Draw(img)
                draw.ellipse(bbox, fill='rgb(255,255,255)', outline=color)
                del draw
        # img =  cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        return np.array(img)
    
    def draw_multiple_frames(
        self,
        frames: list[np.ndarray],
        ball_detections: list[Ball],
        traj_len=8
    ):

        pred_queue = deque()
        
        output_frames = []
        for frame, ball_detection in zip(frames, ball_detections):
        
            # Check capacity of queue
            if len(pred_queue) >= traj_len:
                pred_queue.pop()
        
            pred_queue.appendleft(
                list(ball_detection.xy)
            ) if ball_detection.visibility else pred_queue.appendleft(None)

            # Draw prediction trajectory
            output_frames.append(self.draw_traj(frame, pred_queue, color='yellow'))

        return output_frames
    
    def modify_pred_dict(self, pred_dict: dict):

        mapping = {
            "X": ["X", "x"],
            "Y": ["Y", "y"],
            "Visibility": ["Visibility", "visibility"],
            "Inpaint_Mask": ["Inpaint_Mask", "inpaint_mask"],
            "Img_scaler": ["Img_scaler", "img_scaler"],
            "Img_shape": ["Img_shape", "img_shape"],
        }
        res = {}
        for k, sources in mapping.items():
            for src in sources:
                if src in pred_dict:
                    res[k] = pred_dict[src]
                    break
        return res
    
    def to(self, device: str) -> None:
        self.tracknet.to(device)
        if self.inpaintnet is not None:
            self.inpaintnet.to(device)

    def predict_sample(self, sample: Iterable[np.ndarray], **kwargs):
        raise NoPredictSample()

    def filter_reflections(self, pred_dict: dict) -> None:
        """
        Advanced reflection filtering using glass zone margins, 
        velocity jumps, and rolling median outlier rejection.
        """
        width = self.video_info.width
        height = self.video_info.height
        cfg = self.ROBUST_CONFIG
        
        import pandas as pd
        df = pd.DataFrame({
            'x': pred_dict["X"], 
            'y': pred_dict["Y"], 
            'vis': pred_dict["Visibility"]
        })
        
        # 1. Glass margins rejection
        LEFT = int(width * cfg["LEFT_MARGIN_FRAC"])
        RIGHT = int(width * cfg["RIGHT_MARGIN_FRAC"])
        TOP = int(height * cfg["TOP_MARGIN_FRAC"])
        
        # 2. Rolling Median Outlier Rejection
        df['x_med'] = df['x'].rolling(window=cfg["MEDIAN_WINDOW"], center=True, min_periods=1).median()
        df['y_med'] = df['y'].rolling(window=cfg["MEDIAN_WINDOW"], center=True, min_periods=1).median()
        dist_med = np.sqrt((df['x'] - df['x_med'])**2 + (df['y'] - df['y_med'])**2)
        df.loc[dist_med > cfg["MEDIAN_DIST_MAX"], 'vis'] = 0
        
        # 3. Velocity-aware reflection rejection
        # If the ball jumps suddenly into a glass zone at high speed, it's likely a reflection
        valid_idx = df.index[df['vis'] > 0.5].tolist()
        if len(valid_idx) > 1:
            for k in range(1, len(valid_idx)):
                p_idx, c_idx = valid_idx[k-1], valid_idx[k]
                dt = c_idx - p_idx
                dist = np.hypot(df.at[c_idx, 'x'] - df.at[p_idx, 'x'], 
                                df.at[c_idx, 'y'] - df.at[p_idx, 'y'])
                vel = dist / dt
                
                # Check for jump into glass zone
                curr_x = df.at[c_idx, 'x']
                if vel > cfg["MAX_PIXELS_PER_FRAME"] and (curr_x < LEFT or curr_x > (width - RIGHT)):
                    df.at[c_idx, 'vis'] = 0
        
        # 4. Interpolation (Parabolic)
        df.loc[df['vis'] == 0, ['x', 'y']] = np.nan
        try:
            df['x_int'] = df['x'].interpolate(method=cfg["INTERP_METHOD"], limit_direction='both')
            df['y_int'] = df['y'].interpolate(method=cfg["INTERP_METHOD"], limit_direction='both')
        except:
            df['x_int'] = df['x'].interpolate(method='linear', limit_direction='both')
            df['y_int'] = df['y'].interpolate(method='linear', limit_direction='both')
            
        # 5. Smoothing
        df['xf'] = df['x_int'].rolling(window=cfg["SMOOTH_WINDOW"], center=True, min_periods=1).median()
        df['yf'] = df['y_int'].rolling(window=cfg["SMOOTH_WINDOW"], center=True, min_periods=1).median()
        
        # Write back to dict
        pred_dict["X"] = df['xf'].tolist()
        pred_dict["Y"] = df['yf'].tolist()
        pred_dict["Visibility"] = df['vis'].tolist()
        # Store prediction flags
        pred_dict["is_predicted"] = (df['vis'] == 0).tolist()

    def predict_frames(
        self,
        frame_generator: Iterable[np.ndarray],
        total_frames: int,
    ) -> list[Ball]:

        w_scaler, h_scaler = (
            self.video_info.width / self.WIDTH, 
            self.video_info.height / self.HEIGHT,
        )

        img_scaler = (w_scaler, h_scaler)

        tracknet_pred_dict = {
            'Frame':[], 
            'X':[], 
            'Y':[], 
            'Visibility':[], 
            'inpaint_mask': [],
            'img_scaler': img_scaler, 
            'img_shape': (self.video_info.width, self.video_info.height),
        }

        seq_len = self.tracknet_seq_len

        iterable = BallTrajectoryIterable(
            seq_len=seq_len,
            sliding_step=1,
            data_mode="heatmap",
            bg_mode="concat",
            frame_generator=frame_generator,
            HEIGHT=self.HEIGHT,
            WIDTH=self.WIDTH,
            SIGMA=2.5,
            IMG_FORMAT="png",
            median=self.median,
            median_range=self.median_max_sample_num,
        )

        data_loader = DataLoader(
            iterable,
            batch_size=self.batch_size,
            shuffle=False,
            drop_last=False,
        )

        video_len = total_frames

        ### Init prediction buffer params ###
        # Number of samples of seq_len frames
        num_sample, sample_count = video_len - seq_len + 1, 0
        buffer_size = seq_len - 1
        sample_indices = torch.arange(seq_len) # [0, 1, 2, 3, 4, 5, 6, 7]
        frame_indices = torch.arange(seq_len-1, -1, -1) # [7, 6, 5, 4, 3, 2, 1, 0]
        y_pred_buffer = torch.zeros(
            (
                buffer_size, 
                seq_len, 
                self.HEIGHT, 
                self.WIDTH
            ), 
            dtype=torch.float32,
        )
        # Weights for the frame prediction ensemble along the distinct samples position
        weight = get_ensemble_weight(seq_len, self.EVAL_MODE)

        current_frame_idx = 0
        for x in tqdm(data_loader):
            x = x.float().to(self.DEVICE)

            batch_size = x.shape[0]
            assert seq_len*3 + 3 == x.shape[1] 

            with torch.no_grad():
                y_pred = self.tracknet(x).detach().cpu()
            
            # Concatenate predictions onto the previous predictions buffer
            y_pred_buffer = torch.cat(
                (y_pred_buffer, y_pred), 
                dim=0,
            )

            ensemble_y_pred = torch.empty(
                (0, 1, self.HEIGHT, self.WIDTH), 
                dtype=torch.float32,
            )

            for sample_i in range(batch_size):
                if sample_count < buffer_size:
                    # Incomplete buffer. A given sample first frame have 
                    # not appeared in all frame positions before
                    y_pred = y_pred_buffer[
                        sample_indices + sample_i,
                        frame_indices,
                    ].sum(0) / (sample_count + 1)
                else:
                    # General complete buffer. A given sample first frame
                    # have appeared in all frame positions before
                    y_pred = (
                        y_pred_buffer[
                            sample_indices + sample_i,
                            frame_indices
                        ] * weight[:, None, None]
                    ).sum(0)

                ensemble_y_pred = torch.cat(
                    (
                        ensemble_y_pred, 
                        y_pred.reshape(1, 1, self.HEIGHT, self.WIDTH),
                    ),
                    dim=0,
                )
                sample_count += 1

                if sample_count == num_sample:
                    # The sample above was the last sample
                    y_zero_pad = torch.zeros(
                        (buffer_size, seq_len, self.HEIGHT, self.WIDTH),
                        dtype=torch.float32,
                    )
                    y_pred_buffer = torch.cat(
                        (y_pred_buffer, y_zero_pad),
                        dim=0,
                    )
                    print(seq_len)
                    for frame_i in range(1, seq_len):
                        y_pred = y_pred_buffer[
                            sample_indices + sample_i + frame_i,
                            frame_indices
                        ].sum(0) / (seq_len - frame_i)

                        ensemble_y_pred = torch.cat(
                            (
                                ensemble_y_pred, 
                                y_pred.reshape(1, 1, self.HEIGHT, self.WIDTH),
                            ),
                            dim=0,
                        )

            # Predict
            tmp_pred = predict_modified(
                y_pred=ensemble_y_pred, # first frame prediction of batch_size samples
                img_scaler=img_scaler,
                WIDTH=self.WIDTH,
                HEIGHT=self.HEIGHT,
            )

            # Translate predict_modified keys to match tracknet_pred_dict
            mapping = {"x": "X", "y": "Y", "visibility": "Visibility"}
            for key, val in tmp_pred.items():
                target_key = mapping.get(key, key)
                if target_key in tracknet_pred_dict:
                    tracknet_pred_dict[target_key].extend(val)
            
            # Populate Frame indices
            num_new_preds = len(tmp_pred.get("x", []))
            for _ in range(num_new_preds):
                tracknet_pred_dict['Frame'].append(current_frame_idx)
                current_frame_idx += 1

            # Update buffer, keep last predictions for ensemble in next iteration
            y_pred_buffer = y_pred_buffer[-buffer_size:]

        # Pre-process detections for reflection filtering
        # At this point, tracknet_pred_dict contains the raw TrackNet predictions
        
        # Apply Robust Reflection Filtering & Interpolation
        self.filter_reflections(tracknet_pred_dict)
        
        # Convert final dict to Ball objects
        final_balls = []
        for frame_idx in range(total_frames):
            if frame_idx < len(tracknet_pred_dict["X"]):
                final_balls.append(
                    Ball(
                        frame=frame_idx,
                        xy=(tracknet_pred_dict["X"][frame_idx], tracknet_pred_dict["Y"][frame_idx]),
                        visibility=1 if tracknet_pred_dict["Visibility"][frame_idx] > 0.5 else 0,
                        is_predicted=tracknet_pred_dict["is_predicted"][frame_idx],
                    )
                )
            else:
                # Fallback for missing frames at the end
                final_balls.append(Ball(frame=frame_idx, xy=(0,0), visibility=0, is_predicted=True))

        # 3. BOUNCE DETECTION
        ys = np.array([float(b.xy[1]) for b in final_balls], dtype=np.float64)
        trusted = np.array([float(b.visibility) for b in final_balls], dtype=np.float64)
        
        # Increase gap to approx 0.45s to prevent double-detection of one bounce
        min_gap = max(12, int(self.video_info.fps * 0.45))
        bounce_idx = detect_bounce_frames(
            ys,
            visibility=trusted,
            min_gap_frames=min_gap,
            prominence_px=4.0 # Increased sensitivity for far-away bounces
        )
        
        for idx in bounce_idx:
            if idx < len(final_balls):
                final_balls[idx].is_bounce = True
                
        return final_balls