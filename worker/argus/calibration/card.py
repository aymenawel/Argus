"""The Argus Card: a printable calibration card with ArUco markers and reference patches.

One definition in millimetres drives everything: the print sheet (SVG), the raster render used
in tests, and later the calibration code that finds the card in a frame. Card coordinates have
their origin at the card's top-left corner, x to the right, y down, in mm.

Two sizes share one layout, scaled by `marker_size_mm / 20`:
- standard: 20 mm markers, IDs 0-3, for desk and top-down views
- compact: 14 mm markers, IDs 4-7, to stand beside jars in a side view
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import cv2
import numpy as np

CARD_VERSION = 1
ARUCO_DICTIONARY_ID = cv2.aruco.DICT_4X4_50
MARKER_MODULES = 6  # 4x4 data bits plus a one-module black border

BASE_MARKER_MM = 20.0  # layout below is written for this marker size and scaled from it
BASE_WIDTH, BASE_HEIGHT = 110.0, 80.0
BASE_MARGIN = 5.0
BASE_PATCH, BASE_PATCH_GAP = 10.0, 2.0
BASE_PATCH_ROWS_Y = (29.0, 41.0)

NEUTRALS = (
    ("neutral_100", (255, 255, 255)),
    ("neutral_80", (204, 204, 204)),
    ("neutral_60", (153, 153, 153)),
    ("neutral_40", (102, 102, 102)),
    ("neutral_20", (51, 51, 51)),
    ("neutral_0", (0, 0, 0)),
)
COLOURS = (
    ("red", (200, 50, 45)),
    ("green", (46, 158, 74)),
    ("blue", (47, 85, 180)),
    ("cyan", (31, 166, 201)),
    ("magenta", (194, 51, 142)),
    ("yellow", (242, 198, 42)),
)

REPO = Path(__file__).resolve().parents[3]
INK = "#0B1220"
OUTLINE = "#9AA3AE"
FONT = "Inter, 'Segoe UI', Arial, sans-serif"


@cache
def aruco_dictionary() -> cv2.aruco.Dictionary:
    return cv2.aruco.getPredefinedDictionary(ARUCO_DICTIONARY_ID)


@dataclass(frozen=True)
class Marker:
    id: int
    x_mm: float  # top-left of the outer black border
    y_mm: float
    size_mm: float

    def corners_mm(self) -> np.ndarray:
        """Corners in ArUco order: top-left, top-right, bottom-right, bottom-left."""
        x, y, s = self.x_mm, self.y_mm, self.size_mm
        return np.float32([[x, y], [x + s, y], [x + s, y + s], [x, y + s]])


@dataclass(frozen=True)
class Patch:
    name: str
    rgb: tuple[int, int, int]
    x_mm: float
    y_mm: float
    size_mm: float


@dataclass(frozen=True)
class CardSpec:
    name: str
    marker_size_mm: float
    marker_ids: tuple[int, int, int, int]  # top-left, top-right, bottom-right, bottom-left
    scale_bar_mm: int

    @property
    def unit(self) -> float:
        return self.marker_size_mm / BASE_MARKER_MM

    @property
    def width_mm(self) -> float:
        return BASE_WIDTH * self.unit

    @property
    def height_mm(self) -> float:
        return BASE_HEIGHT * self.unit

    def markers(self) -> tuple[Marker, ...]:
        u, s = self.unit, self.marker_size_mm
        near, far_x, far_y = BASE_MARGIN * u, self.width_mm - BASE_MARGIN * u - s, self.height_mm - BASE_MARGIN * u - s
        positions = ((near, near), (far_x, near), (far_x, far_y), (near, far_y))
        return tuple(Marker(i, x, y, s) for i, (x, y) in zip(self.marker_ids, positions, strict=True))

    def patches(self) -> tuple[Patch, ...]:
        u = self.unit
        size, gap = BASE_PATCH * u, BASE_PATCH_GAP * u
        row_width = len(COLOURS) * size + (len(COLOURS) - 1) * gap
        x0 = (self.width_mm - row_width) / 2
        rows = zip(BASE_PATCH_ROWS_Y, (NEUTRALS, COLOURS), strict=True)
        return tuple(
            Patch(name, rgb, x0 + i * (size + gap), row_y * u, size)
            for row_y, row in rows
            for i, (name, rgb) in enumerate(row)
        )


STANDARD = CardSpec("standard", 20.0, (0, 1, 2, 3), scale_bar_mm=40)
COMPACT = CardSpec("compact", 14.0, (4, 5, 6, 7), scale_bar_mm=30)
CARDS = (STANDARD, COMPACT)


def marker_bits(marker_id: int) -> np.ndarray:
    """6x6 boolean grid, True where the module is black."""
    return cv2.aruco.generateImageMarker(aruco_dictionary(), marker_id, MARKER_MODULES) == 0


def render_raster(spec: CardSpec, px_per_mm: float) -> np.ndarray:
    """BGR image of the card's markers and patches (no text), used for tests and previews."""
    height, width = round(spec.height_mm * px_per_mm), round(spec.width_mm * px_per_mm)
    image = np.full((height, width, 3), 255, np.uint8)
    for marker in spec.markers():
        side = round(marker.size_mm * px_per_mm)
        tile = cv2.aruco.generateImageMarker(aruco_dictionary(), marker.id, side)
        x, y = round(marker.x_mm * px_per_mm), round(marker.y_mm * px_per_mm)
        image[y : y + side, x : x + side] = tile[:, :, None]
    for patch in spec.patches():
        x0, y0 = round(patch.x_mm * px_per_mm), round(patch.y_mm * px_per_mm)
        x1, y1 = round((patch.x_mm + patch.size_mm) * px_per_mm), round((patch.y_mm + patch.size_mm) * px_per_mm)
        image[y0:y1, x0:x1] = patch.rgb[::-1]
    return image


