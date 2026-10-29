# Public timelapse datasets of slow-changing lab or kitchen experiments (not seed germination) for an Argus long-run demo

Scope: downloadable timelapse videos or image sequences of slow macro-scale experiments with measurements or published results, ranked by fit for Argus. Argus needs per-vessel segmentation, area/height/count/CIELAB colour in real units, and controls vs treatments with at least 2 replicates per condition filmed side by side by one camera. Research date: 2026-10-29. About 30 search and fetch calls; every licence below was read from the record itself unless marked otherwise.

## Ranked candidate list by fit for Argus (objective)

### Takeaway
The best ready-to-use candidate is the ColTapp *S. aureus* agar-plate timelapse set on figshare: CC BY 4.0, 8 control and 14 rifampicin plates, one frame every 10 min for about 70 h, high resolution with a known pixel scale, and per-plate zips so you can download only 2 + 2 plates. The best one-clip visual is the Kishony MEGA-plate video on Wikimedia Commons: CC BY-SA 3.0, 11.7 days, antibiotic bands. The best colour/CIELAB candidate is the Mendeley "Ripen Banana" set: CC BY 4.0, 4 carbide-treated vs 4 control bananas, every 2 h for 7 days, but shot on a phone. No open dataset found matches Argus's "controls and treatments side by side in one frame" rule perfectly.

### Cited Findings
Ranked list (fit = Argus measurement + treatment/control structure + licence + ease of download):

