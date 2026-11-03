"""The words a reader with no lab training sees (D-95): the code keeps its names; pages, notes and videos use these."""

from argus.domain import Role

# A measurement's id as a person would say it; an id not listed reads as its words ("root_length" → "root length").
METRIC_WORDS = {
    "delta_e": "colour change",
    "germinated_count": "sprouted seeds",
    "sprouted": "sprouted seeds",
    "skeleton_length": "length",
    "component_count": "count",
    "lab_mean": "colour",
}

# Units as people write them: ΔE is the standard colour-difference number (about 1 is the smallest change an eye sees).
UNIT_WORDS = {"dE00": "ΔE", "mm2": "mm²", "Lab": "L*a*b*"}

ROLE_WORDS = {Role.CONTROL: "control", Role.TREATMENT: "test"}

# A verdict as the page names it: the stored level keeps its code name (INCONCLUSIVE reads "Unclear").
VERDICT_WORDS = {
    "SUPPORTED": "Supported",
    "NOT_SUPPORTED": "Not supported",
    "INCONCLUSIVE": "Unclear",
    "TOO_EARLY": "Too early",
}


def metric_words(metric: str) -> str:
    return METRIC_WORDS.get(metric, metric.replace("_", " "))


def unit_label(unit: str) -> str:
    if unit.endswith("/h"):
        return f"{unit_label(unit[:-2])} per hour"
    return UNIT_WORDS.get(unit, unit)


def role_word(role: Role) -> str:
    return ROLE_WORDS[role]


# What happened, as a clause, for the events a note may cite: the kinds are the code's names.
EVENT_WORDS = {
    "intervention": "a hand or object was at the samples",
    "rule": "a set threshold was crossed",
    "camera_moved": "the camera moved",
    "segment_failed": "SAM couldn't outline a picture",
    "interrupted": "the run was interrupted",
    "spend": "the spending limit was reached",
    "quality": "the picture had a problem",
    "missed": "SAM lost sight of something",
}


def event_words(kind: str) -> str:
    return EVENT_WORDS.get(kind, kind.replace("_", " "))
