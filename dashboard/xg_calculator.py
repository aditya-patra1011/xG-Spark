"""Predict the chance of a goal with the exported Logistic Regression model."""
import math

GOAL_LINE = 120.0
GOAL_CENTER = 40.0
LEFT_POST, RIGHT_POST = 36.0, 44.0

FLAGS = ["under_pressure", "first_time", "one_on_one", "open_goal", "aerial_won",
         "follows_dribble", "redirect"]

TYPICAL_SHOT = {
    "x": 103.0, "y": 40.0, "defenders_in_cone": 1, "nearest_defender": 2.4, "gk_off_line": 2.1,
    "is_home": 1, "body_part": "Right Foot", "technique": "Normal", "shot_type": "Open Play",
    "play_pattern": "Regular Play", "assist_type": "Other Pass",
    **{flag: 0 for flag in FLAGS},
}

GROUPS = {
    "Shot location": ["distance", "log_distance", "angle", "in_box"],
    "Defenders": ["defenders_in_cone", "nearest_defender"],
    "Goalkeeper": ["gk_distance", "gk_off_line"],
    "Body part": ["body_part"],
    "Technique": ["technique"],
    "Assist": ["assist_type"],
    "Phase of play": ["play_pattern", "shot_type", "is_home"],
    "Situation": FLAGS,
}


def build_features(shot: dict) -> dict:
    """Turn what the user chose into the exact inputs the model was trained on."""
    x, y = shot["x"], shot["y"]
    dx = GOAL_LINE - x
    distance = math.hypot(dx, GOAL_CENTER - y)
    angle = abs(math.atan2(RIGHT_POST - y, dx) - math.atan2(LEFT_POST - y, dx))
    gk_x = GOAL_LINE - shot["gk_off_line"]
    return {
        **shot,
        "distance": distance,
        "log_distance": math.log1p(distance),
        "angle": angle,
        "in_box": int(x >= 102 and 18 <= y <= 62),
        "gk_distance": math.hypot(gk_x - x, GOAL_CENTER - y),
    }


def _term(model: dict, feature: str, values: dict) -> float:
    if feature in model["numeric"]:
        return model["weights"][feature] * values[feature]
    return model["weights"].get(f"{feature}_encoded_{values[feature]}", 0.0)


def _score(model: dict, values: dict) -> float:
    features = model["numeric"] + list(model["categories"])
    return model["intercept"] + sum(_term(model, feature, values) for feature in features)


def predict(model: dict, shot: dict) -> float:
    return 1 / (1 + math.exp(-_score(model, build_features(shot))))


def effects(model: dict, shot: dict) -> dict[str, float]:
    """How much each part of the shot changes the odds, compared with a typical shot."""
    values = build_features(shot)
    typical = build_features(TYPICAL_SHOT)
    return {
        group: sum(_term(model, f, values) - _term(model, f, typical) for f in features)
        for group, features in GROUPS.items()
    }


def verdict(chance: float) -> str:
    if chance >= 0.5:
        return "Should be a goal"
    if chance >= 0.3:
        return "Big chance"
    if chance >= 0.12:
        return "Good chance"
    if chance >= 0.05:
        return "Half chance"
    return "Long shot"
