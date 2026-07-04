from .features import ShotFeatures

class ShotRuleEngine:
    def classify(self, f: ShotFeatures) -> tuple[str, float]:
        """
        Classifies a shot based on biomechanical and physical rules.
        Returns (Shot Label, Confidence Score).
        """
        
        # 1. SERVE (Special logic usually requires knowing rally start, 
        # but here we use baseline + slow toss heuristic)
        if not f.near_net and f.ball_speed < 4.0 and f.rel_height > 0:
            # We skip SERVE for now as it needs state. Let's focus on active play.
            pass

        # 2. SMASH (High Overhead + Downward Velocity)
        if f.is_overhead and f.ball_vertical_vel > 2.0:
            conf = 0.6
            if f.ball_speed > 8.0: conf += 0.2
            if f.arm_extension > 150: conf += 0.2
            return "SMASH", min(conf, 1.0)

        # 3. VIBORA / BANDEJA (Overhead differentiation)
        if f.is_overhead:
            # Vibora is usually flatter and faster than Bandeja
            if f.ball_speed > 6.0 and abs(f.ball_vertical_vel) < 1.0:
                return "VIBORA", 0.75
            return "BANDEJA", 0.8

        # 4. LOB (Low impact + Steep upward trajectory)
        # UP = negative vertical velocity in pixel coords
        if f.ball_vertical_vel < -3.0 and f.rel_height < 50:
            return "LOB", 0.9

        # 5. VOLLEY (Near net + ball hit above hip)
        if f.near_net and f.rel_height > -150: # -150 is approx waist
            return "VOLLEY", 0.85

        # 6. FOREHAND / BACKHAND (Default groundstrokes)
        # We use the court-aware side logic we built earlier
        if f.is_top_player:
            # Facing DOWN: Right (camera) = Backhand
            label = "BACKHAND" if f.is_ball_right_of_player else "FOREHAND"
        else:
            # Facing UP: Right (camera) = Forehand
            label = "FOREHAND" if f.is_ball_right_of_player else "BACKHAND"
            
        return label, 0.9
