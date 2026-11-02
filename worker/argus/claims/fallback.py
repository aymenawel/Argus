"""Notes written by code from the refs alone, when a model's answers fail the claim check twice or notes are paused
(spec §7.2). They say they were written by code, and why."""

from __future__ import annotations

from argus.claims.refs import CODE_OUTLINED, RefTable
from argus.plain import metric_words


def fallback_note(level: str, refs: RefTable, *, reason: str) -> dict:
    """One sentence per vessel and metric from its latest reading and its change since the start."""
    keys = sorted({tuple(i.split(":", 2)[1:]) for i in refs.ids() if i.startswith(("m:", "chg:"))})
    sentences = []
    for label, metric in keys:
        latest, change = refs.get(f"m:{label}:{metric}"), refs.get(f"chg:{label}:{metric}")
        lost = latest is not None and latest.kind == "last_reading"  # SAM lost the object after it (D-91)
        now = "at its last reading, before SAM stopped finding it" if lost else "now"
        coded = latest is not None and latest.label.endswith(CODE_OUTLINED)  # SAM found nothing; code drew it (D-93)
        parts = (
            [f"{latest.display} {now}" + (" (outlined by Argus's own code, not SAM)" if coded else "")]
            if latest is not None
            else []
        )
        if change is not None:
            parts.append(
                f"{change.display} {'from its first reading to its last' if lost else 'since its first reading'}"
            )
        sentences.append(f"Sample {label}: {metric_words(metric)} " + ", ".join(parts) + ".")
    return {
        "level": level,
        "observation": " ".join(sentences) if sentences else "No readings yet.",
        "interpretation": "",
        "hypothesis_status": None,
        "confidence": None,
        "confidence_reason": "",
        "rival_explanations": [],
        "next_step": "",
        "refs_used": [i for i in refs.ids() if i.startswith(("m:", "chg:"))],
        "evidence_ids": [],
        "question_for_researcher": "",
        "written_by": "code",
        "reason": reason,
    }