1. **ColTapp *S. aureus* colony timelapses (Bär et al. 2020, Sci Rep)**. Fits **count** (colony appearance) and **area** (colony size, mm² via the known scale).
   - **Design:** 22 timelapse movies of *S. aureus* JE2 on Columbia sheep blood agar: 8 control plates and 14 rifampicin-treated plates, with 16 to 1509 colonies per plate — [PMC7528005](https://pmc.ncbi.nlm.nih.gov/articles/PMC7528005/)
   - **Timing:** one image every 10 min for about 70 h, which gives 410 or 423 images per series — [PMC7528005](https://pmc.ncbi.nlm.nih.gov/articles/PMC7528005/)
   - **Cameras and scale:** a Canon EOS 1200D shot JPGs at 5184×3456 px, one plate per frame, at about 25 µm/px. A Basler acA5472-17um shot TIFFs at 5472×3648 px, **four plates per frame**, at about 50 µm/px. With a 100 mm macro lens the Canon reached about 5 µm/px — [PMC7528005](https://pmc.ncbi.nlm.nih.gov/articles/PMC7528005/)
   - **Scene:** plates sat upside-up on a black background with lids on, under indirect white light, with the camera perpendicular to the plate, in a 37 °C incubator — [PMC7528005](https://pmc.ncbi.nlm.nih.gov/articles/PMC7528005/)
   - **Data record:** figshare "Data_ColTapp", DOI [10.6084/m9.figshare.12951152.v1](https://doi.org/10.6084/m9.figshare.12951152.v1). Licence **CC BY 4.0**. 25 files totalling about 19.5 GB: CTRL_TL_1–8.zip (about 0.67–0.94 GB each), Rifa_TL_1–14.zip (about 0.71–1.39 GB each), Plate7.zip, Plate8.zip, Mixed_Timelapse.zip and Colony_detection_testing.zip (listed twice) — [figshare API record](https://api.figshare.com/v2/articles/12951152)
   - **Code:** the ColTapp code, standalone executables, demo images and analysis files are on GitHub, and the software is GPL v3. The article itself is CC BY 4.0 — [PMC7528005](https://pmc.ncbi.nlm.nih.gov/articles/PMC7528005/)
   - **What the tool measures:** ColTapp measures colony sizes, growth rates and appearance times from these timelapses, so published per-plate results exist to check against — [PMC7528005](https://pmc.ncbi.nlm.nih.gov/articles/PMC7528005/)
2. **Kishony lab MEGA-plate (bacterial evolution on a giant plate with antibiotic bands)**. Fits **area/colour** (white bacterial coverage advancing per band).
   - **Content:** bacteria grow on a large Petri dish with bands of increasing trimethoprim concentration toward the centre. By day 11, variants with 1000× higher resistance reach the central band — [Wikimedia Commons file](https://commons.wikimedia.org/wiki/File:Kishony_lab-The_Evolution_of_Bacteria_on_a_Mega-Plate.webm)
   - **Timing:** playback is 18000× real time and covers 11.7 days. The video lasts 114.6 s — [Commons API metadata](https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=Mega-Plate%20Kishony&gsrnamespace=6&prop=imageinfo&iiprop=extmetadata|size|url&format=json)
   - **File and licence:** 1280×720 WebM, 7.27 MB. Licence **CC BY-SA 3.0**, artist "Rkishony", Kishony Lab, Harvard Medical School & Technion. A version without music is [MEGA-plate-Kishony-Lab-HMS-Technion-no-music.webm](https://upload.wikimedia.org/wikipedia/commons/f/f8/MEGA-plate-Kishony-Lab-HMS-Technion-no-music.webm) — [Commons API metadata](https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=Mega-Plate%20Kishony&gsrnamespace=6&prop=imageinfo&iiprop=extmetadata|size|url&format=json)
3. **Ripen Banana Dataset (Mendeley Data, DOI 10.17632/j9sp322drp.1)**. Fits **colour** (CIELAB, ΔE yellowing and browning) per banana.
   - **Design:** 8 Sabri bananas, 4 treated with calcium carbide and 4 left to ripen naturally as the control. Photos every 2 h for 7 days, 26 Aug to 2 Sep 2024, with a phone camera of unnamed model — [Mendeley record](https://data.mendeley.com/datasets/j9sp322drp/1)
   - **Images:** 1,404 originals, 1,093 natural and 311 carbide. The carbide set was fully ripe by day 2. Augmented images are also included, and the page's totals for them are internally inconsistent (6,410 vs 9,280) — [Mendeley record](https://data.mendeley.com/datasets/j9sp322drp/1)
   - **Licence and gaps:** **CC BY 4.0**. The page reports no colour or weight measurements and does not say whether the two sets were photographed side by side — [Mendeley record](https://data.mendeley.com/datasets/j9sp322drp/1)
4. **Aberystwyth Leaf Evaluation Dataset (Zenodo 168158)**. Fits **area** (rosette) and **count** (leaves, plants).
   - **Design:** top-down visible-light timelapse of four sets of 20 *Arabidopsis* plants in trays, one image every 15 min from a robotic greenhouse. Plants were periodically harvested for destructive measurements. 56 ground-truth images carry leaf-level annotations covering 916 plants — [Zenodo](https://zenodo.org/records/168158)
   - **Licence:** **CC BY 4.0** — [Zenodo](https://zenodo.org/records/168158)
   - **Files:** 63.7 GB in total. images_and_annotations.zip alone is 61.6 GB. The other files are harvested_plant_data.zip (1.8 GB), software.zip (226.7 MB) and a PDF description (335 kB) — [Zenodo](https://zenodo.org/records/168158)
   - **Not on the page:** treatments, duration, resolution and any in-frame scale — [Zenodo](https://zenodo.org/records/168158)
5. **Yeast colony morphology timelapses (Goldschmidt et al., Dudley Lab / Kutz group)**. Fits **area** and texture per colony.
   - **Design:** 5,500 colonies of 196 *S. cerevisiae* strains on YPD at 30 °C. A median of one frame every 23 min for 3 days, from a Canon 5D Mark II with an MP-E 65 mm macro lens on a 2-axis gantry covering up to 13 plates — [PMC9114130](https://pmc.ncbi.nlm.nih.gov/articles/PMC9114130/)
   - **Image size:** images were downsized to about 100×100 px per colony after preprocessing — [PMC9114130](https://pmc.ncbi.nlm.nih.gov/articles/PMC9114130/)
   - **Data record:** figshare "ImageData" (ProcessedYeastImages.zip, 3.63 GB, plus Example.jpg), licence **CC BY 4.0**. Filenames encode medium, strain, iteration and timestamp in minutes — [figshare API record](https://api.figshare.com/v2/articles/15040353); [figshare page](https://figshare.com/articles/dataset/ImageData/15040353)
6. **Duckweed (*Lemna minor*) 12-well timelapse (Plant Direct 2022)**. Fits **area** (frond area) and **count** (fronds).
   - **Design:** one 12-well plate, one colony per well. Half the wells had 0.5% sucrose and half had none as the control. One frame per location every 60 min for 67 h — [PMC9510441](https://pmc.ncbi.nlm.nih.gov/articles/PMC9510441/)
   - **Imaging:** Zeiss Axio Zoom.V16 macro microscope with an Axiocam 512 colour camera, 4248×2322 px at 4.429 µm/px — [PMC9510441](https://pmc.ncbi.nlm.nih.gov/articles/PMC9510441/)
   - **Availability:** only the supplementary movies S1 and S2 (.mov) and the analysis code (github.com/plantbiojordan/biointernship) are public. No raw-image repository is given. The article is CC BY 4.0 — [PMC9510441](https://pmc.ncbi.nlm.nih.gov/articles/PMC9510441/)
7. **ScanCFU / Scan4CFU (Mendeley Data t7r2vpvn7v)**. Fits **count** and **area**.
   - **Design:** wild-type *E. coli* K12 colonies on multiple nutrient agar plates, imaged by a high-resolution scanner in a temperature-controlled chamber. Licence **CC BY 4.0**. Associated work: Pandey & Phillips, "Scan4CFU" — [Mendeley record](https://data.mendeley.com/datasets/t7r2vpvn7v)
   - **Not on the page:** plate count, interval, duration, conditions and file sizes — [Mendeley record](https://data.mendeley.com/datasets/t7r2vpvn7v)
8. **KOMATSUNA dataset (Kyushu University)**.
   - **Contents:** a multi-view set and an RGB-D set with hand-drawn leaf labels, downloadable as ZIPs. The page does not state a licence — [official page](https://limu.ait.kyushu-u.ac.jp/~agri/komatsuna/)
   - **Timing (secondary source):** five plants every 4 h over 10 days, 1,560 images, RGB-D crops about 166×190 px — [Dataset Ninja](https://datasetninja.com/komatsuna)
9. **Physarum (slime mould) ring-chamber image stacks (Dryad)**. Part 1 is 1.89 TB and holds 47 ring experiments from 16 specimens. Part 2 is 665.8 GB and includes the scripts. Imaging was transmitted light, typically one frame every 46 s — [Dryad Part 1](https://datadryad.org/dataset/doi:10.5061/dryad.2z34tmq08); [Dryad Part 2](https://datadryad.org/dataset/doi:10.5061/dryad.v15dv4291)

### Inferences
- **ColTapp is the closest match to Argus's design.**
  - Each control or treated plate is a "vessel", the scale is known, frames are uniform, and the run is long (70 h, about 420 frames, which renders to a 17 s clip at 25 fps).
  - Download cost is low: CTRL_TL_1 + CTRL_TL_2 + Rifa_TL_1 + Rifa_TL_2 is about 3.1 GB.
  - Main caveat: the Canon series imaged plates one at a time. Controls and treatments are therefore probably not in the same frame, so a 2×2 composite (ffmpeg xstack) would be a montage, not a "same camera, side by side" recording, and the demo should say so.
  - The Basler rig (four plates per frame) is closer to the side-by-side requirement. Which zips came from the Basler is unknown (see Gaps).
  - Argus would use ColTapp's outputs only as a reference for comparison. GPL code must not be pasted into the repo (CLAUDE.md rule 7).
- **The MEGA-plate is the strongest 30-second "wow" clip, but a weak measurement source.**
  - From the published design (Baym et al. 2016, *Science*; from memory, not re-verified this session), the plate is mirror-symmetric, so each non-central concentration band appears twice. That would give built-in duplicate replicates in one frame. Check this on the video before claiming it.
  - The 720p WebM at 18000× gives relatively few frames per day, and recovering mm scale needs the published plate dimensions.
  - CC BY-SA 3.0 means a demo video that includes the clip could count as an adaptation carrying ShareAlike obligations. Attribution is always required.
- **The banana set fits the colour-change recipe structurally** (4 vs 4 replicates, a large ΔE, an obvious treatment effect).
  - Phone capture probably means framing and white balance shift between shots. That is a weak match for Argus's dedicated-camera assumption and needs a frame registration and colour normalisation step.
  - It has no colour or weight ground truth, so the "published result to check against" is only qualitative: carbide-treated bananas were fully ripe by day 2.
- **Aberystwyth has the best ground truth** (destructive harvests plus annotations). But it has no treatments and the image archive is a single 61.6 GB file, which is impractical before Nov 4.
- **The yeast set is CC BY 4.0 and long-running**, but the images are pre-cropped 100×100 px colony thumbnails, not a webcam-like scene of dishes.

### Gaps
- **ColTapp:** which zips (CTRL vs Rifa, Plate7/8, Mixed_Timelapse) were shot on the 4-plate Basler rig, and whether any frame shows control and rifampicin plates together. The figshare HTML page returned 403; only the API metadata was read.
- **ColTapp treatment:** whether "rifampicin-treated" means antibiotic in the agar or cells pre-exposed before plating. Not confirmed; it matters for how Argus phrases the hypothesis.
- **Physical scale:** the Petri dish diameter in ColTapp frames was not confirmed (presumably standard 90 mm).
- **Banana set:** the actual file list and sizes, and whether bananas were photographed together.
- **Aberystwyth:** duration, resolution and whether a scale is in frame (probably in the 335 kB PDF, not read).

## Bacterial/fungal colony growth timelapses on agar plates (ScanLag, AGAR, plate robots; antibiotic vs control)

### Takeaway
There are real, openly licensed agar-plate timelapse sets with treatment vs control. ColTapp (CC BY 4.0, rifampicin vs control, 70 h) is the standout, followed by the MEGA-plate antibiotic-gradient video (CC BY-SA 3.0) and the ScanCFU scanner set (CC BY 4.0, details unverified). No open timelapse dataset of disk-diffusion inhibition zones was found.

### Cited Findings
- **ColTapp:** 22 plate timelapses (8 control, 14 rifampicin) at 10-min intervals for about 70 h, CC BY 4.0 data on figshare, about 19.5 GB as per-plate zips — [PMC7528005](https://pmc.ncbi.nlm.nih.gov/articles/PMC7528005/); [figshare API](https://api.figshare.com/v2/articles/12951152)
- **MEGA-plate:** a trimethoprim band gradient over 11.7 days, 1280×720 WebM, CC BY-SA 3.0 — [Commons](https://commons.wikimedia.org/wiki/File:Kishony_lab-The_Evolution_of_Bacteria_on_a_Mega-Plate.webm)
- **ScanCFU (Mendeley):** CC BY 4.0, *E. coli* K12 on multiple plates in a scanner inside a temperature-controlled chamber, with AutoCAD enclosure designs and MATLAB analysis files — [Mendeley](https://data.mendeley.com/datasets/t7r2vpvn7v)
- **Yeast colony timelapses:** 5,500 colonies, 23-min median interval, 3 days, CC BY 4.0, 3.63 GB — [PMC9114130](https://pmc.ncbi.nlm.nih.gov/articles/PMC9114130/); [figshare API](https://api.figshare.com/v2/articles/15040353)
- **pyphe (Bähler lab):** a Python toolbox for arrayed colony phenotyping, including a timecourse mode. Colony positions are found in the last image and the mask is applied to earlier images to give growth curves. A PyPI page says example data and expected outputs are in the repo's Documentation folder. One listing gives an MIT licence — [GitHub](https://github.com/Bahler-Lab/pyphe); [eLife 55160](https://elifesciences.org/articles/55160); [PyPI](https://pypi.org/project/pyphe)
- **Disk diffusion:** a Dryad dataset of disk-diffusion plates scanned with the SIRscan system has timestamped filenames and measurement tables. Whether it holds repeat timepoints per plate was not confirmed — [Dryad](https://datadryad.org/dataset/doi:10.5061/dryad.5dv41nsfj)
- **4TU.ResearchData** holds CC BY photos of disk-diffusion plates annotated with antibiotic and strain. These are static, not timelapse — [4TU record](https://data.4tu.nl/export/cff/datasets/6836caa1-2c19-4e62-b30a-0c15488dd33a)
- **Laser speckle:** a Frontiers in Microbiology 2023 study tracked inhibition-zone formation over time with laser speckle imaging. No downloadable dataset was found — [Frontiers](https://www.frontiersin.org/journals/microbiology/articles/10.3389/fmicb.2023.1266723/pdf)
- **SciLifeLab figshare:** a record on long-term rifampicin exposure of *E. coli* and *Salmonella* exists. Its contents (plates vs liquid vs microscopy) were not verified — [figshare SciLifeLab](https://figshare.scilifelab.se/articles/dataset/Antibiotic_perseverance_increases_the_risk_of_resistance_development/21517710)

### Inferences
- For an "antibiotic vs control" verdict, ColTapp gives Argus a credible story: count colonies over time per plate, compare appearance-time distributions between conditions with n ≥ 2 plates each, and check against the ColTapp paper's findings.
- The Wikimedia search returned many bacteria movies, but they are microscopy supplements (phase contrast, confocal) from PLOS and Nature Communications papers. They do not fit Argus's macro, webcam-like use.

### Gaps
- **Not verified this session:** ScanLag (Levin-Reisman 2010) raw data availability and the AGAR dataset (NeuroSYS) licence. AGAR is a static colony-counting image set as far as known, not a timelapse.
- **ScanCFU:** the interval, duration, plate count and whether any antibiotic plates exist were not stated on the record page.
- **pyphe:** the Documentation folder's example data was not inspected. It may be only endpoint scans or small grids.

## Plant growth/phenotyping time series with treatments (Arabidopsis, Komatsuna, PhenoArch, drought), Lemna/duckweed

### Takeaway
Open plant image timelapses with ground truth exist (Aberystwyth, CC BY 4.0, 15-min interval, harvest data), but the ones found either have no treatment arm or are huge. Drought vs control data with projected rosette area is open only as tables, not images. The duckweed sucrose vs control timelapse is the cleanest treatment design, but its raw images are not deposited.

### Cited Findings
- **Aberystwyth Leaf Evaluation Dataset:** CC BY 4.0, 4 × 20 Arabidopsis plants in trays, 15-min interval, harvested-plant data and 56 annotated images, 63.7 GB total (61.6 GB image zip) — [Zenodo 168158](https://zenodo.org/records/168158)
- **INRAE Phenoscope (Xue, Loudet et al.):** plants grown under control, mild drought, nitrogen deficiency and combined conditions, imaged daily for 31 days. The open record is a table that includes projected rosette area in cm², with raw physiological data deposited separately — [B2FIND record](https://b2find.eudat.eu/dataset/1cae9e7c-2163-56e9-96cd-4f3e6069357c)
- **Ghent drought data (Clauw et al. 2015, Zenodo):** six accessions, well-watered ("C") vs mild drought ("S"), with projected rosette area (mm²) from 9 to 21 days after sowing. Tabular only — [Zenodo 3371328](https://zenodo.org/record/3371328)
- **Duckweed:** a 12-well plate, sucrose vs no-sucrose halves, 60-min interval, 67 h, 4.429 µm/px. Only the supplementary movies and code are public — [PMC9510441](https://pmc.ncbi.nlm.nih.gov/articles/PMC9510441/)
- **Raspberry Pi phenotyping (Tovar et al. 2018):** twelve top-down Pi cameras over Arabidopsis flats in a 4×5 pot grid, 5-min interval, 8:30 am to 5:30 pm. The page gives no image deposit; the scripts are at github.com/danforthcenter/apps-phenotyping. The authors recommend a size marker and colour standards in frame — [PMC5895192](https://pmc.ncbi.nlm.nih.gov/articles/PMC5895192/)
- **Ginzburg & Rhee:** a Raspberry Pi timelapse drought protocol costing about USD 40, validated in Plant Physiol 2022 (doi 10.1093/plphys/kiac411). No public image set was confirmed — [Bio-protocol e4593](https://bio-protocol.org/e4593)
- **KOMATSUNA:** licence not stated on the official page; five plants every 4 h over 10 days per a secondary catalogue — [official page](https://limu.ait.kyushu-u.ac.jp/~agri/komatsuna/); [Dataset Ninja](https://datasetninja.com/komatsuna); [ICCVW 2017 paper](https://openaccess.thecvf.com/content_ICCV_2017_workshops/w29/html/Uchiyama_An_Easy-To-Setup_3D_ICCV_2017_paper.html)

### Inferences
- The tabular drought datasets (INRAE, Ghent) are useful as published reference numbers for what a drought vs control rosette-area difference looks like. They cannot drive an Argus import, which needs images.
- Aberystwyth trays hold many plants, so SAM per-plant segmentation could treat each pot as a vessel. With no treatment, any "control vs treatment" verdict would be artificial.
- The duckweed design (6 + 6 wells, one plate, sucrose vs control) is ideal for Argus. The supplementary .mov files under the CC BY article could be tried, but they may be single-well movies, not the whole plate (not verified).

### Gaps
- **PhenoArch (INRAE maize platform) image availability and licence:** not researched within the call budget.
- **Arabidopsis background:** the Col-0 accession and PSI PlantScreen at NPPC come from a secondary search snippet and were not verified.
- **Other Lemna sets:** no open Lemna toxicity timelapse with raw images was found. The Deepweed project (NC A&T) is a tool with no confirmed dataset.

## Crystal growth, dough/bread rising, yeast/balloon fermentation, slime mould, fruit ripening/browning, ice melting, evaporation, colour-change reactions

### Takeaway
Apart from fruit ripening (banana sets on Mendeley) and very large microscopy-oriented Physarum archives, no open, measured timelapse datasets were found for these kitchen and chemistry experiments. Dough rise, sourdough, apple browning, crystal growth, iodine clock and ice melt exist only as papers, maker projects or unlicensed videos.

### Cited Findings
- **Ripen Banana:** CC BY 4.0, carbide vs natural, 4 + 4 bananas, every 2 h for 7 days, phone camera — [Mendeley j9sp322drp](https://data.mendeley.com/datasets/j9sp322drp/1)
- **banana_ripening_dataset_day0_to_day7 (v2, April 2026):** about 30 bananas, one image per day for days 0–7 in per-banana folders. No treatment. Licence not verified (search summary only) — [Mendeley d5tczj7fs7](https://data.mendeley.com/datasets/d5tczj7fs7/2)
- **Physarum, other sources:** the Slime Mold Graph Repository holds cropped image subsequences, graph data and tracking scripts — [B2FIND](https://b2find.eudat.eu/dataset/eb294e5e-763b-518d-835f-f7378b563904). Another Dryad Physarum network dataset includes timelapse images for only one sample folder, with others on request — [Dryad 79cnp5j4c](https://datadryad.org/dataset/doi:10.5061/dryad.79cnp5j4c)
- **Dough proofing:** camera-based volume tracking was published (Food Research International 2010, on HAL), but no dataset release was found — [HAL hal-02665363](https://hal.inrae.fr/hal-02665363)
- **Sourdough starter monitors:** Grafana's ultrasonic height logger, Twilio's sourd.io, and Justin Lam's Raspberry Pi camera monitor share code but no public measurement dataset — [Grafana blog](https://grafana.com/blog/2020/06/17/how-to-monitor-a-sourdough-starter-with-grafana/); [Twilio sourd.io](https://www.twilio.com/en-us/blog/sourd-io-is-a-fitness-tracker-for-your-sourdough-starter); [Gigazine on Lam's monitor](https://gigazine.net/news/20180627-sourdough-starter-monitor/)
- **Apple browning:** computer-vision studies exist, but the data is not open. Quevedo et al. 2014 imaged 40 slices over time and its repository entry is restricted — [UC Chile repository](https://repositorio-az.uc.cl/dspace/items/1031f86a-a28b-4298-8674-77641223b05a). Lunadei et al. 2011 (multispectral, CIE L*a*b*, 9 days at 7.5 °C) is under CC BY-NC-ND — [UPM repository](https://oa.upm.es/6423/)
- **Wikimedia Commons:** a search for mold/dough/crystal/bacteria timelapse files returned bacteria microscopy supplements and no mold, dough, crystal, fruit or chemical-reaction timelapses in its first 50 hits — [Commons search API query](https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch=timelapse%20OR%20time-lapse%20mold%20OR%20dough%20OR%20crystal%20OR%20bacteria%20filetype:video&srnamespace=6&srlimit=50&format=json)
- **Mould macro timelapses** promoted online carry no stated licence — [PetaPixel 2020](https://petapixel.com/2020/09/08/this-stunning-supermacro-timelapse-captures-the-hidden-beauty-of-mold)

### Inferences
- For the foam/growth-height and colour-change recipes, no open dataset was found that meets the bar. A short self-filmed run (hours, not days) is more realistic than a found dataset for dough, sourdough or a colour reaction. Banana ripening is the one off-the-shelf colour candidate.

### Gaps
- **Not searched within budget:** Commons categories that the search API did not reach, such as specific "Time-lapse videos" subcategories; Kaggle and Hugging Face for bread, mould or crystal timelapses; iodine-clock or pH-indicator video datasets with absorbance ground truth.

## Microscopy-free macro datasets vs exceptional microscopy ones

### Takeaway
The macro, webcam-like candidates are ColTapp (top-down camera over Petri dishes on a black background), MEGA-plate, the bananas, the Aberystwyth trays and the yeast gantry. Duckweed (macro zoom microscope, reflected light, top view of wells) is borderline. Physarum and the Commons bacteria movies are microscopy, or too large, and are not recommended.

### Cited Findings
- **ColTapp:** standard DSLR or industrial cameras perpendicular to lidded plates, indirect white light — [PMC7528005](https://pmc.ncbi.nlm.nih.gov/articles/PMC7528005/)
- **Duckweed:** imaged on a Zeiss Axio Zoom.V16 macro microscope with 5 mm scale bars in the figures — [PMC9510441](https://pmc.ncbi.nlm.nih.gov/articles/PMC9510441/)
- **Physarum Dryad sets:** transmitted-light imaging at about 46 s intervals, 1.89 TB and 665.8 GB — [Dryad Part 1](https://datadryad.org/dataset/doi:10.5061/dryad.2z34tmq08); [Dryad Part 2](https://datadryad.org/dataset/doi:10.5061/dryad.v15dv4291)

### Inferences
- Of the microscopy sets, only the duckweed 12-well design is "exceptionally good" for Argus (clear treatment/control, known µm/px), and its raw frames are not public.

### Gaps
- Whether a ruler or known-size object is visible in any frame: not confirmed for any dataset. Scale would come from published µm/px (ColTapp, duckweed) or known vessel size (Petri dish, MEGA-plate dimensions).

## GitHub repos that ship sample timelapse data with their analysis tools

### Takeaway
ColTapp (GPL v3) ships demo images on GitHub, and its full data is on figshare. pyphe (Bähler lab) points to example data in its Documentation folder. The yeast-morphology tutorial repo pairs with the CC BY figshare images. Repo code must not be copied into Argus; use only the data, under its own licence.

### Cited Findings
- **ColTapp:** GitHub (github.com/ColTapp) holds source, executables, demo images, Arduino camera-trigger code and analysis files under GPL v3 — [PMC7528005](https://pmc.ncbi.nlm.nih.gov/articles/PMC7528005/)
- **pyphe:** example data and expected outputs are in the Documentation folder — [PyPI](https://pypi.org/project/pyphe); [GitHub](https://github.com/Bahler-Lab/pyphe)
- **Yeast morphology tutorial:** a Jupyter notebook at github.com/pyYeast/yeast-morphology-tutorial — [PMC9114130](https://pmc.ncbi.nlm.nih.gov/articles/PMC9114130/)
- **Duckweed:** analysis code at github.com/plantbiojordan/biointernship — [PMC9510441](https://pmc.ncbi.nlm.nih.gov/articles/PMC9510441/)
- **Danforth Raspberry Pi phenotyping:** scripts at github.com/danforthcenter/apps-phenotyping — [PMC5895192](https://pmc.ncbi.nlm.nih.gov/articles/PMC5895192/)

### Inferences
- ColTapp's GitHub demo images are likely the fastest small download for a smoke test before pulling 3 GB from figshare. Their size and licence terms beyond GPL v3 were not checked.

### Gaps
- The contents and sizes of the demo or example folders in ColTapp, pyphe and the yeast tutorial were not inspected.

## Licences: can each be shown in a public hackathon demo video and linked from a public repo?

### Takeaway
Clear yes with attribution (CC BY 4.0): ColTapp data, yeast ImageData, Aberystwyth, Ripen Banana, ScanCFU. Yes with attribution plus ShareAlike caution (CC BY-SA 3.0): MEGA-plate. Unclear or no licence: KOMATSUNA, banana day0–7 (unverified), duckweed raw images (not deposited), the Tovar and Ginzburg images, mould timelapses on blogs. Not usable for adaptation (CC BY-NC-ND): the Lunadei apple-browning paper.

### Cited Findings
- **CC BY 4.0:**
  - ColTapp figshare — [figshare API](https://api.figshare.com/v2/articles/12951152)
  - Yeast ImageData — [figshare API](https://api.figshare.com/v2/articles/15040353)
  - Aberystwyth; Zenodo notes the licence "allows re-distribution and re-use of a licensed work on the condition that the creator is appropriately credited" — [Zenodo 168158](https://zenodo.org/records/168158)
  - Ripen Banana — [Mendeley](https://data.mendeley.com/datasets/j9sp322drp/1)
  - ScanCFU — [Mendeley](https://data.mendeley.com/datasets/t7r2vpvn7v)
- **CC BY-SA 3.0:** MEGA-plate videos (all three Commons copies), artist Rkishony / Kishony Lab — [Commons API metadata](https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=Mega-Plate%20Kishony&gsrnamespace=6&prop=imageinfo&iiprop=extmetadata|size|url&format=json)
- **No licence stated:** KOMATSUNA official page — [Kyushu page](https://limu.ait.kyushu-u.ac.jp/~agri/komatsuna/)
- **CC BY-NC-ND:** Lunadei et al. 2011 apple-browning paper in the UPM repository — [UPM](https://oa.upm.es/6423/)
- **Code licence:** ColTapp is GPL v3 — [PMC7528005](https://pmc.ncbi.nlm.nih.gov/articles/PMC7528005/)

### Inferences
- **Credit line:** for every CC BY item, the demo video's end card and the repo README need a credit line (creator, title, DOI or URL, licence link, "frames re-encoded/cropped").
- **Keep data out of git:** link the data rather than committing it, because sizes run from 3 to 64 GB and the repo is public. A small attributed excerpt (for example a few downscaled frames) is permissible under CC BY.
- **MEGA-plate ShareAlike:** if MEGA-plate footage is cut into the demo, ShareAlike could require the demo video (as an adaptation) to be offered under CC BY-SA. Showing it unmodified as a separate, credited clip is lower risk. This is a licence-interpretation inference, not legal advice.
- **Dryad:** Dryad datasets (Physarum, SIRscan) are generally CC0 under Dryad's policy, but this was not re-verified on those record pages in this session.

### Gaps
- No licence was read for banana_ripening_dataset_day0_to_day7, the duckweed supplementary movies (presumably under the article's CC BY 4.0, not confirmed), the SIRscan Dryad record or the Physarum Dryad records.
