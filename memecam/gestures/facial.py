"""Local expression templates learned from neutral and expressive blendshape samples."""
import math
from pathlib import Path
from memecam.config.settings import read_json


def validate_rules(rules, overlay_ids):
    if not isinstance(rules, list):
        raise ValueError("Facial gestures must be a list")
    seen = set()
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != {"id", "name", "overlay", "enabled", "threshold", "features"}:
            raise ValueError("Invalid facial gesture fields")
        if any(not isinstance(rule[k], str) or not rule[k].strip() for k in ("id", "name", "overlay")):
            raise ValueError("Facial gesture names and IDs must be nonempty")
        if rule["id"] in seen or rule["overlay"] not in overlay_ids or type(rule["enabled"]) is not bool:
            raise ValueError("Duplicate facial gesture, missing overlay, or invalid enabled flag")
        seen.add(rule["id"])
        threshold = rule["threshold"]
        if type(threshold) not in (int, float) or not math.isfinite(threshold) or not .2 <= threshold <= 1:
            raise ValueError("Expression threshold must be between 0.2 and 1")
        if not isinstance(rule["features"], dict) or not 1 <= len(rule["features"]) <= 6:
            raise ValueError("Expression needs 1–6 tracked features")
        for key, pair in rule["features"].items():
            if not isinstance(key, str) or not key or not isinstance(pair, list) or len(pair) != 2:
                raise ValueError("Invalid expression feature")
            if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in pair):
                raise ValueError("Invalid expression sample")
            if abs(pair[1] - pair[0]) < .12:
                raise ValueError("Expression is too similar to neutral; capture a stronger gesture")
    return rules


def load_rules(path, overlay_ids):
    return validate_rules(read_json(path), overlay_ids) if Path(path).exists() else []


def learn_features(neutral, expression):
    changes = sorted(((abs(expression[k] - neutral[k]), k) for k in neutral.keys() & expression.keys()),
                     reverse=True)
    features = {k: [neutral[k], expression[k]] for delta, k in changes[:6] if delta >= .12}
    if not features:
        raise ValueError("Gesto muy parecido al neutral. Repite con una expresión más marcada.")
    return features


def match_score(rule, scores):
    """Require every learned feature, preventing one strong feature from masking missing ones."""
    if not scores or any(k not in scores for k in rule["features"]):
        return 0.0
    return max(0.0, min(1.0, min((scores[k] - a) / (b - a)
                               for k, (a, b) in rule["features"].items())))


def classify(rules, scores):
    matches = [(match_score(r, scores), r["id"]) for r in rules if r["enabled"]]
    eligible = [(score, key) for score, key in matches
                if score >= next(r["threshold"] for r in rules if r["id"] == key)]
    return max(eligible)[1] if eligible else None
