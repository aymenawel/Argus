"""Day-one probes: small, re-runnable checks of the Meta Model API and local hardware.

Run from `worker/` with the repo's `.env` loaded, for example:
    uv run --env-file ../.env python -m probes.sam
Results are written to `probes/out/` (git-ignored) and summarized in
`docs/knowledge-base/16-open-questions.md`.
"""
