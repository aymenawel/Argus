# Measuring in real units without a printed calibration card (cardless scale, colour and relative fallbacks for Argus)

Scope: methods and open tools for getting mm / mm² (and usable colour) from a single camera or video when there is no ArUco + colour card, including videos found online. Researched 2026-10-29. "Inference" bullets are my reasoning from the cited facts; they are not from the sources.

Abbreviations: δ1 = share of pixels whose predicted depth is within a factor of 1.25 of ground truth (standard depth metric; higher is better). AbsRel = mean absolute relative depth error. mAPE = mean absolute percentage error.

---

## 1. Known-object scale: rulers, petri dishes, coins, cards, paper, glassware

### Takeaway
A known object lying in the same plane as the thing being measured is the only cardless route that reaches about 1% scale error. In-the-wild ruler reading has only recently become reliable (RulerNet: about 1.2–1.5% mean error), and classic tick/FFT methods fail often. A credit card (ID-1, tolerance about 0.1 mm) is a very good reference. A petri dish's nominal "90 mm" hides a 2–3% spread between makers and about a 7% gap between lid and base, so it is a ±2–3% reference unless the exact product is known.

### Cited Findings
**Ruler reading (automatic)**
- RulerNet (Pan, Mehta, Sincerbeaux, Goldstein, Gernand, Wang; arXiv 2507.07077, v1 July 2025, v2 Aug 2026) treats ruler reading as keypoint detection. It fits a geometric progression to the tick spacing so it can model perspective, and it is trained on 102,000 ControlNet-refined synthetic rulers plus rulers rendered on the fly — [arXiv abs](https://arxiv.org/abs/2507.07077); [full text](https://arxiv.org/html/2507.07077)
- Accuracy (mAPE per cm at 768 px, lower is better): RulerNet-DeepGP **1.19 ± 5.03 %** on AnyRuler (1,416 web images) and **1.31 ± 3.15 %** on Rulers2023 (654 test images), at **42 ms/sample** on a V100. The baselines do much worse: "Mark Frequency" (tick-frequency, the classic FFT-style method) scores 62.11 ± 134.41 % and 14.79 ± 25.71 %; "Digits Detection" (OCR) scores 56.71 % and 76.05 % — [RulerNet full text](https://arxiv.org/html/2507.07077)
- RulerNet robustness: blur σ=2 gives 0.27 % median scale error; glare up to 30 % of ruler length gives 0.27 %; 20 % perspective stress gives 0.055 % median. Extreme cases fail: 50 % of marks occluded gives **30.14 % median error**, and blur σ=4 gives 21.59 % at the 95th percentile. The model is not zero-shot on inch-only rulers. The paper names out-of-plane distortion, an object offset from the ruler plane, and curved rulers as error sources or out of scope. In a placenta pipeline (711 images), long-axis MAE was 1.16 ± 1.01 cm against 1.68 ± 4.27 cm for the prior AI-PLAX — [RulerNet full text](https://arxiv.org/html/2507.07077)
- RulerNet code and licence: the project page is github.com/ymp5078/RulerNet, and the paper says "code and data will be publicly released with the paper". No code or weights licence is stated. The paper itself is CC BY-NC-ND 4.0 — [arXiv abs](https://arxiv.org/abs/2507.07077); [RulerNet repo](https://github.com/ymp5078/RulerNet)
- LeafMachine2 (herbarium specimens) computes pixel-to-metric conversion factors for 26 common ruler types. A 2026 BISS conference abstract (Milleville, De Witte, Trekels, Groom, Verstockt, "Determining the Scale of Herbarium Sheet Images via Ruler Detection") reports a ruler-based scale error of **0.794 %** and calls this consistent with LeafMachine2's reported **0.8 %**. It also says existing methods need many annotated samples per ruler type and generalise poorly to unseen rulers. Caveat: I saw these numbers only in a search excerpt of the abstract's XML, not on the landing page or in the LeafMachine2 paper itself — [BISS abstract](https://biss.pensoft.net/article/183602/); [XML](https://biss.pensoft.net/article/183602/download/xml/); [DOI](https://doi.org/10.3897/biss.10.183602)
- Older academic work uses a Hough transform for scale detection on measurement tools. It defines "measurement scale" as the ratio between a unit marked on the tool and the corresponding number of pixels — [arXiv 1602.08574](https://arxiv.org/pdf/1602.08574)
- Several US patents are titled "Automatic ruler detection" (e.g. US 10192137, US 10679094, US 11657644). I did not review their claims or assignee — [US10192137](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10192137); [US10679094](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10679094); [US11657644](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11657644)

**Reference objects (coins, cards, the "pixels per metric" method)**
- The PyImageSearch "pixels per metric" method: pixels_per_metric = object_width_px / known_width. The reference must have known dimensions and be easy to find by position or appearance; the example uses a US quarter (0.955 in) as the left-most object. Stated limits: a non-90° camera angle distorts sizes, and without camera calibration "photos can be prone to radial and tangential lens distortion". The recommended fix is checkerboard calibration — [PyImageSearch](https://pyimagesearch.com/2016/03/28/measuring-size-of-objects-in-an-image-with-opencv/)
- The ISO/IEC 7810 ID-1 format (bank and ID cards) is **85.60 × 53.98 mm**, with tolerances of +0.05/−0.06 mm on length and +0.12/−0.13 mm on width. Corner radius is 2.88–3.48 mm. ISO/IEC 7810:2003 was revised by 7810:2019 — [Wikipedia ISO/IEC 7810](https://en.wikipedia.org/wiki/ISO/IEC_7810)

**Petri dishes as references**
- "90 mm" is nominal. SPL lists its Ø90 dish lid at **92.40 mm** (93.10 mm for grid versions) — [SPL datasheet](https://www.n-genetics.com/files/co/Documents/technicaldata/spl_19477.pdf). A glass 90×15 mm dish lists the lid outer diameter as **90 mm ± 1.0** and the base outer diameter as **84 mm ± 1.0** — [Findel](https://findel-international.com/product/science/biology/microbiology/glass-petri-dish-90x15mm-pack-of-10/e8a77215). Integra uses a lid diameter of about 90.5 mm as its reference — [Integra compatibility list](https://www.integra-biosciences.com/sites/default/files/documents/oi_mj_petri_dish_compatibility_list_v21.pdf). Thermo Fisher Sterilin dishes state only a nominal 90 mm, produced to EN ISO 24998:2008 — [Thermo Fisher](https://www.thermofisher.com/order/catalog/product/90032-17)
- Petri dish detection with Hough and RANSAC has been evaluated in the literature. That paper notes that manual circle detection in images and videos is "long, tedious and imprecise" — [SPIE 11510](https://ebooks.spiedigitallibrary.org/conference-proceedings-of-spie/11510/115101Q/Evaluation-of-the-Hough-and-RANSAC-methods-for-the-detection/10.1117/12.2568818.full). A colony-counting study used Hough circles to find plates but rescaled all photos to 512×512 — [arXiv 2505.20365](https://arxiv.org/pdf/2505.20365). A machine-vision patent computes the conversion scale as a located circle's diameter in pixels divided by its known diameter in mm — [US8321055](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8321055)

### Inferences
- **Ranking for Argus (cardless, user's own rig):** (1) credit card or any ID-1 card: about 0.1–0.2 % object tolerance, a rounded rectangle with aspect 1.586 that is easy to find with contours, quick to add (about 0.5–1 day with a confirm step). Tell users to place it face down for privacy. (2) The existing two-point ruler click, already in Argus and robust. (3) Petri dish auto-scale with `cv2.HoughCircles` or ellipse fitting on SAM masks (about 0.5–1 day), but store uncertainty of **±2–3 %** unless the user names the product or measures the lid once. Ask "lid or base?", because base vs lid is about 7 % (84 vs 90 mm in one product). (4) Automatic ruler reading with RulerNet, only if its code and weights are released under a usable licence. If so, about 1–2 days, but treat it as unverified until tested on Argus footage.
- Classic tick-frequency/FFT ruler reading is not worth building in a few days. In RulerNet's tests it averaged 15–62 % error in the wild.
- Every known-object method measures scale **in the reference's plane**. Measurements are valid only for things in that plane (see question 3 for the height-offset error). The reference size must be stored as part of the measurement record, e.g. `scale_source = "petri_lid_90mm_nominal"` with its uncertainty, to satisfy Argus's evidence rules.
- Coins vary by country, and standard glassware has no tightly specified outer diameter in the sources I found. Neither is a good automatic default; both can be offered as "user-declared reference" with user-entered dimensions.

### Gaps
- No primary source verified for LeafMachine2's own 0.8 % figure (Weaver & Smith 2023); seen only second-hand.
- RulerNet code and weights: release status and licence unknown at time of writing.
- A4 (ISO 216, 210 × 297 mm) and coin diameters were not re-verified in this session. Paper also bends, so it is a poor plane reference.
- EN ISO 24998 dimensional tolerances for plastic petri dishes were not found.
- No published accuracy numbers were found for automatic petri-dish-based scale specifically.

---

## 2. Monocular metric depth models (Depth Pro, Depth Anything V2/V3 metric, UniDepth, Metric3D v2, ZoeDepth): accurate enough for tabletop objects at 20–60 cm?

### Takeaway
No. The published zero-shot numbers are reported as δ1 (within ±25 %), not "within a few %". On the closest proxy for tabletop lab scenes, the Booster dataset (indoor scenes built around reflective and transparent materials), the best metric models get only 27–60 % of pixels within 25 %. Depth Pro itself states it is limited on translucent surfaces. These models can give a rough order-of-magnitude scale for online videos, but must not be presented as measurements. Licences range from permissive (Depth Pro; Depth Anything V2-Small; DA3-Metric-Large reportedly Apache-2.0) to non-commercial (UniDepth; Depth Anything V2 Base/Large).

### Cited Findings
**Accuracy**
- Depth Pro paper, Table 1 (zero-shot δ1 %): **Booster** — Depth Pro 46.6, UniDepth 27.6, Metric3D v2 39.4, Depth Anything v2 59.5 (marked "not strictly zero-shot"), ZoeDepth 21.6. **Sun-RGBD** (indoor) — Depth Pro 89.0, UniDepth 95.8, Metric3D v2 75.6, DA v2 72.4, ZoeDepth 85.7. **Middlebury** — Depth Pro 60.5, UniDepth 31.9, Metric3D v2 29.9, ZoeDepth 53.8. **ETH3D** — Depth Pro 41.5, Metric3D v2 87.7. The paper notes that DA v1/v2 metric variants are domain-specific and that Metric3D uses per-domain crops — [Depth Pro paper](https://arxiv.org/html/2410.02073)
- Booster (Ramirez et al., CVPR 2022): 419 samples in 64 indoor scenes built around reflective and see-through materials, 12 MP main images, sub-pixel ground truth — [CVPR 2022](https://openaccess.thecvf.com/content/CVPR2022/html/Ramirez_Open_Challenges_in_Deep_Stereo_The_Booster_Dataset_CVPR_2022_paper.html)
- Depth Pro states it "is limited in dealing with translucent surfaces and volumetric scattering" — [Depth Pro paper](https://arxiv.org/html/2410.02073)
- Depth Pro focal-length estimation (Table 3): only **64.6–84.2 %** of images have focal error under 25 % across six datasets (e.g. 64.6 % on PPR10K, 84.2 % on RAISE). Even so, it is about twice the next-best method on PPR10K (SPEC 34.6 %) — [Depth Pro paper](https://arxiv.org/html/2410.02073)
- UniDepthV2 README (d1/δ1, zero-shot): NYUv2 98.8, SUN-RGBD 96.4, **IBims-1 94.5**, ETH3D 85.2, KITTI 98.9. The table caption mentions UniDepthV1, so its labelling is ambiguous — [UniDepth repo](https://github.com/lpiccinelli-eth/UniDepth); paper [arXiv 2502.20110](https://arxiv.org/abs/2502.20110)
- Metric3D README: ViT-L KITTI AbsRel 0.044 / δ1 0.985 and NYU AbsRel 0.047 / δ1 0.989; ViT-giant2 NYU AbsRel 0.045. The README says these "rank 1st" on the KITTI/NYU benchmarks, so they may be fine-tuned numbers rather than zero-shot. In-the-wild mode without intrinsics tries 9 default focal lengths, and the FAQ says a wrong focal length distorts the geometry — [Metric3D repo](https://github.com/YvanYin/Metric3D); paper [arXiv 2404.15506](https://arxiv.org/pdf/2404.15506)
- Depth Anything V2 metric models are fine-tuned on synthetic Hypersim (indoor, `max_depth` 20 m) or Virtual KITTI 2 (outdoor, 80 m). Sizes are Small 24.8M, Base 97.5M and Large 335.3M parameters. No accuracy numbers are on the metric_depth page — [DA V2 metric_depth](https://github.com/DepthAnything/Depth-Anything-V2/tree/main/metric_depth)
- Depth Anything 3 metric (DA3METRIC-LARGE) outputs canonical depth. Per the project docs as quoted by mirrors, metric depth = focal × net_output / 300, so **a focal length (in pixels) is required** — [HF mirror DA3METRIC-LARGE](https://huggingface.co/APaul1/DA3METRIC-LARGE); [ComfyUI wiki](https://comfyui-wiki.com/en/models/depth-anything/depth-anything-3)
- A 2025 survey: relative-depth models generalise well but cannot give absolute scale — [arXiv 2501.11841](https://arxiv.org/pdf/2501.11841). A 2025 Princeton paper argues standard depth metrics are weak at detecting curvature and shape errors — [arXiv 2510.19814](https://arxiv.org/pdf/2510.19814)

**Licences (code vs weights)**
- **Depth Pro:** the README says both code and weights are released under the repo LICENSE. That licence is a permissive BSD-style Apple licence ("to use, reproduce, modify and redistribute the Apple Software"; no commercial restriction; keep the notice; no Apple trademarks; no patent grant). Subcomponents listed in ACKNOWLEDGEMENTS carry their own terms — [ml-depth-pro](https://github.com/apple/ml-depth-pro); [LICENSE](https://github.com/apple/ml-depth-pro/blob/main/LICENSE)
- **Depth Anything V2:** "Depth-Anything-V2-Small model is under the Apache-2.0 license. Depth-Anything-V2-Base/Large/Giant models are under the CC-BY-NC-4.0 license." It is supported in Hugging Face Transformers; ONNX is community-only — [DA V2 repo](https://github.com/DepthAnything/Depth-Anything-V2)
- **Depth Anything 3:** DA3METRIC-LARGE is listed as Apache-2.0 on the official HF repo listing and mirrors — [Mixpeek listing of depth-anything/DA3METRIC-LARGE](https://mixpeek.com/model/depth-anything/DA3METRIC-LARGE); [HF mirror](https://huggingface.co/APaul1/DA3METRIC-LARGE). One ONNX conversion tags it bsd-3-clause, which conflicts — [AXERA-TECH README](https://huggingface.co/AXERA-TECH/Depth-Anything-3/blob/main/README.md). DA3NESTED-GIANT-LARGE is CC BY-NC 4.0 — [HF card](https://huggingface.co/depth-anything/DA3NESTED-GIANT-LARGE). ONNX and GGUF community exports exist — [ONNX export](https://huggingface.co/Heliosoph/da3metric-large-onnx)
- **UniDepth:** "released under Creatives Common BY-NC 4.0 license" (non-commercial). Stated requirements are **Linux**, Python 3.10+, CUDA 11.8+ — [UniDepth repo](https://github.com/lpiccinelli-eth/UniDepth)
- **Metric3D:** the code is BSD-2-Clause, but no licence is stated for the weights; commercial-use enquiries go to the authors. ONNX models are available for the v2 models — [Metric3D repo](https://github.com/YvanYin/Metric3D)

**Compute**
- Depth Pro: **504M parameters**, 4,370 GFLOPs, a fixed 1536×1536 internal resolution, 341 ms on a V100-32G. No memory figure is reported — [Depth Pro paper](https://arxiv.org/html/2410.02073). The README says 0.3 s for a 2.25 MP map "on a standard GPU" — [ml-depth-pro](https://github.com/apple/ml-depth-pro)
- Metric3D v2 is 1.378G parameters, 1,299.6 ms at VGA (per the Depth Pro paper's Table 5) — [Depth Pro paper](https://arxiv.org/html/2410.02073)

### Inferences
- δ1 = 94.5 % (UniDepthV2 on iBims-1) still means about 1 pixel in 20 is off by more than 25 %, and δ1 says nothing about a per-image scale bias. A scale bias of 5–15 % is entirely consistent with these scores. Argus's "few %" target is therefore not supported by any published zero-shot number I found.
- Distance matters: 20–60 cm is at the extreme near end of the training ranges (Hypersim rooms up to 20 m; NYU/iBims are room-scale). Lab vessels are also the exact failure class (glass, plastic lids, condensation, liquids) that Booster and Depth Pro's own limitations point to. I would expect worse than the indoor numbers, but that is not measured.
- **Lateral scale cancels the focal estimate:** for in-plane sizes, mm per pixel = Z / f_px. With DA3's sourced formula (Z = f × out / 300), mm/px = out / 300, so focal length drops out and lateral scale is purely the network's learned "canonical" prior. I recall Depth Pro's metric depth is also formed as f_px / (w·C) (Eq. 1 of the paper, not re-verified here), in which case the same cancellation applies. This means focal-estimation accuracy is not the bottleneck; the network's appearance-based size prior is, and that prior is weakest for unfamiliar close-up scenes such as agar and seeds.
- **4 GB GPU / CPU:** Depth Anything V2-Small (24.8M, Apache-2.0) runs easily on CPU via Transformers, but its metric checkpoint is trained on Hypersim rooms. Depth Pro (504M, permissive licence) is roughly 1 GB of weights in fp16 at 1536² internal resolution; whether it fits in 4 GB VRAM is unverified, and CPU inference would likely take seconds to tens of seconds per frame (fine for a one-off scale estimate, not per frame). UniDepth's Linux-only requirement is a problem on the user's Windows machine.
- **Recommended use in Argus (if any):** a one-shot "rough scale" for online videos only, stored as `scale_source = "monocular_depth_estimate"` with a wide uncertainty (on the order of ±25 %, matching δ1's threshold). Show it as "approximate size", never as a measurement used in verdicts. Depth Pro is the most licence-friendly strong option; DA3-Metric-Large is the alternative if its Apache-2.0 status checks out upstream. Effort: about 1 day to wrap one model behind a `scale_estimate()` function. Rule 2 says only `segment()`/`reason()` call models, but this would be a local CV model, not a Meta model; record that decision in the decisions log if adopted.

### Gaps
- No benchmark specifically for 20–60 cm tabletop scenes with metric scale error per image (as opposed to per-pixel δ1) was found.
- ZoeDepth's licence (believed MIT) and MoGe-2 (Microsoft, metric geometry) were not verified in this session.
- No VRAM measurements found for Depth Pro or DA3-Metric-Large; would need a local test.
- Metric3D table may be fine-tuned rather than zero-shot; not resolved.
- Whether the Depth Anything V2 Small *metric* checkpoints inherit Apache-2.0 is not stated on the metric_depth page.

---

## 3. Camera intrinsics (EXIF / known camera) + known distance; vanishing-point / plane-based scale; the vessel's own known size

### Takeaway
Pinhole geometry (mm/px = Z / f_px) works if both the focal length in pixels and the camera-to-plane distance are known. Webcams and online videos rarely give either, and every 1 cm of distance error at 30 cm is about 3 % scale error. Learned focal estimates are only within 25 % for 65–84 % of images. The most practical cardless reference is the vessel itself (dish rim/lid). Its scale applies to the rim plane, so content sitting below the rim needs a height correction.

### Cited Findings
- Depth Pro's single-image focal estimator gets only 64.6–84.2 % of images within 25 % focal error on standard datasets — [Depth Pro paper](https://arxiv.org/html/2410.02073)
- Metric3D needs the correct focal length for correct metric geometry. Without it, it tries 9 default focal lengths, and a wrong focal length distorts point clouds — [Metric3D repo](https://github.com/YvanYin/Metric3D)
- Using a detected circle of known diameter as the scale (px diameter / mm diameter) is an established machine-vision technique — [US8321055](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8321055); [MathWorks answer on converting Hough results to mm](https://www.mathworks.com/matlabcentral/answers/24609)
- PlantCV warns that colour-chip size "can only be used reasonably as a scaling factor" when the reference is on a consistent plane with the subject and parallel to the camera — [PlantCV detect_color_card](https://docs.plantcv.org/en/latest/transform_detect_color_card/)
- PyImageSearch: a non-perpendicular view and uncorrected lens distortion degrade reference-object scale; checkerboard calibration is the fix — [PyImageSearch](https://pyimagesearch.com/2016/03/28/measuring-size-of-objects-in-an-image-with-opencv/)
- Petri dish diameters vary by make (lid 90–92.4 mm) and between lid and base (90 vs 84 mm in one glass product) — [SPL](https://www.n-genetics.com/files/co/Documents/technicaldata/spl_19477.pdf); [Findel](https://findel-international.com/product/science/biology/microbiology/glass-petri-dish-90x15mm-pack-of-10/e8a77215)

### Inferences
- **EXIF route:** f_px = f_mm × image_width_px / sensor_width_mm, then mm/px = Z / f_px. Error is roughly the sum of the relative errors in Z and f. At Z = 30 cm, a tape-measured distance off by ±1 cm gives ±3.3 % scale error, so this is good only for a fixed rig measured once. USB webcams and microscopes have no EXIF, and video platforms strip metadata, so this route is mostly irrelevant to Argus's cameras and online videos. For a fixed rig, calibrating once (checkerboard or ArUco) and then removing the card is better: the scale stays valid as long as the camera and the vessel plane do not move.
- **Height offset in the vessel's own reference:** with a top-down camera at distance Z from the rim plane, content Δh below the rim is imaged at scale (Z+Δh)/Z. For example, agar 8 mm below a lid rim at Z = 300 mm gives about 2.7 % error, rising to about 5 % at Z = 160 mm. Argus should either measure in the rim plane or let the user enter the depth offset. Including the dish tolerance (±1–3 %), "use the dish as the ruler" realistically gives **±3–5 %** total. That is acceptable if Argus stores the uncertainty.
- **Ellipse from tilt:** a tilted circular dish images as an ellipse. Use the major axis for scale, since it is the least foreshortened, and the minor/major ratio gives the tilt as a quality flag (e.g. warn above about 10° tilt). With a SAM mask of the dish, `cv2.fitEllipse` on the contour is a few hours of work.
- **Vanishing points / single-view metrology:** plane-based metrology recovers a planar homography from vanishing lines but still needs **one known length** to fix absolute scale. It adds nothing over the "known object" path for Argus, and it is fragile on tabletop scenes with few straight lines.

### Gaps
- I did not fetch or verify the classic single-view metrology literature (Criminisi, Reid & Zisserman) in this session; the statement above is from general knowledge and should be checked before quoting.
- No published accuracy numbers for "known vessel as ruler" in lab imaging were found.

---

## 4. How plant phenotyping and root tools get scale (PlantCV, RootPainter, RhizoVision Explorer, SmartRoot, ChronoRoot, SeedGerm, Fiji/ImageJ)

### Takeaway
None of the mainstream plant or root tools I could verify auto-detect scale from scene content without a reference. They either take a user-supplied scale (ImageJ Set Scale, RhizoVision's pixel size, scanner DPI), use a fixed imaging rig, or (PlantCV) derive scale from a detected ColorChecker's known chip size, which is the same idea as Argus's card. Reporting in pixel units by default is normal and accepted. The exceptions are specimen-imaging tools that read rulers (LeafMachine2, RulerNet).

### Cited Findings
- **PlantCV** `pcv.transform.detect_color_card(rgb_img, label, color_chip_size, roi, **kwargs)` detects a 4×6 Macbeth-style card. If `color_chip_size` is given (`"classic"` 40×40 mm chips, `"passport"` 12×12, `"mini"` 12×12, `"cameratrax"` 11×11, `"nano"` 3×4, or a custom (w, h) in mm), then "size scalings parameters `pcv.params.unit`, `pcv.params.px_width`, and `pcv.params.px_height` are automatically set". It warns this is reasonable only when the card is on a consistent plane parallel to the camera, and that QR codes are often falsely detected as cards. `auto_correct_color` wraps detection plus affine colour correction — [PlantCV docs](https://docs.plantcv.org/en/latest/transform_detect_color_card/)
- **RhizoVision Explorer** reports lengths, areas and volumes in **pixel units by default**. Physical units need the user-supplied pixel size, per the technical note "Setting the scale for scanner or camera-based imaging platforms" — [Zenodo 7825935](https://zenodo.org/records/7825935); tool overview — [ORNL](https://www.ornl.gov/publication/rhizovision-explorer-open-source-software-root-image-analysis-and-measurement)
- **ImageJ/Fiji Set Scale:** "use the straight line selection tool to make a line selection that corresponds to known distance", then "enter the known distance and unit". "Set Distance in Pixels to zero to revert to pixel measurements". "Global" applies the scale to all images. The Pixel Aspect Ratio option supports anisotropic pixels — [ImageJ docs](https://imagej.net/ij/docs/menus/analyze.html)
- **RootScan** manual: the pixel calibration value converts pixel space to metric space, and users measure two calibration values, one per axis — [RootScan manual](https://plantscience.psu.edu/research/labs/roots/methods/metodologia-de-pesquisa/computer/rootscan/rootscan-users-manual)
- **ChronoRoot** combines 3D-printed open hardware with deep segmentation for high-temporal-resolution root phenotyping on agar plates (a fixed rig) — [bioRxiv 2020](https://www.biorxiv.org/content/10.1101/2020.10.27.350553v1.full-text); ChronoRoot 2.0 — [arXiv 2504.14736](https://arxiv.org/html/2504.14736v1)
- **SeedGerm** (John Innes Centre / Cambridge) is a Raspberry Pi imaging rig with open-source software and ML for germination scoring; its traits include seed size, width and length — [Cambridge SeedGerm](https://www.engbio.cam.ac.uk/seedgerm); [JIC press release](https://jic.ac.uk/press-release/artificial-intelligence-works-out-the-problem-of-seed-germination-tests/)
- **LeafMachine2** (herbarium) computes pixel-to-metric factors from 26 ruler types (see question 1) — [BISS abstract XML](https://biss.pensoft.net/article/183602/download/xml/)

### Inferences
- Argus's ArUco + chip-card design is in line with PlantCV, the best-known open phenotyping library. A good cardless story is "fixed rig, calibrate once, then remove the card", which is exactly how ChronoRoot/SeedGerm-style rigs work.
- Offering pixel units plus an optional user-declared scale is not a lesser mode; RhizoVision and ImageJ default to it. Argus should keep the existing two-point ruler click (the ImageJ "Set Scale" equivalent) and add a "Global" equivalent: one scale per camera session, invalidated if the camera moves (detect this with frame registration).

### Gaps
- RootPainter and SmartRoot scale handling was not verified in this session. I believe RootPainter outputs pixel-based measurements and SmartRoot uses image DPI, but no source was fetched.
- ChronoRoot's exact calibration method (fixed pixel size from the rig vs per-plate detection) was not found.
- SeedGerm's pixel-to-mm conversion was not found; its traits may be reported in pixels.

---

## 5. Colour correction without a colour card; relative colour change (ΔE vs the vessel's own start)

### Takeaway
Card-free white balance (grey-world, white-patch/max-RGB, shades-of-grey, grey-edge) is cheap but unreliable on hard scenes: 95th-percentile angular errors of about 10.6–19° on the standard ColorChecker benchmark. Grey-world is also biased when one colour dominates, as with green seedlings or coloured media. For Argus, the sound cardless approach is relative colour: ΔE00 of the region against its own first frame, normalised per frame by a stable neutral background patch (white paper or bench) and with camera auto-exposure and auto-white-balance locked. The result is reported as relative change, not absolute colour.

### Cited Findings
- UEA illuminant-estimation benchmark, Shi's re-processed ColorChecker (Gehler-Shi) dataset, **95 % quantile** angular errors (recovery / reproduction): Grey World 11.25° / 12.41°; Max-RGB (white patch) 19.01° / 20.05°; Shades of Grey 10.56° / 11.97°; 1st-order Grey Edge 11.33° / 14.56°; 2nd-order Grey Edge 11.01° / 13.66°. The best listed learning method (exemplar-based) scores 6.95° / 8.23° — [UEA illuminant estimation errors](https://colour.cmp.uea.ac.uk/datasets/illuminant-estimation-errors.html)
- A re-analysis of ColorChecker dataset misuse reports that Grey World's median error varies from 9.97° (a 2018 paper) to 3.54° once the black level is subtracted correctly (3.98° on the archived project page). Published colour-constancy numbers are therefore sensitive to preprocessing. Seen via search excerpt — [Hemrit et al., arXiv 1903.04473](https://arxiv.org/pdf/1903.04473)
- `skimage.color.deltaE_ciede2000(lab1, lab2, kL=1, kC=1, kH=1, channel_axis=-1)` computes CIEDE2000 on Lab inputs — [scikit-image docs](https://scikit-image.org/docs/stable/api/skimage.color.html). The `colour` library's `delta_E_CIE2000` notes that the order of reference and sample matters — [colour-science docs](https://colour.readthedocs.io/en/v0.4.0/generated/colour.difference.delta_E_CIE2000.html). An independent validation checks a CIEDE2000 implementation against the Sharma, Wu & Dalal 2004 test data — [SkinOptics validation](https://skinoptics.readthedocs.io/en/latest/_static/validation_Delta_E_00.html)
- PlantCV's card-based path is `detect_color_card` → `std_color_matrix` → `affine_color_correction` (or `auto_correct_color`) — [PlantCV docs](https://docs.plantcv.org/en/latest/transform_detect_color_card/)

### Inferences
- **Grey-world on Argus scenes:** a frame filled with green cotyledons, pink indicator media or amber agar violates the grey-world assumption. The correction would shift as the plants grow, creating fake colour change over time, which is the worst failure for a change detector. Do not use global grey-world for time series.
- **Recommended cardless colour mode (about 0.5 day):** (a) lock exposure, white balance and focus on the webcam, already advisable for any time series. (b) Let the user pick (or SAM-segment) a neutral reference region such as white paper under or behind the vessels, or the bench. (c) Per frame, apply a diagonal (von Kries) gain so that region's mean RGB matches its frame-0 value. This is "white patch" on a known-neutral surface, more robust than the max-RGB used in the benchmark above. (d) Convert to Lab and report ΔE00 against the vessel's own baseline, plus Lab channel trends (e.g. b* for browning or yellowing). (e) Label the result `colour_mode = "relative_to_own_start"`, not absolute colour.
- **Online videos:** auto-exposure, auto-WB and compression vary frame to frame. A background-patch normaliser is the minimum. Also report the background's own ΔE drift as a noise floor: if the "neutral" patch drifts by ΔE 3, a sample ΔE of 2 is not evidence. This fits Argus's existing noise-floor concept.
- An absolute colour claim (e.g. "this is Munsell 5Y 8/6") is not supportable without a card, and Argus should not make one in cardless mode.

### Gaps
- No verified mean/median Gehler-Shi numbers for each simple method from a primary table (only the 95 % quantiles above and one re-analysis excerpt).
- No source found quantifying webcam auto-WB drift or H.264 compression effects on ΔE in time-lapse lab imaging.
- Learning-based single-image colour constancy (FFCC, FC4) was not evaluated for licence or runtime.

---

## 6. Online videos with no reference: is relative measurement (percent change from the first frame, pixel units) a sound fallback, and how do tools phrase it?

### Takeaway
Yes, with conditions. Ratios such as area(t)/area(0) and height(t)/height(0) are scale-free as long as the camera, zoom and object-to-camera distance stay fixed and the change is roughly in a plane facing the camera. Established tools already report pixel units by default and leave conversion to the user. Argus should make "relative (pixel units, % of first frame)" the default for referenceless video. It should detect cuts and zoom changes that break the assumption, and never turn pixels into mm without a declared reference.

### Cited Findings
- RhizoVision Explorer reports lengths, areas and volumes in pixel units by default, with physical units only after the user supplies a pixel size — [Zenodo 7825935](https://zenodo.org/records/7825935)
- ImageJ: "Set Distance in Pixels to zero to revert to pixel measurements", so uncalibrated pixel measurement is a standard mode — [ImageJ docs](https://imagej.net/ij/docs/menus/analyze.html)
- A colony-counting pipeline rescaled every photo to 512×512 px, which breaks any fixed px-to-mm relation; resizing must be tracked — [arXiv 2505.20365](https://arxiv.org/pdf/2505.20365)
- Monocular models cannot give reliable absolute scale for close-range scenes (see question 2), and relative-depth models "cannot provide absolute scale" by design — [arXiv 2501.11841](https://arxiv.org/pdf/2501.11841); [Depth Pro paper](https://arxiv.org/html/2410.02073)

### Inferences
- **Why ratios are sound:** with a fixed camera, the mapping from the object plane to the image is a fixed homography. For a small object near the image centre it is close to a fixed affine map, under which area ratios are preserved exactly. Away from the centre, or with strong perspective, local scale varies across the image. Growth that moves the object toward the camera, such as a seedling rising out of the dish toward an overhead camera, inflates apparent size. Argus should flag "out-of-plane growth" when the main growth direction points toward the camera.
- **Conditions to check automatically (all Python, no model):** (1) shot cuts or editing: a big jump in a frame-difference histogram means splitting into segments. Do not chain ratios across segments without registration. (2) Zoom or camera motion: register each frame to frame 0 against static background (ECC or ORB + RANSAC in OpenCV) and treat a recovered scale factor ≠ 1 ± ~1 % as a zoom/motion event. Then either compensate (divide by the scale²) or stop. (3) Frame resizing or different resolutions in one source. (4) Time-lapse frame timing: online videos often have unknown or uneven capture intervals, so "% per hour" needs user-confirmed timing.
- **Suggested phrasing for Argus records (follows Argus's evidence rule):** "Area: 412 % of first frame (pixel units; no physical reference in video)". "Height increase: +38 px (≈ +X % of initial); absolute size unknown". If the user declares a reference ("the dish is a 90 mm plate"): "≈ 31 mm (scale from user-declared 90 mm dish, ±3–5 %)". The LLM may only interpret these numbers; the ratio and uncertainty are computed in Python (rule 1).
- **Statistics:** percent-change series from a single online video are n = 1 per condition with unknown protocol. The verdict panel should cap claims at "observed in this video", in line with Argus's hypothesis-judging rules.
- **Overall recommendation for Argus in the remaining days (Oct 29 – Nov 4), by value and effort:**
  1. Relative mode for referenceless video, with cut/zoom detection and honest labels: about 0.5–1 day. Highest value, since it unlocks online videos.
  2. Relative colour mode (neutral-patch normalised ΔE00 vs own start): about 0.5 day.
  3. "Vessel as ruler" (petri lid ellipse fit with user-chosen diameter, height-offset input, ±3–5 % stored): about 0.5–1 day.
  4. ID-1 card auto-detect as a pocket alternative to the printed card: about 0.5–1 day.
  5. Optional "rough size" from Depth Pro or DA3-Metric (clearly labelled approximate, ±25 %): about 1 day plus a licence check. Lowest priority. Do not use it in verdicts.
  6. Skip classic FFT ruler reading. Revisit RulerNet only if its code and weights are released under a usable licence.

### Gaps
- No published tool was found that explicitly phrases "percent of first-frame area" for uncalibrated time-lapse video. The phrasing above is a proposal, not a quoted convention.
- No source quantifying how much apparent-area error out-of-plane growth causes in overhead germination imaging.
