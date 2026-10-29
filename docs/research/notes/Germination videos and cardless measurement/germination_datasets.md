# Public seed germination, seedling and root growth timelapse datasets for the Argus demo

Scope: public timelapse image sequences or videos that could stand in for a 3-day germination recording in a hackathon demo video (public repo, due Nov 4, 2026). Argus needs several vessels per frame (or tileable per-vessel sequences), controls vs treatments with 2 or more replicates, real units, and ideally ground truth. Research date: Oct 29, 2026. Metadata marked "file listing" was read directly from the Hugging Face and Mendeley APIs on that date; no dataset files were downloaded.

## Which GitHub repos and open datasets provide germination or root timelapse imagery, and how do they rank for the Argus demo?

### Takeaway
Two sets are usable today with no application process and a clear open license. **ChronoRoot's full time series on Hugging Face** (CC0) has a dedicated `Germination` folder: 32 Arabidopsis plates, about 9.4 GB of timestamped PNGs, roughly 0.04 mm/pixel. The **Genze & Grimm germination dataset on Mendeley Data** (CC BY 4.0, 840 MB) has 247 top-view 85 mm petri dishes of maize, rye and pearl millet, imaged every 30 min for about 48 h, with per-seed "germinated / not germinated" boxes on every frame. The well-known names in the brief (SeedGerm, SPIRO, SPENCER, the licorice NaCl set) have no public image deposit I could find. Commons and journal-supplement clips are only good for B-roll.

### Cited Findings

