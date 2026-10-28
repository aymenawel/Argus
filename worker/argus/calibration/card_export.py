"""Export the printable Argus Card sheet as SVG, PDF and a PNG preview.

PDF and PNG are produced by printing the SVG through a headless Chromium browser (Edge or
Chrome), which honours the page size in millimetres. Usage, from worker/:
    uv run python -m argus.calibration.card_export --out ../assets/argus-card
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .card import CARD_VERSION, PAPERS, render_sheet_svg

CSS_PX_PER_MM = 96 / 25.4
PREVIEW_SCALE = 2.5  # device pixels per CSS pixel in the PNG preview

BROWSER_CANDIDATES = (
    os.environ.get("ARGUS_BROWSER", ""),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "msedge",
    "google-chrome",
    "chromium",
)


def find_browser() -> str:
    for candidate in BROWSER_CANDIDATES:
        if candidate and (Path(candidate).is_file() or shutil.which(candidate)):
            return candidate
    raise FileNotFoundError("No Edge or Chrome found; set ARGUS_BROWSER to a Chromium browser executable")


def _html(svg: str, paper: str) -> str:
    width, height = PAPERS[paper]
    return (
        "<!doctype html><meta charset='utf-8'><title>Argus Card</title>"
        f"<style>@page {{ size: {width}mm {height}mm; margin: 0 }} html, body {{ margin: 0; background: #fff }}"
        " svg { display: block }</style>"
        f"{svg}"
    )


def _run_browser(browser: str, *args: str) -> None:
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={profile}", *args],
            check=True,
            capture_output=True,
            timeout=120,
        )


def export(out_dir: Path) -> list[Path]:
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    browser = find_browser()
    written = []
    with tempfile.TemporaryDirectory() as work:
        for paper, (width_mm, height_mm) in PAPERS.items():
            stem = f"argus-card-v{CARD_VERSION}-{paper}"
            svg = render_sheet_svg(paper)
            (out_dir / f"{stem}.svg").write_text(svg, encoding="utf-8")
            html = Path(work) / f"{stem}.html"
            html.write_text(_html(svg, paper), encoding="utf-8")
            pdf = out_dir / f"{stem}.pdf"
            _run_browser(browser, "--no-pdf-header-footer", f"--print-to-pdf={pdf}", html.as_uri())
            written += [out_dir / f"{stem}.svg", pdf]
            if paper == "letter":
                png = out_dir / f"{stem}-preview.png"
                size = f"{round(width_mm * CSS_PX_PER_MM)},{round(height_mm * CSS_PX_PER_MM)}"
                _run_browser(
                    browser,
                    f"--window-size={size}",
                    f"--force-device-scale-factor={PREVIEW_SCALE}",
                    f"--screenshot={png}",
                    html.as_uri(),
                )
                written.append(png)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="output directory")
    for path in export(parser.parse_args().out):
        print(path)


if __name__ == "__main__":
    main()
