"""Drawing one video frame (D-84): the run's frame on the left with each vessel's outline, its curves up to now on
the right, the clock, the caption and the source. Text and lines are drawn at 2× on a transparent layer and scaled
down onto the photo, so they stay sharp; the typeface is Inter, as in the app.

Every word and number comes from stored records (layout.py says which); this module only places them.
"""

from __future__ import annotations

import math
from collections import OrderedDict
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from argus.config import Settings
from argus.domain import Role, RunMode
from argus.media import MediaError
from argus.media.layout import (
    PALETTE,
    Group,
    Slot,
    axis_time,
    caption_at,
    chart_note,
    clock_text,
    condition_groups,
    group_key,
    metric_title,
    segments,
    source_line,
)
from argus.media.records import RunRecords

FONT_PATH = Path(__file__).parent / "fonts" / "Inter[opsz,wght].ttf"
W, H = 1920, 1080
X2 = 2  # the overlay is drawn at twice the size and scaled down
FRAME = (40, 40, 1240, 1000)  # x, y, width, height the run's frame is fitted into
PANEL_X, PANEL_R = 1320, 1880
PLOT = (1380, 190, 1880, 660)  # x0, y0, x1, y1 of the curves; the y labels sit left of it
CAPTION_Y, CAPTION_BOTTOM = 760, 975
SOURCE_Y, SOURCE_LINES, SOURCE_LINE_HEIGHT = 1004, 3, 22  # room for the longest credit with its licence, uncut
DOTS_UP_TO = 150  # readings per vessel drawn as dots too; a denser series is clearer as a line alone


@lru_cache(maxsize=32)
def font(size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    """Inter at `size` px (drawn at 2×); its optical size follows the size, within the font's 14–32 range."""
    face = ImageFont.truetype(str(FONT_PATH), size * X2)
    face.set_variation_by_axes([min(32, max(14, size)), weight])
    return face


def SOURCE_FONT() -> ImageFont.FreeTypeFont:  # noqa: N802 - a constant, read through the font cache
    return font(16, 400)


def colour(name: str, alpha: int = 255) -> tuple[int, int, int, int]:
    hex_ = PALETTE[name].lstrip("#")
    return (int(hex_[0:2], 16), int(hex_[2:4], 16), int(hex_[4:6], 16), alpha)


def wrap(text: str, face: ImageFont.FreeTypeFont, width: float, max_lines: int) -> list[str]:
    """Lines of text no wider than width (2× pixels); past max_lines the last one ends with an ellipsis."""
    lines: list[str] = []
    for word in text.split():
        if lines and face.getlength(f"{lines[-1]} {word}") <= width:
            lines[-1] = f"{lines[-1]} {word}"
        else:
            lines.append(word)
    if len(lines) > max_lines:
        last = lines[max_lines - 1]
        while last and face.getlength(f"{last}…") > width:
            last = last.rsplit(" ", 1)[0] if " " in last else last[:-1]
        lines = [*lines[: max_lines - 1], f"{last}…"]
    return lines


def dashed(draw: ImageDraw.ImageDraw, points: Sequence[tuple[float, float]], fill, width: int, dash) -> None:
    """A polyline; with a dash pattern (on, off) in 2× pixels, drawn as dashes along its whole length."""
    if len(points) < 2:
        return
    if dash is None:
        draw.line(list(points), fill=fill, width=width, joint="curve")
        return
    on, off = dash
    drawing, left = True, on
    for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
        length = math.hypot(x1 - x0, y1 - y0)
        done = 0.0
        while done < length:
            step = min(left, length - done)
            a, b = done / length, (done + step) / length
            if drawing:
                draw.line(
                    [(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)],
                    fill=fill,
                    width=width,
                )
            done += step
            left -= step
            if left <= 1e-9:
                drawing = not drawing
                left = on if drawing else off


def marker(draw: ImageDraw.ImageDraw, x: float, y: float, shape: str, r: float, fill) -> None:
    if shape == "square":
        draw.rectangle([x - r, y - r, x + r, y + r], fill=fill)
    elif shape == "diamond":
        draw.polygon([(x, y - r * 1.3), (x + r * 1.3, y), (x, y + r * 1.3), (x - r * 1.3, y)], fill=fill)
    else:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=fill)


