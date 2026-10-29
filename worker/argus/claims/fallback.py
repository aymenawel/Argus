"""Notes written by code from the refs alone, when a model's answers fail the claim check twice or notes are paused
(spec §7.2). They say they were written by code, and why."""

from __future__ import annotations

from argus.claims.refs import RefTable


def fallback_note(level: str, refs: RefTable, *, reason: str) -> dict:
    """One sentence per vessel and metric from its latest reading and its change since the start."""
    keys = sorted({tuple(i.split(":", 2)[1:]) for i in refs.ids() if i.startswith(("m:", "chg:"))})
    sentences = []
    for label, metric in keys:
        latest, change = refs.get(f"m:{label}:{metric}"), refs.get(f"chg:{label}:{metric}")
        parts = [f"{latest.display} now"] if latest is not None else []
        if change is not None:
            parts.append(f"{change.display} since its first reading")
        sentences.append(f"Vessel {label}: {metric} " + ", ".join(parts) + ".")
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
