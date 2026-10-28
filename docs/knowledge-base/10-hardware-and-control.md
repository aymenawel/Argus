# 10 · Hardware, sensors and control

## Build machine

| Part | Spec | Consequence |
| --- | --- | --- |
| CPU | AMD Ryzen 7 6800H | Watcher, measurements, stats, ffmpeg all fine on CPU |
| GPU | NVIDIA RTX 3050 Laptop, **4 GB VRAM** | Bottleneck for local models |
| RAM | 16 GB | Fine |
| OS | Windows | Use DirectShow for cameras; paths like `C:\Projects\Argus` |

### Can SAM 3.1 run locally?

Partly. SAM 3.1 is ~0.9B parameters (~1.8 GB in fp16).

- **Likely works:** single-image mode, fp16, reduced input resolution (e.g. 672 or 504 instead of 1008), a few seconds per frame. Enough for **Smart trigger**.
- **Likely fails:** SAM's video tracking (memory of past frames), Continuous mode at high rates, running alongside another local model.
- Weights are **gated** on Hugging Face (`facebook/sam3.1`, license listed as "other"); code at github.com/facebookresearch/sam3.

**Decision:** use the **Meta SAM API by default** (simple, ~$14 for the whole build). Local image-mode SAM is an optional fallback behind `SEGMENT_BACKEND`, not a build-week task. Modal ($30 signup credit) is the backup for heavy SAM video if needed.

Muse Spark Open (~816B params) and Muse Glimmer (30B) cannot run on this laptop.

## Hardware tiers

| Tier | Hardware | Unlocks |
| --- | --- | --- |
| 0 | Laptop webcam or phone, printed Argus Card | Every desk recipe |
| 1 | USB webcam on a stand, smart plug | Plant mode, light/heater control, long unattended runs |
| 2 | USB microscope (shows up as a webcam), Bluetooth thermometer, Raspberry Pi camera node | Cell/microbe recipes, temperature as a tracked variable, more cameras |
| 3 | OpenFlexure motorized microscope (~$135–200 DIY), liquid-handling robots later | Many fields of view, autofocus, closed-loop wet lab |

## Cameras Aymen owns (confirmed Oct 27)

### Nuroum V11 webcam (model AW-V11, "QHD Webcam") — the live camera

| Spec (Nuroum datasheet) | Value | What it means for Argus |
| --- | --- | --- |
| Sensor | 1/2.9" CMOS, 4 MP | Fine for desk experiments |
| Modes | **MJPEG up to 1440p @ 30 fps or 1080p @ 60 fps; YUV only up to 360p @ 30 fps** | **Gotcha:** OpenCV must request MJPEG or it falls back to 360p. Set `cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))` *before* setting width/height, then read the size back |
| Focus | **Fixed** (3.0 mm lens) | Good: no autofocus hunting or focus drift. Subjects need to be far enough away to be sharp; find the closest sharp distance on day one (expect roughly 30 cm or more) |
| Field of view | 90° diagonal (82° H, 52° V) | Wide: a row of 4–6 cups fits at desk distance |
| Interface | USB 2.0 Type-C, UVC 1.1/1.5 | Plug and play on Windows |
| WDR | "True WDR" | Can change tone between frames; turn off if the driver or the NearSync app allows, and rely on the card's neutral patch |
| Software | NearSync app (image adjustments, firmware) | Try locking exposure/white balance there if DirectShow properties don't stick |

Use it for: the live dashboard feed, Continuous-mode reactions, the main top-down multi-vessel view.

### Canon XA50 (4K pro camcorder; stand not available right now, so it sits flat on a table) — the precision and long-run camera

| Spec (Canon XA55/XA50 spec page) | What it means for Argus |
| --- | --- |
| 1.0-type CMOS, 15× optical zoom, full manual exposure, white balance and focus | Best image quality and fully lockable settings, which calibration loves |
| Records 4K UHD / Full HD MP4 (up to 150 Mbps) or XF-AVC to SD cards | Long runs can record in-camera, then go through **Import video** |
| **Slow & Fast Motion: fast motion up to ×1200** (Europe page lists 25P/50P; US models use 30P/60P) | **Built-in timelapse.** At ×1200 and 30 fps, one frame is recorded about every 40 s; a 3-day run becomes ~3.6 min of video. Argus needs the **time-scale factor** on import to rebuild real timestamps |
| **Infrared shooting mode + built-in 850 nm IR lamp** (in the handle) | Night frames for plant runs without switching on visible light. Plant phenotyping systems commonly use near-infrared at night because plants respond far less to it than to visible light. Strong "surprise" shot for the demo |
| Minimum focus 10 mm at the wide end (60 cm across the whole zoom range) | Close-ups of seeds, crystals and colonies without a microscope |
| Mini HDMI out (Full HD); timecode is superimposed on HDMI in Camera mode | For a **live** feed: mini-HDMI → HDMI cable + a **USB HDMI capture card** (UVC); it then appears to OpenCV as a webcam. Turn off on-screen displays/timecode for HDMI if the menu allows, otherwise crop |
| USB is Mini-B **PTP only** (file transfer); **no Wi-Fi/LAN streaming; not a USB webcam** | Without a capture card, use it only for recordings |
| AC adapter CA-570 supplied | Run days on AC power, never on battery |

