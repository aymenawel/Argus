# 09 · Measurement and calibration

> Calibration turns "it looks bigger" into numbers a researcher would put in a report. Card layout below is **[proposed]**; adjust after testing with the real camera.

## The Argus Card [decided, v1 built Oct 27, D-47]

**Print files:** `assets/argus-card/argus-card-v1-letter.pdf` (US Letter) and `-a4.pdf`, generated from one definition in `worker/argus/calibration/card.py` (`uv run python -m argus.calibration.card_export --out ../assets/argus-card`). One page holds two cards plus a 100 mm print-check line and instructions:

| Card | Size | Markers (ArUco `DICT_4X4_50`) | Use |
| --- | --- | --- | --- |
| Standard | 110 × 80 mm | 20 mm, IDs 0 (top-left), 1, 2, 3 clockwise | Desk and top-down views |
| Compact | 77 × 56 mm (same layout × 0.7) | 14 mm, IDs 4–7 | Beside jars in a side view |

Each card: 4 corner markers with a white quiet zone of at least one module, a 6-step neutral ramp (sRGB 255/204/153/102/51/0), 6 color patches (red, green, blue, cyan, magenta, yellow; values in `card.py`), a mm scale bar (40 mm / 30 mm) and the Argus mark. Printed colors are used as **relative** references against the first frame, so printer accuracy doesn't matter. Checked: both sizes detect with the right IDs; after a strong perspective tilt the marker homography recovers patch positions within 0.15 mm (`worker/tests/test_card.py`); in the exported artwork markers measure 19.90 / 13.97 mm against 20 / 14 (within one preview pixel).

The concept notes below still apply.

A free printable card placed in the frame **on the same plane as the subject, parallel to the camera** (PlantCV's docs give the same caveat for any scale card).

- **4 ArUco markers** at the corners (e.g. dictionary `DICT_4X4_50`, IDs 0–3, each 20 mm, known spacing). Detection gives mm-per-pixel and a homography to correct the viewing angle.
- **Neutral patches** (white, mid-gray, black) for white balance and exposure drift.
- **A few color patches** for relative color correction. Home printers aren't color-accurate, so the printed card gives **relative** correction; a real ColorChecker gives **absolute** color when a lab has one.
- Print at 100% scale and check one marker with a ruler; store the measured size in the calibration record.

```python
import cv2
d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
det = cv2.aruco.ArucoDetector(d, cv2.aruco.DetectorParameters())
corners, ids, _ = det.detectMarkers(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
```

ArUco detection is in OpenCV's `objdetect` module (`cv2.aruco.ArucoDetector`, OpenCV ≥4.7). **Checked Oct 27:** `opencv-python` 5.0.0 has it; `generateImageMarker` + `ArucoDetector.detectMarkers` found all 4 card markers (IDs 0–3) on a perspective-warped page (`worker/probes/camera.py`). No contrib package needed.

**Pipeline:** detect markers → homography (straight-on view) → mm per pixel → color correction from neutral/color patches → measure inside each vessel mask.

Optional later: PlantCV `detect_color_card` + `correct_color` (supports ColorChecker Passport/Classic/Mini/Nano and custom chip sizes, and sets the measurement scale from chip size), or `colour-checker-detection` (BSD-3; its YOLO script is AGPL, avoid that part).

## Microscope calibration

A stage micrometer slide gives µm per pixel for each objective; saved as a named profile per microscope + zoom.

## Quantitative color: standard curves

For color-change experiments, place a few vials of **known concentration** in the frame. Argus fits a calibration curve from their (corrected) color and converts the unknown's color into a concentration with an error range. This is how low-cost smartphone colorimetry is done in the literature.

## Lock the camera (Windows) [verify on your camera]

Auto-exposure, auto white balance and autofocus make color and brightness drift. Try, in order:

1. Open with DirectShow: `cv2.VideoCapture(index, cv2.CAP_DSHOW)`.
2. Set properties and **read them back** to confirm they took effect: `CAP_PROP_AUTO_EXPOSURE` (on DirectShow commonly `0.25` = manual, `0.75` = auto), `CAP_PROP_EXPOSURE` (DirectShow uses negative log2 seconds, e.g. `-6`), `CAP_PROP_AUTO_WB` = 0 then `CAP_PROP_WB_TEMPERATURE`, `CAP_PROP_AUTOFOCUS` = 0 then `CAP_PROP_FOCUS`.
3. If a property is ignored: `cap.set(cv2.CAP_PROP_SETTINGS, 1)` opens the driver's settings dialog on DirectShow, or lock settings in the camera's own app.
4. If nothing works: warn the researcher that brightness/color readings will drift, rely more on the card's neutral patches, and record "unlocked" in the run record.

Values and support differ by camera and driver; treat these as starting points, not facts.

**Checked Oct 27 on the laptop's built-in HP Wide Vision HD camera** (the Nuroum V11 was not connected): MJPEG 1280×720 @ 30 fps delivered (its maximum). `set()` returned `True` for every property, but only white balance read back as locked (`AUTO_WB` 1 → 0, `WB_TEMPERATURE` 4000 → 4500); `AUTO_EXPOSURE` reads back `-1` (unsupported), so exposure lock is **unknown** on this driver. Lesson: a `True` from `set()` proves nothing; Argus records each property as locked / not locked / unknown from the read-back, and leans on the card's neutral patch when exposure can't be confirmed. The Nuroum test (2560×1440 MJPEG, exposure lock, closest sharp distance) is still open.

## Frame-quality checks

| Check | Method | Action |
| --- | --- | --- |
| Blur | Variance of Laplacian below threshold | Skip frame, log |
| Glare / over-exposure | % of saturated pixels in a vessel ROI | Skip or flag vessel |
| Occlusion / hand in frame | Large sudden change outside vessels or covering ROIs | Pause measuring, log likely intervention, ask the researcher |
| Camera moved | ArUco marker positions shift | Re-run homography; flag measurements during the move |
| Lighting | Card neutral patch drift | Correct; warn if beyond correction range |

**Lighting check in setup (30 s):** warns about windows (day/night cycles), flicker and shadows; suggests diffuse light, or back lighting for cloudiness and foam.

## Measurement methods (code, not AI)

| Metric | Method |
| --- | --- |
| Area | Mask pixel count × (mm per px)² |
| Height / level | Top edge of mask along the vessel axis (side view), in mm |
| Length (roots, cracks, stems) | `skimage.morphology.skeletonize` then path length |
| Count | Connected components / SAM instances, with size filter |
| Color | Mean and spread in Lab inside the mask; ΔE from baseline |
| Cloudiness | Brightness/contrast of a background pattern seen through the vessel |
| Angle | Fitted line on the skeleton vs vertical |

Every metric records a `method_version` so old runs can be re-measured later.

## Noise floor and ±

First minutes: measure static things (background, card, empty region). Their spread is the noise floor. Each measurement's ± combines noise floor and calibration error (propagate with `uncertainties`). Effects below ~3× the noise floor are labeled "not real yet."
