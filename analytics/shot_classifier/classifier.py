from .features import FeatureExtractor
from .rules import ShotRuleEngine

class PadelShotClassifier:
    """
    Main orchestrator for rule-based shot classification.
    """
    def __init__(self, frame_height: int = 1080):
        self.extractor = FeatureExtractor(frame_height)
        self.engine = ShotRuleEngine()

    def predict(self, ball_xy, kp, post_vel, player_pxy, player_id, frame_idx) -> tuple[str, float]:
        features = self.extractor.extract(ball_xy, kp, post_vel, player_pxy)
        if not features:
            return "SHOT", 0.1
            
        features.player_id = player_id
        features.frame_idx = frame_idx
        
        return self.engine.classify(features)