# --- SVG (print) -------------------------------------------------------------------------


def _f(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _text(
    x: float, y: float, size: float, body: str, *, weight: int = 400, anchor: str = "start", fill: str = INK
) -> str:
    return (
        f'<text x="{_f(x)}" y="{_f(y)}" font-family="{FONT}" font-size="{_f(size)}" font-weight="{weight}" '
        f'text-anchor="{anchor}" fill="{fill}">{body}</text>'
    )


def _marker_svg(marker: Marker) -> str:
    module = marker.size_mm / MARKER_MODULES
    rects = []
    for row, bits in enumerate(marker_bits(marker.id)):
        col = 0
        while col < MARKER_MODULES:
            if not bits[col]:
                col += 1
                continue
            start = col
            while col < MARKER_MODULES and bits[col]:
                col += 1
            rects.append(
                f'<rect x="{_f(marker.x_mm + start * module)}" y="{_f(marker.y_mm + row * module)}" '
                f'width="{_f((col - start) * module)}" height="{_f(module)}"/>'
            )
    return f'<g id="marker-{marker.id}" fill="#000" shape-rendering="crispEdges">{"".join(rects)}</g>'


@cache
def _mark_inner_svg() -> str:
    source = (REPO / "brand" / "argus-mark.svg").read_text(encoding="utf-8")
    match = re.search(r"<svg[^>]*>(.*)</svg>", source, re.DOTALL)
    if match is None:
        raise ValueError("brand/argus-mark.svg has no <svg> element")
    return match.group(1)


def _scale_bar_svg(spec: CardSpec) -> str:
    u = spec.unit
    length = spec.scale_bar_mm
    x0, y0 = (spec.width_mm - length) / 2, 62.0 * u
    parts = [
        f'<line x1="{_f(x0)}" y1="{_f(y0)}" x2="{_f(x0 + length)}" y2="{_f(y0)}" stroke="{INK}" stroke-width="0.2"/>'
    ]
    for mm in range(length + 1):
        tick = 3.0 * u if mm % 10 == 0 else 2.0 * u if mm % 5 == 0 else 1.2 * u
        parts.append(
            f'<line x1="{_f(x0 + mm)}" y1="{_f(y0)}" x2="{_f(x0 + mm)}" y2="{_f(y0 - tick)}" '
            f'stroke="{INK}" stroke-width="0.15"/>'
        )
        if mm % 10 == 0:
            parts.append(_text(x0 + mm, y0 + 3.2 * u, 2.4 * u, str(mm), anchor="middle"))
    parts.append(_text(x0 + length / 2, y0 + 6.6 * u, 2.4 * u, "millimetres", anchor="middle", fill="#4A5565"))
    return "".join(parts)


def render_card_svg(spec: CardSpec) -> str:
    """SVG group for one card in card-mm coordinates (place it with a transform)."""
    u = spec.unit
    patches = []
    for patch in spec.patches():
        stroke = f' stroke="{OUTLINE}" stroke-width="0.15"' if patch.rgb == (255, 255, 255) else ""
        patches.append(
            f'<rect x="{_f(patch.x_mm)}" y="{_f(patch.y_mm)}" width="{_f(patch.size_mm)}" '
            f'height="{_f(patch.size_mm)}" fill="{_hex(patch.rgb)}"{stroke}/>'
        )
    ids = f"{spec.marker_ids[0]}–{spec.marker_ids[-1]}"
    header_x = 31.0 * u
    return "".join(
        [
            f'<g id="card-{spec.name}">',
            f'<rect x="0" y="0" width="{_f(spec.width_mm)}" height="{_f(spec.height_mm)}" fill="#FFF" '
            f'stroke="{OUTLINE}" stroke-width="0.25" stroke-dasharray="1.5 1"/>',
            f'<svg x="{_f(header_x)}" y="{_f(7.5 * u)}" width="{_f(12 * u)}" height="{_f(12 * u)}" viewBox="0 0 64 64">'
            f"{_mark_inner_svg()}</svg>",
            _text(header_x + 14 * u, 13.2 * u, 4.6 * u, "ARGUS CARD", weight=650),
            _text(
                header_x + 14 * u,
                18.4 * u,
                2.5 * u,
                f"v{CARD_VERSION} · {spec.name} · markers {_f(spec.marker_size_mm)} mm",
            ),
            _text(header_x + 14 * u, 21.9 * u, 2.5 * u, f"ArUco 4x4 · IDs {ids}", fill="#4A5565"),
            *patches,
            _scale_bar_svg(spec),
            *(_marker_svg(m) for m in spec.markers()),
            "</g>",
        ]
    )


PAPERS = {"letter": (215.9, 279.4), "a4": (210.0, 297.0)}

INSTRUCTIONS = (
    "Print at 100% (“Actual size”). Turn off “Fit to page” and any scaling.",
    "Check the print: the line above must measure exactly 100 mm. Argus asks for this number during setup.",
    "Cut along the dashed outline. Glue the card onto stiff cardboard so it stays flat. Plain matte paper, not glossy.",
    "Place the card in the same plane as what you measure (for jars: level with the front walls), facing the camera.",
    "Standard card: desk and top-down views. Compact card: beside jars in a side view. Keep one card fully in frame.",
)


def _placed(spec: CardSpec, x_mm: float, y_mm: float) -> str:
    return f'<g transform="translate({_f(x_mm)} {_f(y_mm)})">{render_card_svg(spec)}</g>'


def render_sheet_svg(paper: str = "letter") -> str:
    """Full printable page with both cards, a 100 mm print check and instructions."""
    page_w, page_h = PAPERS[paper]
    centre = page_w / 2
    standard_y, compact_y = 30.0, 122.0
    check_y, check_x0 = 196.0, centre - 50.0
    check = [
        f'<line x1="{_f(check_x0)}" y1="{_f(check_y)}" x2="{_f(check_x0 + 100)}" y2="{_f(check_y)}" '
        f'stroke="{INK}" stroke-width="0.3"/>'
    ]
    for mm in range(0, 101, 5):
        tick = 4.0 if mm % 10 == 0 else 2.5
        check.append(
            f'<line x1="{_f(check_x0 + mm)}" y1="{_f(check_y)}" x2="{_f(check_x0 + mm)}" '
            f'y2="{_f(check_y - tick)}" stroke="{INK}" stroke-width="0.25"/>'
        )
        if mm % 10 == 0:
            check.append(_text(check_x0 + mm, check_y + 4.0, 2.6, str(mm), anchor="middle"))
    instructions = [_text(25.0, 214.0 + i * 7.0, 3.1, f"{i + 1}.  {line}") for i, line in enumerate(INSTRUCTIONS)]
    return "".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{_f(page_w)}mm" height="{_f(page_h)}mm" '
            f'viewBox="0 0 {_f(page_w)} {_f(page_h)}">',
            f'<rect width="{_f(page_w)}" height="{_f(page_h)}" fill="#FFF"/>',
            _text(25.0, 16.0, 6.0, "Argus Card", weight=650),
            _text(
                25.0,
                22.5,
                3.2,
                f"Calibration card v{CARD_VERSION}: millimetre scale, viewing angle and colour drift",
                fill="#4A5565",
            ),
            _placed(STANDARD, centre - STANDARD.width_mm / 2, standard_y),
            _placed(COMPACT, centre - COMPACT.width_mm / 2, compact_y),
            _text(centre, check_y - 7.0, 3.2, "Print check: this line is 100 mm", weight=600, anchor="middle"),
            *check,
            *instructions,
            _text(
                25.0,
                page_h - 12.0,
                2.6,
                "ArUco DICT_4X4_50 · standard IDs 0–3 (20 mm) · compact IDs 4–7 (14 mm) · github.com/aymenawel/Argus",
                fill="#4A5565",
            ),
            "</svg>",
        ]
    )