**Rank 1: ChronoRoot "UnsupervisedRootVideos", `ArabidopsisDataset/Germination` folder (Hugging Face)**
- This dataset holds the complete time series that the ChronoRoot 2.0 annotations were taken from. Raw images are 3280 x 2464 infrared frames, and the license is CC0 1.0 — [HF dataset card](https://huggingface.co/datasets/ngaggion/UnsupervisedRootVideos)
- Top-level folders are `ArabidopsisDataset` (subfolders `Germination`, `Etiolation`, `ManyRoots`, `Roots`) and `TomatoDataset`. Total used storage on the Hub is 227,904,326,500 bytes (about 228 GB) — [HF file listing API](https://huggingface.co/api/datasets/ngaggion/UnsupervisedRootVideos/tree/main/ArabidopsisDataset)
- The `Germination` folder holds 2,839 PNG files (9.40 GB) in 32 leaf folders, one per camera/plate, named like `rpi101_2024-09-06_16-14/1`..`/4` (Raspberry Pi module, start time, camera 1–4). Plates have about 52–95 frames each, and folders run 167–285 MB. Filenames are timestamps (`2024-09-06_16-16-18_1.png`, `2024-09-06_17-01-18_1.png`, `2024-09-06_18-01-18_1.png`), so this release is sampled about hourly — [HF file listing API](https://huggingface.co/api/datasets/ngaggion/UnsupervisedRootVideos/tree/main/ArabidopsisDataset/Germination)
- Hardware: each ChronoRoot module has four fixed-focus Raspberry Pi cameras (Pi NoIR v2) imaging four vertical plates of about 12 x 12 cm. Images are 3280 x 2464 px at about 0.04 mm per pixel, with 15-minute temporal resolution in the paper. Arabidopsis experiments run 10–14 days, tomato 5–7 days, and screening experiments typically 3–5 days — [ChronoRoot 2.0, arXiv](https://arxiv.org/html/2504.14736v2)
- The Screening Interface does "automated tracking for up to 100 seeds/plate" and has a seed germination tutorial — [chronoroot.github.io](https://chronoroot.github.io)
- The paper's demo data includes a "germination screening" video "with hundreds of seeds", an etiolation screening video and a tomato pair. They ship in the Docker/Apptainer images (`/Demo/`) and a Google Drive folder — [ChronoRoot 2.0, arXiv](https://arxiv.org/html/2504.14736v2); [GitHub ChronoRoot2](https://github.com/ChronoRoot/ChronoRoot2); [Drive folder](https://drive.google.com/drive/folders/1PJCn_MMHcM9KPgz8dYe1F2Cvdt43FS3Z?usp=sharing)
- Sister folders in the same CC0 dataset: `Etiolation` has 3,824 PNG (13.29 GB, 28 plates). `ManyRoots` has 2,431 PNG (8.43 GB, 16 plates, e.g. 165 frames per plate). `Roots` has 42,262 files (140.74 GB, 85 folders, including 104 `.gz` files). `TomatoDataset` has 14,760 PNG (51.05 GB, 63 folders) — [HF file listing API](https://huggingface.co/api/datasets/ngaggion/UnsupervisedRootVideos/tree/main)

**Rank 2: Genze & Grimm, "Data for: Accurate Machine Learning-Based Germination Detection…" (Mendeley Data)**
- The dataset covers 824 *Zea mays*, 811 *Secale cereale* and 814 *Pennisetum glaucum* seeds. There are about 10 seeds per dish and 12 dishes per experiment in a 4x3 grid, on **85 mm petri dishes** with black cloth for contrast. A Raspberry Pi Camera v2.1 sits about 40 cm above, facing down, capturing every 30 min for about 2 days. License CC BY 4.0, DOI 10.17632/4wkt6thgp6.3 — [Mendeley Data v3](https://data.mendeley.com/datasets/4wkt6thgp6/3)
- Files: `GermPredDataset.zip` holds images (.jpg) plus PASCAL VOC .xml bounding boxes (839,827,765 bytes). `GermPredRecords.zip` holds TFRecord train/val/test splits, with the test set split by germination experiment (911,471,686 bytes). `GermPredModels.zip` holds model checkpoints (4,773,262,484 bytes, not needed) — [Mendeley public API file listing](https://data.mendeley.com/public-api/datasets/4wkt6thgp6/files?folder_id=root&version=3)
- Paper details: whole-setup captures were cropped to one dish per image (624 x 624 px patches), with 6–12 seeds per dish. There are 82 / 81 / 84 dishes (247 total) and up to 97 images per dish over about 48 h, giving 23,797 images. A seed counts as germinated when a radicle visibly emerges. Labels were drawn in CVAT. No treatments or seed lots are compared, and some series were dropped when dishes dried out — [Genze et al. 2020, Plant Methods (PMC7754596)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7754596/)
- Code: [github.com/grimmlab/GerminationPrediction](https://github.com/grimmlab/GerminationPrediction) (linked from [Mendeley Data v3](https://data.mendeley.com/datasets/4wkt6thgp6/3))

**Rank 3: other ChronoRoot folders (same CC0 dataset): `Etiolation`, `Roots`, `ManyRoots`, `TomatoDataset`**
- The ChronoRoot 2.0 use cases are: Col-0 long-day (16h/8h) vs continuous light (n=23 vs n=21); NF-YA10miRres lines vs Col-0 (n=16 Col-0); etiolation of three genotypes G1–G3 in the dark for 5 days; and tomato wild type vs mutant (n=5 each) — [ChronoRoot 2.0, arXiv](https://arxiv.org/html/2504.14736v2)
- The annotated companion set `ngaggion/ChronoRoot2` holds 913 Arabidopsis and 480 tomato infrared frames. Its six classes are main root, lateral roots, seed, hypocotyl, leaves and petiole, with .nii.gz masks made in ITK-SNAP. License CC0 1.0 — [HF ChronoRoot2 card](https://huggingface.co/datasets/ngaggion/ChronoRoot2). Hub storage is 19,402,169,674 bytes (about 19.4 GB) — [HF API](https://huggingface.co/api/datasets/ngaggion/ChronoRoot2)
- In the original 2021 ChronoRoot study, the photoperiod use case used 12 videos per photoperiod with a frame every 15 min. There were 240 plants across 66 videos in total — [dkNET record citing ChronoRoot 2021](https://dknet.org/data/record/nlx_144509-1/SCR_021259/resolver/pdf&i=rrid:scr_021259); [SINC PDF](https://sinc.unl.edu.ar/sinc-publications/2021/GADLLRCMCBF21/sinc_GADLLRCMCBF21.pdf)

**Rank 4: Aberystwyth Leaf Evaluation Dataset (Zenodo)**
- Visible-light, top-down timelapse of *Arabidopsis* in trays: 4 sets of 20 plants, each tray imaged in a 15-minute timelapse sequence on a PSI PlantScreen. Some plants were periodically harvested for destructive measurement. 56 hand-annotated images cover 916 plants. Files total 63.7 GB (`images_and_annotations.zip` alone is 61.6 GB). License CC BY 4.0 — [Zenodo 168158](https://zenodo.org/records/168158)

**Rank 5: Barley germination time series (RGB + NIR-HSI + NIR spectra)**
- 2,242 malting barley kernels on black filter paper, imaged before moisture exposure and then every 24 h for 5 days. Each kernel is labelled germinated / not germinated at each acquisition, and segmentation masks are included. The arXiv page licenses the article CC BY 4.0, but I did not find a separate dataset URL or license there — [arXiv 2504.16658](https://arxiv.org/abs/2504.16658)

**Rank 6 (B-roll only): openly licensed single-subject timelapse videos on Wikimedia Commons and in journal supplements** (license, resolution, size and duration read from the Commons API)
- `Mung bean germination.ogv`: CC BY-SA 3.0, 1080x810, 17.2 MB, 65 s — [Commons](https://commons.wikimedia.org/wiki/File:Mung_bean_germination.ogv)
- `Lima Bean Time Lapse.webm`: CC BY 3.0, 1280x720, 63.3 MB, 119 s — [Commons](https://commons.wikimedia.org/wiki/File:Lima_Bean_Time_Lapse.webm)
- `Timelapse of lettuce emerging.webm`: CC BY 2.0, 1280x720, 4.8 MB, 19 s (Dwight Sipler) — [Commons](https://commons.wikimedia.org/wiki/File:Timelapse_of_lettuce_emerging.webm)
- `Lentil sprouting Haft-sin time lapse (short).webm`: CC BY 2.0, 3840x2160, 5.8 MB, 94.5 s — [Commons](https://commons.wikimedia.org/wiki/File:Lentil_sprouting_Haft-sin_time_lapse_(short).webm)
- `Germination of two little plants.webm`: CC BY-SA 3.0, 1920x1080, 1.4 MB, 11.5 s — [Commons](https://commons.wikimedia.org/wiki/File:Germination_of_two_little_plants.webm)
- `Pea de-etiolation.ogv`: CC BY-SA 3.0, 1630x2229, 21.7 MB, 92.6 s — [Commons](https://commons.wikimedia.org/wiki/File:Pea_de-etiolation.ogv)
- Brachypodium supplementary videos from Matos et al., PLOS ONE (pone.0100072.s002–s019): CC BY 4.0, 1280x720, about 1–2 MB each, 12–22 s. The paper studies growth rate under daily temperature changes vs the circadian clock, so the videos likely show different temperature regimes (not verified per clip) — [Commons example s002](https://commons.wikimedia.org/wiki/File:Daily-Changes-in-Temperature-Not-the-Circadian-Clock-Regulate-Growth-Rate-in-Brachypodium-distachyon-pone.0100072.s002.ogv)
- Pinus pinaster apex reorientation after inclination (BMC Plant Biology supplement): CC BY 2.0, 640x480, 24 s — [Commons](https://commons.wikimedia.org/wiki/File:Apex_reorientation_in_Pinus_pinaster_during_the_first_24h_after_plant_inclination_-_1471-2229-10-217-S1.ogv)
- Kladnik, "Germination timelapse" on Vimeo: five species over one week, one photo every 5 minutes. No license shown — [Vimeo 30074251](https://vimeo.com/30074251)

**Not usable now: no public images found, or the license or access is unclear**
- **SeedGerm** (Colmer et al. 2020, New Phytologist; John Innes / Earlham / UEA). It covers tomato, pepper, Brassica, barley and maize, with CSV and PNG outputs — [UEA research portal](https://research-portal.uea.ac.uk/en/publications/seedgerm-a-costeffective-phenotyping-platform-for-automated-seed-/). The repo lists no example dataset and no LICENSE file — [GitHub Crop-Phenomics-Group/SeedGerm](https://github.com/Crop-Phenomics-Group/SeedGerm). Note the brief's "Colmenero-Flores" attribution is wrong; the first author is Colmer — [JIC press release](https://jic.ac.uk/press-release/artificial-intelligence-works-out-the-problem-of-seed-germination-tests/)
- **SPIRO** (Ohlsson et al., Plant Journal 2024). A time-lapse robot for up to 4 vertical Petri plates, with germination and root-growth assays — [bioRxiv](https://www.biorxiv.org/content/10.1101/2021.03.15.435343.full.pdf); [GitHub SPIRO](https://github.com/AlyonaMinina/SPIRO). The assays repo is BSD-2-Clause, but it lists no example dataset and no data license — [SPIRO.Assays](https://github.com/jiaxuanleong/SPIRO.Assays)
- **SPENCER robot** (ABA and DOG1 on germination uniformity, bioRxiv 2024). It holds 32 rectangular plates and up to 8,000 Arabidopsis seeds. Its Arabidopsis set has 1,212 images with 2,927 seed and 2,071 radicle objects, and there are Colab segmentation models. I found no public data deposit; the full text was rate-limited (HTTP 429) when I tried to read the data statement — [bioRxiv 2024.05.10.593629](https://www.biorxiv.org/content/10.1101/2024.05.10.593629.full.pdf)
- **Licorice NaCl germination (YOLOv8-licorice, Frontiers 2024)**. This is the closest match to the Argus scenario: 16 NaCl levels from 0–300 mmol/L in 20 mmol/L steps, 20 seeds per plate, a frame every 15 min for 120 h, 5472x3648 JPG, 2,820 raw images, and four state classes. The data statement only says data "will be made available by the authors", with no URL — [Frontiers fpls.2024.1474321](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2024.1474321/full)
- **Julkowska tomato lateral roots under salt (Zenodo 10957050)**. Imaged with SPIRO every 30 min across two genotypes and 4 experiments, but the record contains **only 29 CSV trace files**, not images. CC BY 4.0 — [Zenodo 10957050](https://zenodo.org/records/10957050)
- **Komatsuna** (Kyushu University, 2017). Five plants imaged every 4 h for 10 days, 562 MB. The license is "publicly available" or "other" depending on the source, and is unverified — [Dataset Ninja](https://datasetninja.com/komatsuna); [official page](https://limu.ait.kyushu-u.ac.jp/~agri/komatsuna/)
- **MSU-PID** (Arabidopsis and bean, hourly over a 16 h day, four modalities). No explicit license found — [MSU CV Lab](https://cvlab.cse.msu.edu/project-pid-database.html)
- **RootPainter minirhizotron demo** (100 images from a grassland field experiment, repeated over months). CC BY 4.0 per a university mirror. These are field roots, not lab vessels — [Zenodo 7239095](https://zenodo.org/records/7239095); [Leuphana mirror](https://fis.leuphana.de/de/datasets/minirhizotron-images-for-rootpainter-demo/)
- **Maize germination / vigor RGB dataset** (Chen et al. 2024, Frontiers; IEEE DataPort DOI 10.21227/74fk-an75). Germination recorded hourly; not checked further — [PMC10915039](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10915039/)

### Inferences
- **Ranking rationale.** ChronoRoot `Germination` best matches Argus's "several vessels, real units, CC0, ready-made sequence" needs. One Pi module = 4 plates captured at the same timestamps, so tiling cameras 1–4 of one run into a 2x2 mosaic gives SAM 3.1 four vessels per frame. Genze is second: it has the best ground truth and real 85 mm dishes, but it is per-dish crops at 624 px with no treatments.
- **ChronoRoot frame content.** Plates are vertical and imaged by NoIR cameras under infrared, so frames are effectively greyscale. Argus's colour measurement will not be meaningful on them; area, length, skeleton and count will be.
- **Field of view.** 3280 px x 0.04 mm/px ≈ 131 mm, which matches a 12 cm square plate filling the frame.
- **Argus-like experiment.** No found public dataset combines a salt treatment with replicate dishes, public images and a clear license. The licorice NaCl set would be ideal but requires emailing the authors, which is unrealistic before Nov 4.
- **Commons clips.** These are single-subject and have no replicates. Use them only as cinematic B-roll or an intro shot, not for the verdict.

### Gaps
- I did not open any ChronoRoot `Germination` frame. Seeds per plate, what differs between plates, and whether the 32 plates carry genotype or treatment labels are all unverified; the folder names carry only module, date and camera.
- The license of the ChronoRoot Google Drive demo videos is not stated. The HF datasets are CC0, but the Drive folder has no license text.
- I could not see the Genze image layout inside the zip. The paper says per-dish 624x624 crops, but I did not confirm whether full-frame 4x3 captures are also included.
- The licenses of the SPENCER, SPIRO and SeedGerm data are unknown, and so is whether any images exist publicly.
- I did not check CVPPP/LSC, RootNav 2.0, the "HTPRootSlides" Mendeley set or Kaggle germination sets in this pass. As far as I know CVPPP is rosettes and RootNav is single timepoints, so they are low priority, but this is unverified.

## Which have treatments vs controls with replicates and ground truth to validate Argus's measurements?

### Takeaway
None of the openly downloadable image sets has a salt, osmotic or temperature treatment with replicate dishes and clear ground truth. The closest substitutes are below. Genze & Grimm gives per-seed germination ground truth on about 80 replicate dishes per species, with species as the "condition". ChronoRoot gives genotype and photoperiod comparisons with replicate plates, but the plate-to-condition mapping is not published in the HF folder names.

### Cited Findings
- Genze & Grimm: every image carries a bounding box per seed with class germinated / non-germinated. Each seed is tracked across its time series, so per-seed germination time is derivable. The paper itself reports only aggregate curves and indices. There are 82–84 dishes per species and no treatments or seed-lot contrasts — [PMC7754596](https://pmc.ncbi.nlm.nih.gov/articles/PMC7754596/)
- ChronoRoot 2.0 contrasts: Col-0 long-day vs continuous light (n=23 vs 21); NF-YA10miRres vs Col-0; etiolation of genotypes G1–G3 in the dark for 5 days; tomato WT vs mutant (n=5 each) — [ChronoRoot 2.0, arXiv](https://arxiv.org/html/2504.14736v2)
- ChronoRoot ground truth: 913 Arabidopsis and 480 tomato frames with expert multi-class masks (main root, lateral roots, seed, hypocotyl, leaves, petiole), CC0 — [HF ChronoRoot2](https://huggingface.co/datasets/ngaggion/ChronoRoot2)
- Aberystwyth: harvested-plant ground truth (destructive measurements) plus 56 annotated images, across 4 sets of 20 plants — [Zenodo 168158](https://zenodo.org/records/168158)
- Barley: a per-kernel germinated / not label at every 24 h acquisition, plus masks — [arXiv 2504.16658](https://arxiv.org/abs/2504.16658)
- Treatment datasets that exist but have no public images:
  - Licorice: 16 NaCl concentrations, data "made available by the authors" on request — [Frontiers](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2024.1474321/full)
  - SPENCER: ABA and DOG1, no deposit found — [bioRxiv](https://www.biorxiv.org/content/10.1101/2024.05.10.593629.full.pdf)
  - Julkowska tomato salt: CSV traces only — [Zenodo 10957050](https://zenodo.org/records/10957050)
  - Arabidopsis natural variation in salt-induced root growth phases (125 mM NaCl, root length averaged per hour): image deposit not found — [bioRxiv 2023.01.27.525841](https://www.biorxiv.org/content/10.1101/2023.01.27.525841.full.pdf)
  - Arabidopsis HapMap salt vs control: CSV of root and shoot area only — [Zenodo 7268672](https://zenodo.org/record/7268672)

### Inferences
- **Most honest demo with Genze.** Treat the three species as three "conditions". Pick 3–4 dishes per species from the same experiment and let Argus measure per-dish germination fraction and time to 50% germination. Validate Argus's per-seed germination calls against the VOC boxes; the germinated-box count per frame gives a ground-truth germination curve per dish. This satisfies "at least 2 replicates per condition" and yields a real accuracy number, but the hypothesis must be about species, not salt.
- **With ChronoRoot.** A genotype or photoperiod comparison needs the plate-to-condition key. Without it, Argus can still demo per-plate root length or germination counts, but a treatment verdict would be fabricated framing. The demo must not label plates "0 / 50 / 100 mM NaCl" because that is not what was filmed. This follows Argus's own "never overwrite evidence / no invented claims" rules.
- **If the salt narrative is essential,** the realistic paths are: (a) email the licorice or SPENCER authors, probably too slow before Nov 4; or (b) run a short real experiment in which radicle emergence of cress or radish on wet paper is visible within about 24–36 h at room temperature. That timing is general seed knowledge and was not verified in this research.

### Gaps
- Whether the ChronoRoot `Etiolation` folder's 28 plates map to genotypes G1–G3 with replicates. This is likely given use case 3 but unverified, and the mapping file location is unknown.
- Whether the 104 `.gz` files in ChronoRoot `Roots` are segmentation masks that align with specific time-series frames, which would give root-length ground truth for the exact frames Argus processes. Unverified.
- No per-seed germination-time table is published for Genze; it must be derived from the per-frame boxes.

## Which include a ruler, petri dish of known diameter or calibration target that gives millimetres?

### Takeaway
None of the shortlisted datasets shows a ruler or calibration card in frame. Two give a known-size vessel that Argus can calibrate from: Genze uses 85 mm round dishes, and ChronoRoot uses about 12 x 12 cm square plates with a published scale of about 0.04 mm/pixel. That suits a "cardless" (vessel-as-reference) measurement demo.

### Cited Findings
- Genze & Grimm: 85 mm petri dishes on black cloth, camera about 40 cm above, top-down — [Mendeley Data v3](https://data.mendeley.com/datasets/4wkt6thgp6/3). Crops are 624 x 624 px, one dish per image — [PMC7754596](https://pmc.ncbi.nlm.nih.gov/articles/PMC7754596/)
- ChronoRoot: vertical plates about 12 x 12 cm; 3280 x 2464 px at about 0.04 mm/pixel; calibration is via a "manual calibration tool in the Screening Interface", with no ruler described — [ChronoRoot 2.0, arXiv](https://arxiv.org/html/2504.14736v2)
- SPIRO preprocessing includes "setting scale in cm", method not described — [SPIRO.Assays](https://github.com/jiaxuanleong/SPIRO.Assays)
- Aberystwyth, Komatsuna, MSU-PID and barley pages state no scale — [Zenodo 168158](https://zenodo.org/records/168158); [Dataset Ninja Komatsuna](https://datasetninja.com/komatsuna); [arXiv 2504.16658](https://arxiv.org/abs/2504.16658)

### Inferences
- **Genze scale.** An 85 mm dish spanning most of a 624 px crop implies about 0.13–0.15 mm/px, coarse but adequate for radicle-emergence calls. Seed and radicle lengths will carry about ±0.15 mm per-pixel uncertainty, which Argus's `uncertainties` handling should propagate. This is computed, not measured.
- **ChronoRoot scale.** At about 0.04 mm/px, a 1 mm radicle is about 25 px, good for length. Argus can show its own plate-edge calibration (120 mm across) next to the published 0.04 mm/px as a sanity check, a nice "two independent scales agree" moment.

### Gaps
- I could not confirm the exact visible plate dimensions in ChronoRoot frames (square 120 mm plates vs other sizes per experiment) without opening a frame.
- I did not confirm whether Genze dish crops show the full dish rim, which is needed for diameter-based calibration.

## What licenses apply, and can each be shown in a public hackathon demo video and committed or linked from a public repo?

### Takeaway
CC0 (ChronoRoot on HF) and CC BY 4.0 (Genze on Mendeley, Aberystwyth, Julkowska CSVs, the PLOS Brachypodium videos) are safe to show and to redistribute with attribution. CC BY-SA 3.0 Commons clips carry share-alike obligations. Everything else is unlicensed or unclear and should only be linked, not shown or committed.

### Cited Findings
| Source | License (as stated) | Source |
|---|---|---|
| ChronoRoot UnsupervisedRootVideos (full time series) | CC0 1.0 | [HF card](https://huggingface.co/datasets/ngaggion/UnsupervisedRootVideos) |
| ChronoRoot2 annotated frames | CC0 1.0; paper says "without restrictions" | [HF card](https://huggingface.co/datasets/ngaggion/ChronoRoot2); [arXiv](https://arxiv.org/html/2504.14736v2) |
| ChronoRoot software | GPL-3.0 | [GitHub](https://github.com/ChronoRoot/ChronoRoot2) |
| ChronoRoot Google Drive demo videos | not stated | [chronoroot.github.io](https://chronoroot.github.io) |
| Genze & Grimm germination data | CC BY 4.0 on Mendeley; the article's boilerplate also says data is CC0 "unless otherwise stated" | [Mendeley v3](https://data.mendeley.com/datasets/4wkt6thgp6/3); [PMC7754596](https://pmc.ncbi.nlm.nih.gov/articles/PMC7754596/) |
| Aberystwyth Leaf Evaluation | CC BY 4.0 | [Zenodo 168158](https://zenodo.org/records/168158) |
| Julkowska tomato salt CSVs | CC BY 4.0 | [Zenodo 10957050](https://zenodo.org/records/10957050) |
| RootPainter minirhizotron | CC BY 4.0 (per mirror) | [Leuphana](https://fis.leuphana.de/de/datasets/minirhizotron-images-for-rootpainter-demo/) |
| Barley NIR/RGB time series | article CC BY 4.0; dataset license not found | [arXiv 2504.16658](https://arxiv.org/abs/2504.16658) |
| Commons: Lima bean (CC BY 3.0), lettuce and lentil (CC BY 2.0), Brachypodium PLOS videos (CC BY 4.0), Pinus (CC BY 2.0) | as listed | Commons API (links in the first section) |
| Commons: Mung bean, Pea de-etiolation, "Germination of two little plants" | CC BY-SA 3.0 | Commons API (links in the first section) |
| SPIRO.Assays code | BSD-2-Clause; no data license | [GitHub](https://github.com/jiaxuanleong/SPIRO.Assays) |
| SeedGerm | no LICENSE file in repo | [GitHub](https://github.com/Crop-Phenomics-Group/SeedGerm) |
| Komatsuna | "publicly available" / "other", inconsistent | [Dataset Ninja](https://datasetninja.com/komatsuna) |
| MSU-PID | none found | [MSU CV Lab](https://cvlab.cse.msu.edu/project-pid-database.html) |
| Licorice NaCl set | not public (on request) | [Frontiers](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2024.1474321/full) |
| Kladnik Vimeo | none shown | [Vimeo](https://vimeo.com/30074251) |
| Roboflow "Seed Germination" set | not checked; not linked to SeedGerm | [Roboflow](https://universe.roboflow.com/workspace-epph6/seed-germination-pfzr6) |

- The Mendeley v3 page asks users to cite the Plant Methods paper (doi 10.1186/s13007-020-00699-x) — [Mendeley v3](https://data.mendeley.com/datasets/4wkt6thgp6/3)
- The ChronoRoot HF card asks users to cite ChronoRoot 2.0 (GigaScience 2026, doi 10.1093/gigascience/giag018) and the original 2021 paper — [HF card](https://huggingface.co/datasets/ngaggion/UnsupervisedRootVideos)

### Inferences
- **CC0 (ChronoRoot).** Free to show in the demo video and to commit a small subset (for example one 4-plate run, downsampled) to the public repo. Credit Gaggion et al. anyway as good practice.
- **CC BY 4.0 (Genze, Aberystwyth, PLOS videos).** Allowed in the video and the repo with an attribution line (authors, title, DOI, license link, and a note of changes such as cropping, tiling or re-encoding). Put this in the README or a `data/ATTRIBUTION.md`, and add an on-screen credit in the video.
- **CC BY-SA 3.0 Commons clips.** Usable, but an edited video that adapts them arguably must be released under BY-SA. Prefer the CC BY lima bean or lettuce clips for B-roll.
- **Unlicensed or unclear sources** (ChronoRoot Drive demo videos, SeedGerm, MSU-PID, Komatsuna, Vimeo). Do not commit, and do not show without permission; link only.
- **Repo size.** Mendeley and HF archives should be fetched by script rather than committed; GitHub warns at 50 MB per file and blocks files over 100 MB (general GitHub knowledge, not verified here).

### Gaps
- The precise attribution string preferred by Genze & Grimm and by Gaggion et al. beyond "cite the paper".
- Whether the BMC "CC0 unless otherwise stated" boilerplate or the Mendeley CC BY 4.0 governs the Genze data. Treating it as CC BY 4.0 is the conservative choice.

## How large are they and how quickly could they be downloaded and turned into a video (frame rate, ordering)?

### Takeaway
A demo-sized slice is small and quick. One ChronoRoot 4-plate germination run is about 0.7–1.1 GB of timestamp-named PNGs, downloadable by path pattern from Hugging Face. The whole Genze image set is one 840 MB zip with a direct Mendeley link. Both become a 5–15 s video at 10–24 fps with ffmpeg after a filename sort.

### Cited Findings
- ChronoRoot `Germination`: 9.40 GB for all 32 plates. Example run `rpi101_2024-09-06_16-14` has 4 cameras x 67 frames, about 233–238 MB per camera, so about 0.94 GB for the run. Run `rpi12_2024-07-08_15-50` camera 1 has 95 frames (285 MB). Average PNG size is about 3.3 MB. Filenames follow `YYYY-MM-DD_HH-MM-SS_<cam>.png` — [HF file listing API](https://huggingface.co/api/datasets/ngaggion/UnsupervisedRootVideos/tree/main/ArabidopsisDataset/Germination)
- Whole UnsupervisedRootVideos repo: about 228 GB (do not clone it whole) — [HF API](https://huggingface.co/api/datasets/ngaggion/UnsupervisedRootVideos)
- Genze: `GermPredDataset.zip` is 839,827,765 bytes and has a direct public download URL (`https://data.mendeley.com/public-files/datasets/4wkt6thgp6/files/4ab46f9f-b34f-4112-a4be-0f3d6c459cf4/file_downloaded`) with no login. There are 23,797 images, at most 97 per dish, at 30-minute intervals — [Mendeley public API](https://data.mendeley.com/public-api/datasets/4wkt6thgp6/files?folder_id=root&version=3); [PMC7754596](https://pmc.ncbi.nlm.nih.gov/articles/PMC7754596/)
- Aberystwyth: a single 61.6 GB images zip, impractical for this timeline — [Zenodo 168158](https://zenodo.org/records/168158)
- Commons clips are 1–63 MB ready-made video files — Commons API (links in the first section)

### Inferences
- **ChronoRoot download recipe.** `huggingface-cli download ngaggion/UnsupervisedRootVideos --repo-type dataset --include "ArabidopsisDataset/Germination/rpi101_2024-09-06_16-14/*" --local-dir data/chronoroot` (standard `huggingface_hub` include-pattern usage). Then:
  - Lexicographic sort of filenames equals chronological order.
  - For a 2x2 vessel mosaic, align cameras by nearest timestamp; the four cameras of one module fire about 23 s apart.
  - 67 frames at 12 fps gives about a 5.6 s clip. Use `ffmpeg -framerate 12 -i` over a concat list, because ffmpeg's `-pattern_type glob` is not available in typical Windows builds.
  - Argus's importer should take real timestamps from the filenames rather than assuming a fixed interval; intervals are about 1 h in this release and some runs start with a 45 min gap.
- **Genze recipe.** Download the 840 MB zip and group images by dish ID (from file or XML naming, unverified). Tile 3 species x 3–4 dishes into a grid at 30-min steps; 97 frames at 12 fps gives about 8 s. The XML boxes give a per-frame germinated count to overlay as ground truth.
- **Time budget.** On a typical 50–100 Mbit/s connection, each set downloads in about 2–3 min; conversion is seconds. Both fit inside the remaining 6 days.

### Gaps
- Internal filename / dish-ID scheme inside `GermPredDataset.zip` (needed for grouping frames per dish) — not inspected.
- Exact capture interval in each ChronoRoot germination run (some appear to begin with a 45-min step, then hourly) — inferred from three sample filenames only.
