# Microscopy and life-science datasets and footage for the Argus demo

Scope: openly licensed time-lapse microscopy and organism footage with controls vs treatments, for an Argus re-analysis demo (import a video or image sequence, segment regions with SAM 3.1, measure area, length, count or colour over time, judge a locked hypothesis that needs at least 2 replicates per condition, then suggest the next run with Ax, which needs a numeric factor with 3+ levels). Also covers what could run live at home on a USB microscope. Research date: 29 Oct 2026. About 30 searches and fetches. Anything not confirmed on a primary page is marked as a gap or an inference.

## Which candidates rank best overall for the demo (ranked shortlist)

### Takeaway
The strongest re-analysis demos are: (1) the Konstanz zebrafish-embryo inhibitor time-lapse (TwinNetworkDataset033, CC BY 4.0), with a dose series, untreated controls and 720 frames at 2-min intervals; (2) the Zaritsky wound-healing time-lapse set (data CC0), with 4–6 replicates per condition and a gap that closes on screen; (3) the C. elegans insecticide dose-response videos on Zenodo (CC BY 4.0), with 6 dose levels, 2 control types, 4 wells each and 16 wells per camera, which matches SAM's ~16 tracks. B. subtilis swarming against kanamycin (eLife, CC BY 4.0) is the most dramatic footage, but it has only one video per condition, so Argus cannot give a replicate-based verdict on it.

### Cited Findings

