"""Videos of a run (D-84, D-85): the timelapse with its curves drawn over it, and the highlights reel. Made only from
stored records (frames, outlines, readings, fits, events, notes, the verdict); no model is called and nothing is
recomputed, and every number on screen is formatted by the worker."""


class MediaError(Exception):
    """Drawing or encoding failed; the message is the reason (ffmpeg's own last line when it was ffmpeg)."""


class MediaRefused(Exception):
    """The run can't be made into a video yet (still running, no frames); the message is why."""