class Drawer:
    """Draws frames of one run. Photos are decoded once and kept for the next few frames."""

    def __init__(self, records: RunRecords, settings: Settings) -> None:
        self.records, self.settings = records, settings
        run = records.run
        self.ts = [f.t for f in records.frames]
        t0, t1 = self.ts[0], self.ts[-1]
        self.t_range = (t0, t1 if t1 > t0 else t0 + 1.0)
        # Live runs start their clock at the real start, shown in this machine's time; an imported run shows a time of
        # day only when its start was given.
        live = run.started_at.astimezone() if run.mode is RunMode.LIVE else None
        self.start = run.source.start_time or live
        fits = records.fits
        self.groups = condition_groups(fits["vessels"])
        self.note = chart_note(fits)
        self.metric = metric_title(fits["metric"], fits["unit"])
        self.source = source_line(run)
        readings = [v for vessel in fits["vessels"] for _, v in vessel["readings"]]
        values = readings + [v for vessel in fits["vessels"] if vessel["fit"] for _, v in vessel["fit"]["samples"]]
        low, high = (min(values), max(values)) if values else (0.0, 1.0)
        pad = (high - low) * 0.05 or 1.0
        self.y_range = (low - pad, high + pad)
        self.y_labels = (min(readings), max(readings)) if readings else ()  # the readings' own extremes, not the fit's
        self.controls = {v.id for v in records.vessels if v.role is Role.CONTROL}
        self._photos: OrderedDict[int, tuple[Image.Image, float]] = OrderedDict()

    # ---- the photo ----

    def _photo(self, index: int) -> tuple[Image.Image, float]:
        """Frame `index` fitted into the frame box, and the scale from its own pixels to the fitted ones."""
        if index in self._photos:
            self._photos.move_to_end(index)
            return self._photos[index]
        frame = self.records.frames[index]
        path = self.settings.data_dir / frame.path
        try:
            bgr = cv2.imdecode(np.frombuffer(path.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
        except OSError as error:
            raise MediaError(f"a frame can't be read: {frame.path}") from error
        if bgr is None:
            raise MediaError(f"a frame can't be read: {frame.path}")
        image = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        _, _, box_w, box_h = FRAME
        scale = min(box_w / image.width, box_h / image.height)
        fitted = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
        self._photos[index] = (fitted, scale)
        if len(self._photos) > 4:
            self._photos.popitem(last=False)
        return fitted, scale

    # ---- one frame ----

    def run_frame(self, slot: Slot, caption_kind: str | None = None, caption: str | None = None) -> Image.Image:
        photo, scale = self._photo(slot.a)
        if slot.b is not None and slot.w > 0:
            other, _ = self._photo(slot.b)
            if other.size != photo.size:
                other = other.resize(photo.size, Image.Resampling.LANCZOS)
            photo = Image.blend(photo, other, slot.w)
        fx, fy, box_w, box_h = FRAME
        x0, y0 = fx + (box_w - photo.width) // 2, fy + (box_h - photo.height) // 2
        base = Image.new("RGB", (W, H), colour("ground")[:3])
        base.paste(photo, (x0, y0))

        layer = Image.new("RGBA", (W * X2, H * X2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        self._outlines(draw, self.records.frames[slot.a].id, x0, y0, scale)
        self._clock(draw, slot.t)
        self._chart(draw, slot.t)
        if caption is None and caption_kind is None:
            caption = caption_at(self.records.notes, slot.t)
        self._caption(draw, caption_kind, caption)
        self._source(draw)
        return self._finish(base, layer)

    def card(self, lines: Sequence[str]) -> Image.Image:
        """A title or end card: the first line large, the rest below it, centred."""
        base = Image.new("RGB", (W, H), colour("ground")[:3])
        layer = Image.new("RGBA", (W * X2, H * X2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        blocks = []
        for i, line in enumerate(lines):
            face = font(56, 600) if i == 0 else font(32, 400)
            blocks += [(face, text, i == 0) for text in wrap(line, face, 1400 * X2, 4)]
        heights = [face.size * 1.3 for face, _, _ in blocks]
        y = (H * X2 - sum(heights)) / 2
        for (face, text, first), height in zip(blocks, heights, strict=True):
            width = face.getlength(text)
            draw.text(((W * X2 - width) / 2, y), text, font=face, fill=colour("text" if first else "muted"))
            y += height
        return self._finish(base, layer)

    def _finish(self, base: Image.Image, layer: Image.Image) -> Image.Image:
        small = layer.resize((W, H), Image.Resampling.LANCZOS)
        return Image.alpha_composite(base.convert("RGBA"), small).convert("RGB")

    # ---- the parts ----

    def _outlines(self, draw: ImageDraw.ImageDraw, frame_id: str, x0: int, y0: int, scale: float) -> None:
        for vessel_id, polygons in self.records.outlines.get(frame_id, []):
            fill = colour("muted" if vessel_id in self.controls else "accent")
            for polygon in polygons:
                points = [((x0 + x * scale) * X2, (y0 + y * scale) * X2) for x, y in polygon]
                if len(points) >= 2:
                    draw.line([*points, points[0]], fill=fill, width=3 * X2, joint="curve")

    def _clock(self, draw: ImageDraw.ImageDraw, t: float) -> None:
        run_time, _, day_time = clock_text(t, self.start).partition(" · ")
        face = font(56, 600)
        x, y = PANEL_X * X2, 48 * X2
        draw.text((x, y), run_time, font=face, fill=colour("text"))
        if day_time:
            draw.text((x + face.getlength(f"{run_time}  "), y), f"· {day_time}", font=face, fill=colour("muted"))

    def _xy(self, t: float, value: float) -> tuple[float, float]:
        x0, y0, x1, y1 = PLOT
        (t0, t1), (v0, v1) = self.t_range, self.y_range
        return ((x0 + (t - t0) / (t1 - t0) * (x1 - x0)) * X2, (y1 - (value - v0) / (v1 - v0) * (y1 - y0)) * X2)

    def _chart(self, draw: ImageDraw.ImageDraw, t: float) -> None:
        draw.text((PANEL_X * X2, 150 * X2), self.metric, font=font(22, 600), fill=colour("text"))
        x0, y0, x1, y1 = PLOT
        if self.note is not None:
            draw.text((PANEL_X * X2, (y0 + 40) * X2), self.note, font=font(22, 400), fill=colour("muted"))
            return
        axis = colour("muted", 110)
        draw.line([(x0 * X2, y0 * X2), (x0 * X2, y1 * X2), (x1 * X2, y1 * X2)], fill=axis, width=2 * X2)
        label = font(16, 400)
        for value in self.y_labels:
            text = f"{value:.3g}"
            _, y = self._xy(self.t_range[0], value)
            draw.text(
                ((x0 - 8) * X2 - label.getlength(text), y - label.size / 2), text, font=label, fill=colour("muted")
            )
        for t_label in self.t_range:
            text = axis_time(t_label, self.t_range[1] - self.t_range[0])
            x, _ = self._xy(t_label, self.y_range[0])
            x = min(x, x1 * X2 - label.getlength(text))
            draw.text((x, (y1 + 8) * X2), text, font=label, fill=colour("muted"))

        vessels = sorted(self.records.fits["vessels"], key=lambda v: v["role"] != "control")  # treatments on top
        for vessel in vessels:
            group = self.groups[group_key(vessel)]
            fill = colour("muted" if group.control else "accent")
            shown = [(rt, v) for rt, v in vessel["readings"] if rt <= t + 1e-6]
            for run_ in segments(shown):
                draw.line([self._xy(*p) for p in run_], fill=fill[:3] + (120,), width=2 * X2)
            if len(vessel["readings"]) <= DOTS_UP_TO:
                for point in shown:
                    marker(draw, *self._xy(*point), group.marker, 4 * X2, fill)
            fit = vessel["fit"]
            if fit and fit.get("ok") and fit["samples"]:
                curve = [self._xy(st, v) for st, v in fit["samples"] if st <= t + 1e-6]
                dash = (group.dash[0] * X2 * 2, group.dash[1] * X2 * 2) if group.dash else None
                dashed(draw, curve, fill, 3 * X2, dash)
        cursor, _ = self._xy(min(max(t, self.t_range[0]), self.t_range[1]), self.y_range[0])
        draw.line([(cursor, y0 * X2), (cursor, y1 * X2)], fill=colour("text", 150), width=2 * X2)
        self._legend(draw)

    def _legend(self, draw: ImageDraw.ImageDraw) -> None:
        face = font(18, 400)
        x, y = PANEL_X * X2, 705 * X2
        for group in self.groups.values():
            width = (24 + 8) * X2 + face.getlength(group.label)
            if x + width > PANEL_R * X2 and x > PANEL_X * X2:
                x, y = PANEL_X * X2, y + 28 * X2
            self._legend_mark(draw, x, y + 11 * X2, group)
            draw.text((x + 24 * X2, y), group.label, font=face, fill=colour("text"))
            x += width + 16 * X2

    def _legend_mark(self, draw: ImageDraw.ImageDraw, x: float, y: float, group: Group) -> None:
        fill = colour("muted" if group.control else "accent")
        dash = (group.dash[0] * X2, group.dash[1] * X2) if group.dash else None
        dashed(draw, [(x, y), (x + 18 * X2, y)], fill, 3 * X2, dash)
        marker(draw, x + 9 * X2, y, group.marker, 4 * X2, fill)

    def _caption(self, draw: ImageDraw.ImageDraw, kind: str | None, caption: str | None) -> None:
        y = CAPTION_Y * X2
        if kind:
            kind_face = font(18, 600)
            draw.text((PANEL_X * X2, y), kind, font=kind_face, fill=colour("accent"))
            y += 32 * X2
        if not caption:
            return
        face = font(26, 400)
        line_height = 36 * X2
        room = max(1, int((CAPTION_BOTTOM * X2 - y) // line_height))
        for line in wrap(caption, face, (PANEL_R - PANEL_X) * X2, min(5, room)):
            draw.text((PANEL_X * X2, y), line, font=face, fill=colour("text"))
            y += line_height

    def _source(self, draw: ImageDraw.ImageDraw) -> None:
        face = SOURCE_FONT()
        y = SOURCE_Y * X2
        for line in wrap(self.source, face, (PANEL_R - PANEL_X) * X2, SOURCE_LINES):
            draw.text((PANEL_X * X2, y), line, font=face, fill=colour("muted"))
            y += SOURCE_LINE_HEIGHT * X2