**Rank 1: Zebrafish embryos with BMP/Nodal-pathway inhibitors (TwinNetworkDataset033, Univ. Konstanz, part of the EmbryoNet data family)**
- What is filmed: bright-field time-lapse of zebrafish embryos (from incrosses of TE strains) in multi-well plates, on an Acquifer Imaging Machine. — [B2FIND record, TwinNetworkDataset033](https://b2find.eudat.eu/dataset/c5af9e57-60e2-5e0f-92f6-7b5f92a5ae17)
- Treatment design (by well): LDN-193189 at 4 µM (A3–A6), 3.5 µM (B1–B4) and 12 µM (B5–B6); SB-505124 at 5 µM (C1–C6) and 6 µM (D1–D6); wells A1–A2 had no modulator (controls). — [B2FIND record](https://b2find.eudat.eu/dataset/c5af9e57-60e2-5e0f-92f6-7b5f92a5ae17)
- Duration and interval: 2–2.5 hpf to 26–26.5 hpf, 720 time points at 120 s. — [B2FIND record](https://b2find.eudat.eu/dataset/c5af9e57-60e2-5e0f-92f6-7b5f92a5ae17)
- Format: application/x-tar. Size not stated. Data organised by microscope position and embryo number. µm/px not stated. — [B2FIND record](https://b2find.eudat.eu/dataset/c5af9e57-60e2-5e0f-92f6-7b5f92a5ae17)
- Licence: CC BY 4.0, open access. DOI 10.48606/91, part of 10.48606/50. — [B2FIND record](https://b2find.eudat.eu/dataset/c5af9e57-60e2-5e0f-92f6-7b5f92a5ae17); [DOI](https://doi.org/10.48606/91)
- Sister dataset TwinNetworkDataset032: same kind of experiment, 501 s interval, 2–3 hpf to 27–28 hpf. — [TIB record rdr-doi-10-48606-90](https://service.tib.eu/ldmservice/dataset/rdr-doi-10-48606-90) (seen in a search summary only; not opened)
- Parent EmbryoNet data (Čapek, Kurzbach, Safroshkin et al., 2022, DOI 10.48606/15): bright-field time-lapse of embryos in multiwell plates. Zebrafish training sets are named by pathway (BMP, retinoic acid, Wnt, FGF, Nodal, Shh, PCP). "Severities" sets cover different inhibitor concentrations. There is an untreated WT set (DOI 10.48606/16). Imaging used an Acquifer and a Keyence BZ-X810. Training images carry JSON human annotations. Licence CC BY 4.0. — [KonDATA EmbryoNet overview](https://kondata.uni-konstanz.de/radar/en/dataset/vduFUywzdHVchMaC)
- The EmbryoNet BMP training package is listed at 141.5 GB, CC BY 4.0. Downloads are free with no account fee. — [B2FIND EmbryoNet listing](https://b2find.eudat.eu/dataset/7003eda3-45d6-5106-a5ab-d55f751ded1a) (from a search summary)
- EmbryoNet "Severities – Acquifer" package exists. — [B2FIND Severities](https://b2find.eudat.eu/dataset/69182573-7f23-5db2-8bd9-f5d2174a2bd9)

**Rank 2: In-vitro wound healing, growth factor and inhibitor vs control (Zaritsky et al. 2015, GigaScience)**
- 31 time-lapse wound-healing experiments in two cell lines. DA3 (mouse mammary adenocarcinoma): Control (6 replicates), +HGF/SF (5), PHA665752 Met inhibitor (4), PHA+HGF/SF (6). MDCK: Control (5), +HGF/SF (5). Each experiment has ≥1,000 cells. — [Zaritsky et al. 2015, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4341232/)
- Raw data are on the Cell Image Library (groups 44501 and 45451). Processed monolayer contours, motion fields and MATLAB scripts are in GigaDB 100118 (DOI 10.5524/100118), with code at github.com/gigascience/paper-zaritsky2015. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4341232/)
- Licences: article CC BY 4.0; data CC0 "unless otherwise stated"; code GPL v3. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4341232/)
- Published result: HGF/SF makes cells sparser, faster and more coordinated. No explicit healing rates on the page. Doses, frame interval and pixel size are in Additional file 1/3, which I did not open. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4341232/)
- Sample time-lapse stacks from Zaritsky are also reported on Zenodo (Zabary & Zaritsky 2020): six .tif stacks, single monolayers and two monolayers expanding toward each other. — reported in a search summary drawing on [BBBC019](https://bbbc.broadinstitute.org/bbbc/BBBC019) and related pages; Zenodo URL not confirmed

**Rank 3: C. elegans insecticide/anthelmintic dose-response in 96-well plates (Zenodo, Brown lab)**
- Record "20191212_rr04_sp43_ds08" (DOI 10.5281/zenodo.4673707) supports "Behavioral fingerprints predict insecticide and anthelmintic mode of action" (McDermott-Rouse, Minga, Barlow, Feriani, Harlow, Flemming, Brown). N2 worms on OP50, 2 worms per well, imaged from above, tracked with Tierpsy. — [Zenodo 4673706](https://zenodo.org/record/4673706)
- Doses: SY1099 at 1, 3, 10, 30, 100, 150 µM; SY2333 at 1, 3, 10, 30 µM. Controls: no compound and 0.1% DMSO. Each condition in 4 wells (rows E–H). — [Zenodo 4673706](https://zenodo.org/record/4673706)
- 25 fps, 12.4 µm/px. Files: a 3.8 GB data zip plus a 2.4 kB metadata zip. Licence CC BY 4.0. — [Zenodo 4673706](https://zenodo.org/record/4673706)
- Sibling records from the same April 2021 series (more plates): [4673508](https://zenodo.org/record/4673508), [4677473](https://zenodo.org/record/4677473), [4672019](https://zenodo.org/records/4672019), [4673744](https://zenodo.org/records/4673744). — [search listing](https://zenodo.org/record/4673706)
- The rig (Barlow et al. 2022): six 12-MP cameras (Basler acA4024) per 96-well plate, each video covering 16 wells, 12.4 µm/px, 25 fps. Standard assay is 5 min pre-stimulus, 6 min with three 10-s blue-light pulses and 5 min post (~16 min). Raw footage is ~6.5 TB/hour uncompressed. Videos are in imgstore format. Barlow's own drug screen is on Zenodo DOI 10.5281/zenodo.5121521; the paper states no dataset licence (article CC BY 4.0). — [Barlow et al. 2022, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC8943053/)

**Rank 4: Bacillus subtilis swarm meeting a kanamycin gradient (Grobas et al., eLife 62632)**
- 8 videos: swarm expansion toward a kanamycin disk (the WT halts while waves keep coming from the centre); the Δeps strain under the same setup; jamming at ×60; island formation at ×10; second-layer islands at ×40; multilayer formation near the disk (up to ~4 layers); UV-induced islands; a barrier. — [eLife figures page](https://elifesciences.org/articles/62632/figures)
- Kanamycin disks of 30, 100 and 200 µg; sequential dosing 200–0, 150–50, 100–100, 50–150 µg; MIC for B. subtilis 5 µg/ml. Frame interval not stated. Article CC BY 4.0 "except where otherwise noted". — [eLife figures page](https://elifesciences.org/articles/62632/figures)

**Rank 5: Mitocheck genome-wide RNAi time-lapse (IDR idr0013, also BioImage Archive S-BIAD865)**
- Licence CC0 1.0 per the IDR study page (the CC BY 4.0 footer covers site content). Downloadable as OME-Zarr via BioImage Archive S-BIAD865, Parquet tables per screen, and an annotation CSV on GitHub. — [IDR idr0013](https://idr.openmicroscopy.org/study/idr0013/)
- Design: HeLa cells stably expressing H2B-GFP, seeded on siRNA-spotted slides. Imaging began 18 h after transfection, every 30 min for 48 h. — [mitoODEdata vignette (Bioconductor)](https://bioconductor.statistik.tu-dortmund.de/packages/3.4/data/experiment/vignettes/mitoODEdata/inst/doc/mitoODEdata-introduction.pdf)
- Scale: ~21,000 human genes. screenA has ~191,368 images. — [IDR studies table](https://idr.openmicroscopy.org/about/studies.html); [IDR idr0013](https://idr.openmicroscopy.org/study/idr0013/)

**Rank 6: Scratch-assay ground-truth sets, for validating SAM wound segmentation (not ideal as the main demo)**
- BBBC019v2 "Collective cell migration": 171 images in 8 sets (Init 28, SN15 54, Melanoma 20, TScratch 24, Scatter 6, Microfluidics 13, HEK293 12, MDCK 14). Manual binary PNG masks. Pixel sizes: Init 0.625 µm, SN15 1.24, Microfluidics 0.5, HEK293 2.5, MDCK 0.88/1.24 µm. Zips are 1.5–50.9 MB at data.broadinstitute.org/bbbc/BBBC019/. Licence CC BY 3.0 Unported. — [BBBC019](https://bbbc.broadinstitute.org/BBBC019)
- Scratch-assay segmentation release (EA.hy926 and SKOV-3, brightfield, 5×): 903 images with wound masks; closure analysis on 116 paired observations from 50 acquisition series against a manual reference. Images CC BY 4.0; code MIT; YOLO weights AGPL-3.0. Concept DOI 10.5281/zenodo.20298129; v3.0.0 is 10.5281/zenodo.23453791; the earlier deposit 10.5281/zenodo.20298130 is superseded. — [Hugging Face model card](https://huggingface.co/nmariotto/Scratch-assay-segmentation)
- Caveat: the first version split train and test by image, so frames from the same field leaked across the split. It was later rebuilt by acquisition field, so use the corrected version. — [search summary of the same release](https://huggingface.co/nmariotto/Scratch-assay-segmentation)
- Precedent: a 2024 arXiv paper used SAM with point prompts to segment scratch wounds without domain training. It beat a semi-objective baseline, and its intra- and inter-observer variability was comparable to manual expert segmentation. — [arXiv 2407.02187](https://arxiv.org/abs/2407.02187)

**Rank 7: Physarum polycephalum (slime mould)**
- Wikimedia Commons "Timelapse physarum polycephalum.webm": growth of a plasmodium, 720×720, 20 s, 4.15 MB, author "Tim Tim", 2022. CC BY-SA 4.0. No interval or scale stated. — [Commons file page](https://commons.wikimedia.org/wiki/File:Timelapse_physarum_polycephalum.webm)
- The Commons category holds 11 video or animated files, including two "Australian Physarum polycephalum timelapse" webms (16 s and 13 s), intracellular streaming (39 s) and a hairy-root/Physarum video. Licences are per file. — [Commons category](https://commons.wikimedia.org/wiki/Category:Physarum_polycephalum)
- Dryad ring-confined Physarum (Part 1): 16-bit TIFF stacks, 4–6 s interval, 4–12 h per recording (the abstract says "tens of hours"), at 25 °C in the dark. Agar with nutrients (5 specimens) vs without (11). 47 ring experiments from 16 specimens. 1.89 TB in 13 zips of 53–265 GB. The page does not state an exact licence. Paper: arXiv 2501.02651. — [Dryad Part 1](https://datadryad.org/dataset/doi:10.5061/dryad.2z34tmq08); [Dryad Part 2](https://datadryad.org/dataset/doi:10.5061/dryad.v15dv4291)

**Rank 8: Cell Tracking Challenge 2D+time (no treatments; licence unclear)**
- Examples: Fluo-N2DL-HeLa (H2B-GFP, 30 min, 0.645 µm, 182 MB training zip); PhC-C2DH-U373 (15 min, 0.65 µm, 40 MB); DIC-C2DH-HeLa (10 min, 0.19 µm, 37 MB); BF-C2DL-HSC and BF-C2DL-MuSC (stem cells in hydrogel microwells, 5 min, 0.645 µm, 1.2–1.6 GB); PhC-C2DL-PSC (10 min, 1.6 µm, 124 MB). Direct links on data.celltrackingchallenge.net. The dataset page has no licence or terms, only "© 2012-2024". — [CTC 2D datasets](https://celltrackingchallenge.net/2d-datasets/)
- BBBC mirrors one CTC set (Fluo-N3DH-SIM+) under CC BY, "obtained with permission", and adds that the CTC conditions of use still apply. — [BBBC035](https://bbbc.broadinstitute.org/BBBC035)

### Inferences
- **Zebrafish (Rank 1) best fits Argus's verdict and Ax rules.** Arithmetic from the well map: controls n=2 (exactly Argus's minimum); LDN-193189 has 4 levels including 0 (0, 3.5, 4, 12 µM); n=2–6 per condition. 720 frames played at 30 fps make a 24 s clip of 24 h of development, which is good for a 3-minute video. Embryo area and body-axis length (skeleton) should diverge as BMP inhibition dorsalises embryos. That phenotype is textbook knowledge, not confirmed for this specific dataset, so treat it as a hypothesis for Argus to judge. One embryo or a few per well fits SAM's ~16 tracks if each well is a region. Unknowns: tar size, µm/px (calibrate from the plate or embryo diameter, ~0.7 mm chorion, rather than inventing a value), embryos per well.
- **Wound healing (Rank 2) is the cleanest "area over time" story.** It needs one SAM object per frame (the cell-free gap), or two monolayer fronts, and has strong replicates (4–6). The factors are categorical (±HGF, ±PHA, a 2×2 design in DA3), so Ax has no numeric axis here. Argus could propose an HGF dose series as the next run. Cell Image Library formats and per-image licences need checking before download.
- **C. elegans (Rank 3) gives the best dose-response design and an exact SAM fit** (16 wells per camera = 16 regions). Argus's current metrics (area, length, count, ΔE) do not capture motility, the main readout. Worm length or area per well works, and paralysis at high doses would show as unchanging shape. Showing "wriggling vs paralysed" well by well is visually strong. A frame-difference activity metric would be new Python code (fine under rule 1). The 3.8 GB zip may hold Tierpsy masked videos or features rather than plain video; check before relying on it.
- **B. subtilis/kanamycin (Rank 4) is the most "cool to watch"** (a swarm front stopping at the antibiotic disk, multilayer islands). With one video per condition, Argus should say a verdict can't be given, which is itself a useful honest moment in the demo. The disk doses (30/100/200 µg) form a 3-level numeric factor for an Ax suggestion. Argus must frame this as published-footage re-analysis only, never as a home experiment.
- **Mitocheck (Rank 5) has impeccable licensing (CC0) and scale, but is less cinematic.** It shows hundreds of fluorescent nuclei per frame, about 96 frames per movie (48 h at 30 min, by arithmetic), so Argus would measure total count or coverage rather than tracking objects.
- **Licence ranking for public demo use:** CC0 (Zaritsky data, Mitocheck) > CC BY 4.0 (Konstanz zebrafish, C. elegans Zenodo, eLife videos, scratch-assay Zenodo) > CC BY 3.0 (BBBC019) > CC BY-SA 4.0 (Commons Physarum; share-alike may extend to a demo video that embeds it, so prefer B-roll elsewhere or license the demo compatibly) > unclear (CTC, Cell Image Library per-image, Barlow 5121521) > NC-ND (TIB Dictyostelium films, unusable for remix).

### Gaps
- Not confirmed: TwinNetworkDataset033 tar size, µm/px, embryos per well, and whether frames are single-plane or z-stacks. The RADAR landing page download button was not tested.
- Not confirmed: the Zaritsky frame interval, duration, pixel size and HGF/PHA doses (in additional files not opened), and the Cell Image Library licence per image.
- Not confirmed: whether Zenodo 4673707's zip contains viewable (masked) video or only Tierpsy features/skeletons, and the paper's published dose-response values.
- Not confirmed: Mitocheck control and replicate structure (negative and positive control siRNAs, replicate spots). Check the screenA annotation CSV or Neumann et al. 2010 (Nature 464:721).
- EmbryoNet paper (Nature Methods) details and published accuracies were not retrieved in this session.

## Wound-healing / scratch assays with drug vs control: what is open and how is it licensed?

### Takeaway
Use Zaritsky 2015 (31 time-lapse experiments, 4–6 replicates per condition, data CC0) as the main wound demo, and BBBC019 (CC BY 3.0, masks) or the Zenodo scratch-assay set (CC BY 4.0, masks) to show that SAM wound masks match human ground truth. Several drug-vs-control scratch studies exist, but their raw data are controlled or not deposited.

### Cited Findings
- Zaritsky 2015: DA3 control/HGF/PHA/PHA+HGF and MDCK control/HGF, 4–6 replicates, CIL plus GigaDB, data CC0. — [PMC4341232](https://pmc.ncbi.nlm.nih.gov/articles/PMC4341232/); [GigaScience/Springer](https://link.springer.com/article/10.1186/s13742-015-0049-6)
- BBBC019 includes a TScratch set (24 images) and the multi-well HEK293 and MDCK wound sets, with masks, under CC BY 3.0. — [BBBC019](https://bbbc.broadinstitute.org/BBBC019)
- Zenodo 21031330 "Wound Healing Assay Time-Lapse Series" (MCF-7, HepG2; 32 sequences at 0/24/48/72 h, JPEG) is controlled access, by request to the author. No drug design is described. — [Zenodo 21031330](https://zenodo.org/records/21031330) (via search summary)
- Frequent-sampling scratch study using nocodazole, vinorelbine and Taxol, with controls triplicated in each plate. Raw time-lapse deposit not confirmed. — [Frontiers / PMC7991799](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7991799/)
- Wound Healing Size Tool (ImageJ/Fiji; Suarez-Arnedo et al., PLOS ONE 2020) measures wound area, coverage, average width and width SD. It was tested on HaCaT keratinocytes exposed to conditioned media from adipose-derived MSCs. No sample-image repository was found. — [PMC7386569](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7386569/)
- CSMA, a separate wound-healing tool, has code on GitHub. — [CSMA_WoundHealing](https://github.com/AminaSagymbayeva/CSMA_WoundHealing) (via search result)
- SAM point-prompt segmentation of scratch wounds has been validated against experts. — [arXiv 2407.02187](https://arxiv.org/abs/2407.02187)

### Inferences
- How the demo would look: the phase-contrast monolayer scratch with a dark gap, Argus's SAM mask of the gap shrinking frame by frame, live "wound area (µm²)" curves per replicate, and the HGF curves dropping faster than controls. Verdict: "HGF accelerates closure", supported if it holds across 5–6 replicates. Argus's own Wound-Healing-Size-Tool-style metrics (area, width) can be computed in Python with OpenCV, not by the LLM.
- BBBC019 makes a strong credibility slide: "SAM mask vs human mask, IoU = x". The IoU must be computed, not claimed.

### Gaps
- No open Zenodo/figshare scratch time-lapse with a numeric drug dose series (3+ levels) plus replicates was found. Incucyte-style public dose-response wound data remains unfound.
- I did not open the Zabary & Zaritsky 2020 Zenodo sample stacks, so their URL and licence are unconfirmed.

## Cell Tracking Challenge, BBBC, IDR, Allen Cell, EMBL: which have treatments and permissive licences?

### Takeaway
IDR idr0013 (Mitocheck) is CC0 and has a perturbation design. BBBC019 is CC BY 3.0. The Cell Tracking Challenge has excellent small time-lapse sets but no treatments, and states no licence on its dataset page. Allen Cell and EMBL-specific sets were not verified in this pass.

### Cited Findings
- IDR idr0013: CC0 1.0; two-day live imaging of labelled chromosomes after genome-wide RNAi; OME-Zarr via BioImage Archive S-BIAD865. — [IDR idr0013](https://idr.openmicroscopy.org/study/idr0013/)
- Mitocheck imaging: H2B-GFP HeLa, every 30 min for 48 h, starting 18 h after transfection. — [mitoODEdata vignette](https://bioconductor.statistik.tu-dortmund.de/packages/3.4/data/experiment/vignettes/mitoODEdata/inst/doc/mitoODEdata-introduction.pdf)
- CTC datasets: 10 2D+time sets with time steps and pixel sizes; zips of 37 MB–1.6 GB; no licence text on the page. — [CTC 2D datasets](https://celltrackingchallenge.net/2d-datasets/)
- The CTC 10-year paper is CC BY 4.0 (the article, not necessarily the data). Training and test data are public on the CTC site. — [CTC 10 years, PMC10333123](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10333123/)
- BBBC035 republishes CTC's simulated HL60 set under CC BY "with permission", and says CTC conditions still apply. — [BBBC035](https://bbbc.broadinstitute.org/BBBC035)

### Inferences
- CTC's BF-C2DL-HSC/MuSC (stem cells dividing inside hydrogel microwells, 5-min frames) would look good under "count per microwell over time" with ≤16 microwells as SAM regions. With no treatments, it fits a "watch and measure" segment, not a verdict. Before showing it publicly, email CTC or rely only on BBBC-mirrored sets.

### Gaps
- No verified licence for CTC data, the Allen Cell Explorer time-lapses or other EMBL sets in this session. LIVECell (Sartorius) is believed to be NC-licensed but was not verified here.
- Other IDR time-lapse drug screens beyond idr0013 were not surveyed.

## Organism-level options: zebrafish, C. elegans, Dictyostelium, Physarum, Daphnia, tardigrades, brine shrimp, fungi, yeast, bacterial swarming

### Takeaway
Zebrafish (Konstanz, CC BY 4.0) and C. elegans (Zenodo, CC BY 4.0) are the only organism sets found that pair open licences with real dose series and replicates. Physarum has open footage (Commons CC BY-SA; Dryad nutrient vs no-nutrient, but 1.89 TB). The B. subtilis kanamycin swarm videos are CC BY but unreplicated. Dictyostelium films found were NC-ND or of unclear licence. No open Daphnia, tardigrade, brine-shrimp or fungal time-lapse datasets with treatments were found.

### Cited Findings
- Zebrafish inhibitor time-lapse and EmbryoNet: see Rank 1. — [B2FIND TwinNetwork033](https://b2find.eudat.eu/dataset/c5af9e57-60e2-5e0f-92f6-7b5f92a5ae17); [KonDATA](https://kondata.uni-konstanz.de/radar/en/dataset/vduFUywzdHVchMaC)
- C. elegans dose-response: see Rank 3. — [Zenodo 4673706](https://zenodo.org/record/4673706); [Barlow 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC8943053/)
- Dictyostelium: Bonner's 1940s life-cycle time-lapse is hosted by ASU's Embryo Project (aggregation at ~00:27; a 38 MB service file). Licence not confirmed. — [ASU Embryo Project](https://embryo.asu.edu/pages/slime-mold-development-video-john-tyler-bonner)
- A TIB AV-Portal Dictyostelium discoideum aggregation and sporophore film is CC BY-NC-ND 3.0 DE. Which TIB film this refers to was not confirmed. — [TIB AV-Portal](https://av.tib.eu/media/26439) (via search summary)
- A cAMP-relay live-imaging movie of Dictyostelium aggregation is on EurekAlert. Licence not checked. — [EurekAlert 838267](https://www.eurekalert.org/multimedia/838267)
- Daphnia: heart rate falls from ~320–330/min at 21 °C to ~50/min at 3 °C, and caffeine slowed it by up to ~20%. This is a conference abstract with no raw data. — [Physiological Society abstract](https://www.physoc.org/abstracts/modulation-of-heart-rate-in-the-simple-planktonic-crustacean-daphnia-by-temperature-and-by-caffeine-concentration/). A school protocol exists. — [Practical Biology, Daphnia heart rate](https://practicalbiology.org/control-and-communication/control-of-heart-rate/investigating-factors-affecting-the-heart-rate-of-daphnia)
- Bacterial swarming: B. subtilis with kanamycin (eLife, CC BY). — [eLife 62632 figures](https://elifesciences.org/articles/62632/figures). A Bio-protocol method covers reproducible swarming assays with time-lapse photography. — [Bio-protocol e4162](https://www.bio-protocol.org/e4162). A JoVE flatbed-scanner method records P. aeruginosa swarms under phage and antibiotic stress; it is a pathogen, so footage only. — [JoVE 60915](https://www.jove.com/t/60915)
- Fungi: the HyPhy/SkelPy preprint imaged three Botrytis cinerea isolates over 72 h (180 time-series images). Deposit not confirmed. — [bioRxiv 2025.09.11.675604](https://www.biorxiv.org/content/10.1101/2025.09.11.675604.full.pdf). mycelyso analyses Streptomyces phase-contrast hyphal time-lapses. — [mycelyso, PMC6727546](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6727546/). A Podospora anserina network time-lapse (~20 h from germinating ascospores) was reported. — [APS March Meeting 2024 abstract](https://meetings-archive.aps.org/mar/2024/t36/3)
- Physarum: see Rank 7. — [Commons file](https://commons.wikimedia.org/wiki/File:Timelapse_physarum_polycephalum.webm); [Dryad](https://datadryad.org/dataset/doi:10.5061/dryad.2z34tmq08)

### Inferences
- Skeleton-based length suits worms, zebrafish body axes, Physarum networks and hyphae, so Argus's "length (skeleton)" metric has strong showcase material in Ranks 1, 3 and 7.
- Daphnia heart rate would need a periodic-signal metric (an FFT of a heart-region intensity trace) that Argus does not have yet. Skip it for the hackathon unless that metric is cheap to add.
- Bread or ambient moulds are not ideal for a home demo. Spores are allergenic, and some common moulds (e.g., some Aspergillus species) are opportunistic pathogens. Argus's safety rule argues for sealed dishes only, or avoiding it. This is general knowledge, not sourced here.

### Gaps
- No open tardigrade, brine-shrimp or yeast-colony time-lapse dataset with treatments was found (not searched exhaustively for tardigrades or yeast).
- Licences of the other 10 Commons Physarum files are unchecked.
- The Dryad Physarum licence was not shown on the page. Dryad generally publishes under CC0, but that was not verified in this session.

## Plant microscopy: pollen tubes, root hairs, stomata with treatments

### Takeaway
No open plant time-lapse dataset with treatments was found. Pollen-tube growth vs sucrose concentration is well documented as a protocol and is a natural live home experiment (length metric, numeric factor).

### Cited Findings
- Sucrose concentration shifts the peak oscillatory growth frequencies of Camellia pollen tubes in a microfluidic device (Nezhad, Packirisamy, Bhat, Geitmann, IEEE TBME 2013, DOI 10.1109/TBME.2013.2270914). Data deposit not found. — [DOI](https://doi.org/10.1109/TBME.2013.2270914) (via search summary)
- A Brazilian (FAPESP-funded) project describes >2,000 time-lapses of wild-type Arabidopsis pollen tubes, each up to 1 h (900 datapoints). Availability unknown. — [FAPESP](https://bv.fapesp.br/en/bolsas/226007/URL) (via search summary)
- There is a school protocol for observing pollen-tube growth. — [Practical Biology, pollen tubes](https://practicalbiology.org/cells-to-systems/reproductive-systems/observing-the-growth-of-pollen-tubes)

### Inferences
- Pollen tubes in drops of 0/5/10/15/20% sucrose (a numeric factor with 5 levels, which Ax can use), 3 drops per level, would show measurable tube length within roughly an hour. The duration is general knowledge and should be confirmed in a dry run. The magnification needed (~100× or more) is at the edge of what a cheap USB microscope can resolve.

### Gaps
- Root-hair and stomata time-lapse datasets with treatments (e.g., ABA) were not found in this pass.

## Which could run live on a cheap USB microscope at home, safely, with controls and treatments?

### Takeaway
Best home live options: brine-shrimp hatching vs salinity (object count, a numeric factor with 4–6 levels, results within ~24 h), pollen-tube growth vs sucrose (length, under 1 h), and Physarum on agar with or without oat flakes (area/coverage over hours). All are non-pathogenic and use household or aquarium-shop materials.

### Cited Findings
- Artemia hatching: 66% in brackish water vs 60% in seawater vs 48% in freshwater. — [WAS Asian-Pacific Aquaculture 2019](https://was.org/Meeting/Program/PaperDetail/153262)
- Hatching peaked at 42 h; 15 g/L was recommended. — [UWM undergraduate symposium](https://sites.uwm.edu/undergrad-research-symposium/?p=912)
- Across a 5–40 g/L test, 30 g/L was best. — [Baghdad Science Journal](https://bsj.uobaghdad.edu.iq/index.php/BSJ/article/view/1025)
- Optimum salinity varies by cyst population. — [Oklahoma State](https://scholars.okstate.edu/en/publications/examining-population-specific-hatching-cues-of-salinity-and-light/)
- Pollen-tube protocol. — [Practical Biology](https://practicalbiology.org/cells-to-systems/reproductive-systems/observing-the-growth-of-pollen-tubes)
- Physarum plasmodium growth is visually striking even in amateur time-lapses. — [Commons file](https://commons.wikimedia.org/wiki/File:Timelapse_physarum_polycephalum.webm)

### Inferences
- **Brine shrimp:** cups at 0, 10, 20, 30, 40 g/L salt, 2–3 cups each, a webcam or USB microscope on a shallow dish. Argus counts nauplii per region; swimming objects suit counting by detection better than SAM's 16 tracks, so measure count or coverage per vessel. Hypothesis to lock: "hatching is highest at 20–30 g/L". The sources disagree on the optimum, which makes it a genuine test.
- **Physarum:** buy a plasmodium culture from a biology supplier, then oat flake vs no oat (or 0/1/2/4 flakes, a numeric factor), 2+ dishes each. Area or coverage over 6–24 h, plus a ΔE colour metric (yellow plasmodium on pale agar). Very "cool to watch" on a webcam.
- **Yeast:** baker's yeast in sugar solutions of 0/1/5/10% under a USB microscope (budding counts), or colonies on plates. Safe, but less dramatic, and not sourced here.
- All home options avoid hazardous chemicals and pathogens, in line with Argus safety rule 8.

### Gaps
- No source here measured how resolvable pollen tubes or yeast buds are on a specific cheap USB microscope. A dry run is needed.

## Licences for public demo use, and download practicality

### Takeaway
For the public video and repo, prefer CC0 and CC BY 4.0 sources (Zaritsky, Mitocheck, the Konstanz zebrafish, C. elegans Zenodo, eLife). Avoid committing data to the repo: download at run time and credit in the demo. Watch the CC BY-SA share-alike on Commons, the NC-ND on TIB films, and the missing licences on CTC and the Barlow Zenodo record.

### Cited Findings
- CC0: Zaritsky data — [PMC4341232](https://pmc.ncbi.nlm.nih.gov/articles/PMC4341232/); IDR idr0013 — [IDR](https://idr.openmicroscopy.org/study/idr0013/)
- CC BY 4.0: TwinNetwork033 — [B2FIND](https://b2find.eudat.eu/dataset/c5af9e57-60e2-5e0f-92f6-7b5f92a5ae17); EmbryoNet — [KonDATA](https://kondata.uni-konstanz.de/radar/en/dataset/vduFUywzdHVchMaC); C. elegans — [Zenodo 4673706](https://zenodo.org/record/4673706); scratch-assay images — [HF card](https://huggingface.co/nmariotto/Scratch-assay-segmentation); eLife 62632 — [eLife](https://elifesciences.org/articles/62632/figures)
- CC BY 3.0: BBBC019 — [BBBC019](https://bbbc.broadinstitute.org/BBBC019)
- CC BY-SA 4.0: Commons Physarum time-lapse — [Commons](https://commons.wikimedia.org/wiki/File:Timelapse_physarum_polycephalum.webm)
- NC-ND: TIB Dictyostelium film — [TIB AV-Portal](https://av.tib.eu/media/26439) (via search summary)
- Unclear or none stated: CTC — [CTC](https://celltrackingchallenge.net/2d-datasets/); Barlow Zenodo 5121521 — [PMC8943053](https://pmc.ncbi.nlm.nih.gov/articles/PMC8943053/); Dryad Physarum page — [Dryad](https://datadryad.org/dataset/doi:10.5061/dryad.2z34tmq08)
- Restricted: Zenodo 21031330 wound series (controlled access) — [Zenodo](https://zenodo.org/records/21031330)
- Sizes: BBBC019 zips 1.5–50.9 MB; CTC 37 MB–1.6 GB; C. elegans 3.8 GB per plate record; EmbryoNet BMP 141.5 GB; Dryad Physarum 1.89 TB; Mitocheck screenA ~191k images (per-movie OME-Zarr access). — sources as above

### Inferences
- For practical downloads before 4 Nov: BBBC019 and CTC (minutes), one C. elegans plate (3.8 GB), and selected Zaritsky CIL movies are all feasible. TwinNetwork033 is feasible only if the tar is modest (size unknown). Use the EmbryoNet BMP package (141.5 GB) and Dryad Physarum (TB-scale) only as subsets or not at all.
- The demo should show on-screen attribution (dataset, authors, licence, DOI) and label every imported clip "re-analysis of published data", in keeping with Argus's evidence-separation rule.

### Gaps
- Whether RADAR/KonDATA supports partial or per-file downloads of the Konstanz tars was not checked.
- No registration requirement was found for any source above, apart from controlled-access Zenodo 21031330. RADAR download mechanics are unverified.