**Roles for the build:**
1. **Today:** record the chosen germination run from the side, camera flat on a table, in fast motion on AC power (`20-demo-experiment-germination.md`).
2. **With a capture card:** second live camera (side view for heights, or zoomed close-up).
3. **Demo:** infrared night clip and high-quality B-roll for the video.

No USB microscope and no smart plug yet (see Q-05, Q-07).

## Camera handling (all cameras)

- **Worker owns each camera** (`cv2.VideoCapture(i, cv2.CAP_DSHOW)`). On Windows a webcam often can't be opened by two programs at once, so the dashboard gets frames from the worker (MJPEG), not from the camera.
- **Phone as camera:** IP-camera apps expose an MJPEG/RTSP URL that `cv2.VideoCapture(url)` reads directly; no extra streaming server needed.
- **Top + side views:** two cameras on one experiment (area from top, height from side).
- **Import video:** MP4 or a folder of photos runs through the same pipeline.

## Smart plug (closed-loop control)

| Option | How | Verdict |
| --- | --- | --- |
| **Shelly Plug (Gen2 and newer)** | Local HTTP RPC, no library: `GET http://<ip>/rpc/Switch.Set?id=0&on=true`, power via `/rpc/Switch.GetStatus?id=0` (`apower` in W) | **Preferred if buying a plug:** ~15 lines of our own code, local, no cloud account. Check whether device authentication is enabled. The Shelly Plus Plug US ($22.99, 1800 W, power metering) is discontinued; Shelly lists the **Plug US Gen4** as its successor. Confirm the Gen4 page lists the same local RPC API before ordering |
| TP-Link Kasa / Tapo | `python-kasa` 0.12.0 (GPL-3.0-or-later, Python ≥3.11). CLI: `kasa --host <ip> on`. Newer firmware and all Tapo plugs need TP-Link account credentials (`KASA_USERNAME`, `KASA_PASSWORD`) | Use only if you already own one. Keep the code in an optional module because of the GPL |

**No plug this hackathon (Q-07 answered no, D-44).** Plug control is on the roadmap; the closed loop in the demo is the Ax next run. The control rules and safety section below still describe the intended design.

## Control rules and safety [decided]

- Rules, not only schedules: "heater off if foam > 50 mm", "lights 16 h on / 8 h off".
- **AI suggests, human approves** (from the phone), unless auto-approve is turned on for that rule.
- **Hard limits the AI cannot override:** max on-time per device, min interval between actions (e.g. never water more than twice a day), dry-run mode, emergency stop.
- Safety check in the wizard blocks automatic control for flame, strong heat, pressure, hazardous chemicals or living pathogens.
- Every action is logged as an **intervention** in the timeline.

## Sensors (later; camera can't see temperature, mass, or pH without an indicator)

| Source | How | Note |
| --- | --- | --- |
| Bluetooth thermometers (e.g. Xiaomi LYWSD03MMC) | **`bleak`** (cross-platform BLE) on Windows | MiTemperature2 is documented for **Linux only** (BlueZ tooling); use bleak on Windows |
| Any Arduino sensor | Serial lines like `temp=24.1 light=530` | Covers pH probes, light sensors, load cells |
| Instrument's own display | Mark the screen as a region; read the number from the frame; keep the frame as proof; flag impossible jumps | Turns existing lab gear into a logged sensor with no wiring |
| Instrument logs | Import CSV/JSON, align on the timeline | |

Sensor readings share the video timeline ("growth slowdown at 03:00 matches a 4 °C drop"). **Cross-checks:** when camera, sensor and log disagree, raise a disagreement note instead of picking one. **Sensor health:** flag stopped or stuck sensors and the measurements that depend on them.

## Alerts

ntfy: `requests.post("https://ntfy.sh/<long-random-topic>", data=msg, headers={"Title": ..., "Priority": ..., "Tags": ..., "Click": url})`. The topic name is effectively the password, so use a long random one stored in `.env`.
