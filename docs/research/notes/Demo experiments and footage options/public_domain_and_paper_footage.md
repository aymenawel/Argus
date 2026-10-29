# Public-domain and openly licensed institutional footage of controlled experiments for the Argus demo

Scope: footage or image sequences (any field) that show controls vs treatments, ideally with replicates, that Argus could import as a labelled re-analysis for the 3-minute demo (due Nov 4, 2026). Research date: Oct 29, 2026. Nothing was downloaded; all details below come from catalogue pages, API metadata and article pages.

## Q1. NASA and ESA: ISS plant, crystal, fluid and flame experiments. What is downloadable, and which have flight vs ground-control comparisons?

### Takeaway
NASA has downloadable public-domain material on ISS plant experiments, but no time-lapse found here puts the control and the treatment in one frame. The best NASA finds are: (a) a 1080p public-domain time-lapse of Plant Habitat-04 chile peppers (striking, but flight only, no control in the video); (b) Plant Habitat-07 ground-unit lettuce stills that show control, flood, drought and wilt moisture treatments side by side on days 7, 14 and 28 (6000x4000 px, but the creator is Techshot and the file metadata carries a copyright, so these are not clearly public domain); (c) PH-02 radish ground-control harvest photos and video. ESA material is CC BY-SA 3.0 IGO only where a page says so. No ESA time-lapse with a ground reference was found.

### Cited Findings
**NASA usage terms**
- NASA images, audio and video "generally are not subject to copyright in the United States". NASA "should be acknowledged as the source of the material". The NASA insignia, logotype and identifiers "are not in the public domain". Commercial use must not imply NASA endorsement. For commercial use, permission should be obtained from identifiable people, and currently employed astronauts' names or likenesses cannot be used commercially. Third-party copyrighted material needs the holder's permission. The page has no specific guidance on ESA or JAXA partner imagery. — [NASA Brand Center: images and media guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/)

**Plant Habitat-04 (PH-04) chile peppers time-lapse (flight only, public domain)**
- images.nasa.gov has two time-lapse videos dated 2022-04-25 (KSC): "Expedition 66 Crew Grows Chile Peppers on the International Space Station Time-lapse" (nasa_id `Peppers Timelapse Longe Rev 7`) and a short version (`Peppers Timelapse Salsa Music Rev 4`). The peppers began growing on July 12, 2021. The descriptions do not mention a ground control. — [images-api search "time-lapse plants"](https://images-api.nasa.gov/search?q=time-lapse%20plants&media_type=video)
- Long version: 59 s, 1920x1080, 30 fps, 135 MiB. Secondary creator "NASA/Francisco Martin". — [asset metadata.json](https://images-assets.nasa.gov/video/Peppers%20Timelapse%20Longe%20Rev%207/metadata.json)
- The asset manifest lists `~orig.mp4`, `~large.mp4`, `~medium.mp4`, `~mobile.mp4`, `~small.mp4`, `~preview.mp4`, plus an `.srt` caption file, `metadata.json` and keyframe JPGs. All are direct file URLs under `images-assets.nasa.gov/video/Peppers Timelapse Longe Rev 7/`. — [images-api asset manifest](https://images-api.nasa.gov/asset/Peppers%20Timelapse%20Longe%20Rev%207)
- A separate NASA video, "Space is Spicier: Peppers Growing on Station" (KSC-20210713-VP-MWC01-001-PEPPERS-3277958, 2021-07-13), describes a ground-control pepper run at Kennedy alongside the ISS crop. — [images-api search "plant habitat ground control"](https://images-api.nasa.gov/search?q=plant%20habitat%20ground%20control&media_type=image,video)

**Plant Habitat-07 (PH-07) romaine lettuce moisture treatments (side by side, but third-party images)**
- PH-07 studies how optimal and suboptimal moisture affects growth, nutrient content and the plant microbiome. — [images-api search "PH-07"](https://images-api.nasa.gov/search?q=PH-07&media_type=image,video)
- Four ground-experiment stills from JSC, credited "TECHSHOT, INC.", all from the same search:
  - jsc2025e047407 (2024-02-06): day 7 seedlings after thinning.
  - jsc2025e047408 (2024-02-13): day 14, with dividers separating the canopies and microbiomes of plants under different moisture treatments.
  - jsc2025e047409 (2024-02-27): "control (left) and flood (right) moisture treatments" before the day-28 harvest.
  - jsc2025e047410 (2024-02-27): "drought (left) and wilt (right)" treatments mid-harvest on day 28.
  - Source: [images-api search "PH-07"](https://images-api.nasa.gov/search?q=PH-07&media_type=image,video)
- jsc2025e047409 is 6000x4000 px (2.7 MiB). Its embedded metadata gives creator "TECHSHOT, INC." and "Copyright: 2021", and the description says the image is courtesy of the PH-07 Team. — [jsc2025e047409 metadata.json](https://images-assets.nasa.gov/image/jsc2025e047409/metadata.json)
- NASA-created PH-07 material: ground-control harvest stills at KSC on 2025-04-24 (NASA/Kim Shiflett), a harvest video (NASA/Glenn Benson), and preflight-harvest stills and video from 2024-08-29 (NASA/Ben Smegelsky; NASA/Frank Michaux). — [images-api search "PH-07"](https://images-api.nasa.gov/search?q=PH-07&media_type=image,video)

**Plant Habitat-02 (PH-02) radishes (ground control vs flight, separate stills)**
- Twelve stills from 2020-12-14 (KSC-20201214-PH-KLS01_00xx, NASA/Kim Shiflett) show radishes in the APH ground unit as the ground control for PH-02, plus researchers measuring the harvested ground radishes. There is also a ground-harvest video (KSC-20201214-MH-GEB01_0001, NASA/Glenn Benson). None of these is a time-lapse. — [images-api search "plant habitat ground control"](https://images-api.nasa.gov/search?q=plant%20habitat%20ground%20control&media_type=image,video)
- Astronaut Kate Rubins harvested the flight crop on Nov. 30, 2020; scientists planned to compare the ground and space plants. No NASA image pairing the two side by side was found. — [NASA Kennedy blog, Dec 15 2020](https://blogs.nasa.gov/kennedy/2020/12/15/kennedy-harvests-radish-crop-as-part-of-ph-02-experiment); [NASA feature](https://www.nasa.gov/feature/astronauts-harvest-radish-crop-on-international-space-station)
- Commercial stock sites (e.g. SuperStock) resell the same ground-unit images under commercial terms. Use NASA's originals instead. — [SuperStock listing](https://www.superstock.com/asset/view-radishes-growing-advanced-plant-habitat-aph-ground-unit-inside/6145-45285453)

**Veggie VEG-05 dwarf tomatoes (two light treatments plus ground control; no time-lapse found)**
- One Veggie unit used equal red and blue light, the other a 90:10 red:blue ratio, both with about 10% green. Flight ran Dec 2022 – Mar 2023, with fruit harvests at days 83, 90 and 100. The first ground control was short of plants, so it was restarted in Feb 2023 and ran through May with all 12 plants. Only 12 ripe tomatoes were produced on orbit. Yield was similar between ground and flight when plants were not stressed. — NASA technical reports in the NTRS search result set ([20240001505](https://ntrs.nasa.gov/citations/20240001505), [20240016407](https://ntrs.nasa.gov/citations/20240016407), [20250000747](https://ntrs.nasa.gov/citations/20250000747)); the specific report was not pinned down. See also the [NASA VEG-05 investigation page](https://science.nasa.gov/biological-physical/investigations/veg-05).

**Arabidopsis / seedling imaging on the ISS**
- A 2012 BMC Plant Biology study grew Arabidopsis on the ISS in a habitat with a camera that took images every 6 hours for 15 days. — search result for ["Plant growth strategies are remodeled by spaceflight"](https://ouci.dntb.gov.ua/en/works/leaxO2Ol/)
- The Petri Plants investigations kept their ground controls in the ISS Environmental Simulator (ISSES) chamber at KSC. Images went from the Light Microscopy Module to the Telescience Support Center. — [NASA SpaceX blog, Feb 2017](https://blogs.nasa.gov/spacex/2017/02/19/dragons-cargo-includes-diverse-experiments/)
- OSDR study OSD-38 (SpaceX-5) plated Arabidopsis Col-0 on twenty-two 60 mm Petri plates. The record links downloads at osdr.nasa.gov, but it is not confirmed that images are included. — [data.gov record](https://catalog.data.gov/dataset/proteomics-and-transcriptomics-analysis-of-arabidopsis-seedlings-in-microgravity)

**ESA**
- The CC BY-SA 3.0 IGO licence applies only where ESA expressly states it. Other ESA images fall under its standard copyright notice, which requires credit and needs a specific licence for commercial use. The ESA logo is excluded from the CC licence. — [ESA Copyright Notice Images](https://www.esa.int/ESA_Multimedia/Copyright_Notice_Images); [ESA open access policy](https://esa.int/About_Us/Digital_Agenda/ESA_affirms_Open_Access_policy_for_images_videos_and_data)
- Credit format: "ESA/Photographer's name, CC BY-SA 3.0 IGO", keeping any photographer's name. Include a licence link and do not imply ESA endorsement. Light edits such as cropping, sharpening, colour management and embedding are fine. Substantial changes that cannot be shared under the same licence need an ESA waiver of share-alike. — [open.esa.int](https://open.esa.int/?p=2); [ESA Rosetta blog example](https://blogs.esa.int/rosetta/?p=2699)
- ESA TV published a 1 min 36 s clip (July 2026) of Veggie time-lapses from Columbus, showing alfalfa in Veg-06. Its licence was not checked. — [ESA TV: Veggie – Growing plants for science](https://www.esa.int/esatv/Videos/2026/07/Veggie_Growing_plants_for_science)
- WAICO, the first Columbus experiment, compared wild-type and genetically modified Arabidopsis, with daily video images of root growth in Biolab. No public download was found. — [Universe Today](https://www.universetoday.com/articles/first-experiment-starts-in-iss-columbus-module-testing-plant-growth)

**Crystals and flames (watch-only physics)**
- NASA's "Candle Flame – 1g vs Microgravity" image pairs an Earth flame with a microgravity flame. — [NASA image article](https://www.nasa.gov/image-article/candle-flame-1g-vs-microgravity/)
- A EurekAlert copy credits NASA Johnson Space Center with usage restrictions "None". — [EurekAlert 734151](https://www.eurekalert.org/multimedia/734151)
- Commons marks a 1g vs 0g candle comparison (Space_Fire.jpg) as public domain because NASA created it. — [Commons File:Space Fire.jpg](https://commons.wikipedia.com/wiki/File:Space_Fire.jpg)
- NASA SVS has an entry "NASA Studies Fire in Microgravity". — [SVS 31394](https://svs.gsfc.nasa.gov/31394)
- Search results describe a NASA/JSC image captioned (a) Earth-grown vs (b) microgravity-grown protein crystals, the space crystals being larger and more uniform. The exact page was not pinned down. — [NASA search result](https://www.nasa.gov/?p=1002181)
- Don Pettit's 2026 ISS photo of a hollow potassium-chloride "hopper" crystal has no Earth comparison. — [Live Science](https://livescience.com/chemistry/nasa-astronaut-shares-image-of-impossible-looking-hopper-crystal-growing-on-the-space-station-what-is-happening)

### Inferences
- **PH-04 pepper time-lapse.** This is the most "cool to watch" NASA asset that is unambiguously NASA-created and a direct-download 1080p file. It suits the "watch → measure" part of the demo: plant area and height growth, and colour (CIELAB ΔE) as the fruit ripens. It cannot support a verdict, because no control is in frame.
- **PH-07 stills.** These are the only NASA-catalogued images with a control and treatments in one frame. The four moisture levels (drought, wilt, control, flood) are an ordinal factor, not a numeric one. There are only three timepoints, likely with different framing. Because Techshot holds the copyright, I would not show these in a public demo without permission from Redwire (Techshot's successor).
- **NASA logos and astronauts.** APH hardware and NASA videos may show NASA logos and astronauts. Crop or avoid them, and add "Credit: NASA" (or "NASA/Francisco Martin") on screen.
- **Flame material.** Flame imagery is fine to re-analyse because Argus only watches. This matches safety rule 8 (no automatic hardware actions for flame).

### Gaps
- No NASA or ESA time-lapse showing flight and ground control in the same frame was found. Whether the PH-04 ground-control run at KSC was filmed as a time-lapse is unknown.
- Whether the PH-07 stills show at least 2 plants per treatment, and the plant count per section, could not be confirmed from the metadata.
- Not verified: the image content of OSDR OSD-38; supplementary movies for the 2012 BMC Plant Biology study; NASA GeneLab image downloads in general.
- Not checked: the licence of the ESA Veg-06 clip and of ESA multimedia plant videos generally; NASA SVS fluid-physics items; ISS bacterial-growth and slime-mould items. The CNES "blob" (Physarum) ISS and classroom experiment was not researched.

## Q2. Other US government, museum and library sources (USDA ARS, NOAA, USGS, Smithsonian, Wellcome)

### Takeaway
The USDA ARS Image Gallery is public domain with specific credit lines, but it holds stills, not time-lapse controlled experiments. No usable Smithsonian, Wellcome, NOAA or USGS footage of controls vs treatments was verified in this session.

### Cited Findings
- ARS gallery photos "are available free of charge and are copyright-free, public domain, images unless otherwise indicated". The approved credit lines are a photographer line, "Photo courtesy of USDA Agricultural Research Service", or "Photo courtesy of USDA ARS". Photos may not imply ARS endorsement. — [ARS image copyright page](https://www.ars.usda.gov/oc/images/copyright)
- The ARS Image Gallery is mirrored on Ag Data Commons, with more than 2,000 JPEGs. — [Ag Data Commons: USDA ARS Image Gallery](https://agdatacommons.nal.usda.gov/articles/dataset/USDA_ARS_Image_Gallery/24659814)

### Inferences
- ARS stills could serve as one-off "photo of a field trial" examples. They are not time series, so they would not show Argus's tracking well.

### Gaps
- Not searched for lack of tool budget: Smithsonian Open Access (CC0) video holdings, Wellcome Collection (CC BY), NOAA, USGS, US national labs. The common NOAA image of a pteropod shell dissolving in acidified water is, as far as I know, a third-party (National Geographic) photo. This was not verified, so do not assume it is public domain.

## Q3. Open-access paper supplementary movies and datasets (CC BY / CC0) with side-by-side conditions

### Takeaway
The strongest openly licensed material is: (1) the Danforth Center Setaria "Bellwether" image set (CC BY 4.0, 79,200 images, water-limited vs well-watered plants, with a camera calibration file for real units); (2) Futo et al. 2022 (Scientific Reports, CC BY 4.0), with 1080p time-lapse videos of *Bacillus subtilis* biofilms every 6 minutes, a 1 cm scale bar, strains filmed in parallel and a three-replicate video; (3) a CC BY 4.0 PLOS ONE infrared time-lapse of *Brachypodium* growth under switching temperature regimes. Most PLOS and Nature Communications videos on Commons are cell microscopy, not macro side-by-side scenes. No CC footage was found for corrosion, coffee rings, bread, hydrogels or salt-gradient germination.

### Cited Findings
**Danforth Center plant phenotyping datasets (CC BY 4.0 / CC0)**
- Dataset 1: Fahlgren et al. 2015, "A Versatile Phenotyping System and Analytics Platform Reveals Diverse Temporal Responses to Water Availability in Setaria" (Molecular Plant, DOI 10.1016/j.molp.2015.06.005).
  - Licence: "licensed under a Creative Commons Attribution 4.0 International License".
  - Images: 79,200 PNG (118 GB) or 79,200 JPG (4.4 GB), as HTTP tar.gz files.
  - On Figshare: manual measurements (height, biomass, tiller count and angles), water treatment data, soil weight and volumetric water content, and a camera zoom calibration file.
  - Source: [Danforth datasci data page](https://datasci.danforthcenter.org/data/)
- The PlantCV data page lists the study as *Setaria viridis* and *S. italica*, about 79,200 images, VIS/NIR/PSII imaging, shoot, "Growth: Water-limited", available via http, globus and CyVerse. — [PlantCV data page](https://plantcv.danforthcenter.org/pages/data.html)
- The same Danforth page also lists:
  - Feldman et al. *Setaria*: 151,000 PNG, CC BY 4.0, on CyVerse.
  - Veley et al. sorghum resource-use efficiency: 96,867 PNG, 178 GB, CC BY 4.0. The file name refers to nitrogen.
  - Berry et al. colour-standardisation set: 24,000 PNG, 143 GB, CC0.
  - Source: [Danforth datasci data page](https://datasci.danforthcenter.org/data/)

**Futo et al. 2022: bacterial biofilm time-lapse (CC BY 4.0)**
- "A novel time-lapse imaging method for studying developing bacterial biofilms", Scientific Reports 12:21120, published 2022-12-07, DOI 10.1038/s41598-022-24431-y. Authors: Futo, Široki, Koska, Čorak, Tušar, Domazet-Lošo. An Arduino-controlled acrylic robotic arm lifts the Petri lid to avoid condensation. — [PMC9729682](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9729682/); [DOAJ](https://doaj.org/article/1197408d215349ef8ff2e23bb4f03bde)
- Filmed: *B. subtilis* macrocolonies on MSgg agar in 90 mm dishes, at 30 °C and about 85% RH, under a stereomicroscope with episcopic light. Strains NCIB3610, 100, 102, 106 and 108 were each on their own plate.
- Photos every 6 min:
  - 3-day runs: strain 108, in 3 replicates.
  - 7-day runs: strains 100, 102, 108 and NCIB3610.
  - 21-day run: strain 106.
- Size and scale: camera frames 6000x4000; videos 1920x1080 at 30 fps; scale bars added, 1 cm in Fig. 1.
- Supplementary videos include Video 8 (four strains in parallel), Video 9 (two strains in parallel) and Video 10 (three replicates of strain 108). Videos are hosted on FigShare and private YouTube links listed in a table in the article. Code is at github.com/bacillus-biofilms/time-lapse-imaging. The article is CC BY 4.0.
- Source for the three points above: [PMC9729682 full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC9729682)

**PLOS ONE *Brachypodium* infrared time-lapse (CC BY 4.0, on Commons)**
- Matos D, Cole B, Whitney I, MacKinnon K, Kay S, Hazen S (2014), "Daily Changes in Temperature, Not the Circadian Clock, Regulate Growth Rate in Brachypodium distachyon", PLOS ONE, DOI 10.1371/journal.pone.0100072. Movie S3 is an infrared time-lapse of seedlings: 12 h light at 28 °C alternating with 12 h dark at 12 °C, then constant light at 28 °C, with "Conditions are noted in each frame".
- File: 1280x720, 22 s, 2.1 MB, Ogg Theora, licensed CC BY 4.0. It was imported by the Open Access Media Importer bot. The frame interval is not stated.
- Source for both points: [Commons file page](https://commons.wikimedia.org/wiki/File:Daily-Changes-in-Temperature-Not-the-Circadian-Clock-Regulate-Growth-Rate-in-Brachypodium-distachyon-pone.0100072.s004.ogv)

**Other Commons material**
- A Commons MediaSearch for "time-lapse control treatment" videos returned about 40 Ogg files from PLOS ONE, PLOS Genetics, PLOS Pathogens and Nature Communications. Almost all are cell or tissue microscopy (tumour cells, neurons, *M. tuberculosis* localisation). None was plant, fungal, crystal, food, corrosion or droplet footage. — [Commons MediaSearch](https://commons.wikimedia.org/w/index.php?search=time-lapse+control+treatment+filetype%3Avideo&title=Special:MediaSearch&type=video)
- "Category:Time-lapse videos of plants" has 70 files, with licences not checked per file. Relevant ones include:
  - "Apex reorientation in Pinus pinaster during the first 24h after plant inclination - 1471-2229-10-217-S1.ogv" (BMC Plant Biology supplementary, gravitropism)
  - "Pea de-etiolation.ogv" and "Pea de-étiolation with circadian cycle.ogv"
  - "Germination of two little plants.webm" and "Fittonia watered.ogv"
  - "Time Lapse Banana Ripening.webm", "Rotting carrot time lapse video.ogv" and "Pourrissement tomate.webm"
  - "Browning Fuji apple - 32 minutes in 16 seconds.webm"
  - Source: [Commons category](https://commons.wikimedia.org/wiki/Category:Time-lapse_videos_of_plants)
- The browning apple file is by Vassia Atanassova (User:Spiritia), own work, 2017-02-12, licensed CC BY-SA 4.0. It was made from 32 photos at 1-min intervals played at 2 fps: 600x600 px, 16 s, 56 KB. It shows one apple, with no lemon-juice or untreated control. — [Commons file page](https://commons.wikimedia.org/wiki/File:Browning_Fuji_apple_-_32_minutes_in_16_seconds.webm)
- Commons has 11 Physarum videos, including "Timelapse of Slime Mould.webm", "Australian Physarum polycephalum timelapse.webm" and a paper-style file "Plant hairy root cultures as plasmodium modulators of the slime mold emergent computing substrate Physarum polycephalum - Video1.webm". None is labelled as a maze or side-by-side condition, and licences were not checked. — [Commons MediaSearch "Physarum"](https://commons.wikimedia.org/w/index.php?search=Physarum&title=Special:MediaSearch&type=video)

**Other microbiology and germination leads**
- ColTapp (Scientific Reports 2020, DOI 10.1038/s41598-020-72979-4) released 22 time-lapse movies of *Staphylococcus aureus* colonies on blood agar, designed with varied lag times and densities. The software is GPL-3.0; the dataset's licence was not found. — [PMC7528005](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7528005/)
- A Sensors 2020 paper built a time-lapse from periodic snapshots of a *Candida* dish (single dish). — [PMC7248749](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7248749/)
- SPIRO (Ohlsson, Leong, Minina et al.) is an open-source robot for time-lapse imaging of up to 4 vertical Petri plates. An imaging cycle takes under 2 min, it has a green LED for night imaging, and it comes with an Arabidopsis germination assay. The hardware repo is CC BY 4.0. No public image dataset was found. — [bioRxiv 2021.03.15.435343](https://www.biorxiv.org/content/10.1101/2021.03.15.435343.full.pdf); [GitHub AlyonaMinina/SPIRO](https://github.com/AlyonaMinina/SPIRO)
- A 2024 bioRxiv paper (SPENCER robot) images germination under ABA and DOG1 conditions. Its licence and data were not checked. — [bioRxiv 2024.05.10.593629](https://www.biorxiv.org/content/10.1101/2024.05.10.593629.full.pdf)
- A 2024 Frontiers in Plant Science licorice study imaged full-time-sequence sprouting under different NaCl concentrations. Whether it has a supplementary video, and its licence, were not checked. — [Frontiers 10.3389/fpls.2024.1474321](https://public-pages-files-2025.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2024.1474321/text)

### Inferences
- **Danforth Setaria (best fit for the verdict logic).** This is the best match for Argus's requirements: many replicate plants per watering condition, CC BY 4.0, direct HTTP download, and a zoom-calibration file for converting pixels to millimetres.
  - Caveat: as far as I know, Bellwether images are one plant per image (conveyor imaging cabinet), not a multi-pot scene. That is not confirmed here. A demo would need a scripted mosaic, e.g. a 4x4 grid of 8 well-watered and 8 water-limited plants over days. That fits SAM's ~16-object limit, and the composite must be labelled as an assembled re-analysis.
  - If the water treatment file shows 3 or more levels, the "next run" suggestion (numeric factor with 3 or more levels) works directly. If only 2 levels, Argus could propose intermediate levels.
- **Futo et al. biofilm videos (most visually striking).** Wrinkled colonies grow over days at 6-min resolution, in 1080p with a real scale bar, and the licence is CC BY 4.0.
  - The comparison is between strains (genotype), not a treatment. Only strain 108 has replicates (3), so a strict verdict of 2 or more replicates per condition is not possible across strains.
  - The "parallel" videos are tiled composites of plates filmed separately.
  - *B. subtilis* is a low-risk lab organism, so it is fine to show.
- **Brachypodium (within-subject changepoints).** Growth rate changes when the temperature regime changes, which suits changepoint detection (ruptures) and a "the condition changed here" note. It is not a between-group control vs treatment design.
- **ColTapp (*S. aureus*).** Avoid it in the demo even if the licence clears. *S. aureus* is a BSL-2 pathogen, and showing pathogen culture in a public demo sits awkwardly with Argus's pathogen safety stance.
- **ShareAlike.** CC BY-SA files (e.g. the apple browning video) require derived overlays to be shared under CC BY-SA. That is manageable for a demo video, but do not commit the files to the public repo.

### Gaps
- No CC BY, CC0 or public-domain macro footage with side-by-side conditions was found for: corrosion (steel in salt water vs control), coffee-ring evaporation, bread or dough rising, fruit browning with a control, cheese or fermentation, hydrogel swelling, or salt-gradient germination. Searches were limited, so absence is not proven.
- Fahlgren et al. 2015: the number of water levels, plants per treatment, imaging frequency and views (top or side) were not on the data page and were not verified. The Figshare items' licences were also not checked.
- Futo et al.: exact FigShare URLs and the published quantitative growth values were not extracted. Strain identities (wild type vs mutants vs isolates) beyond NCIB3610 were not checked.
- Not checked: per-file licences of the Commons plant and Physarum videos; source papers for the Pinus pinaster and Physarum "Video1" files.
- eLife, PNAS, Frontiers and Nature Communications were not searched systematically for macro-scale side-by-side movies.

## Q4. University and museum open video collections (CC licences, NC flags)

### Takeaway
Open University OpenLearn releases material under CC BY-NC-SA 4.0 "wherever possible", but third-party video (e.g. BBC) is excluded and must be checked item by item. NC licences are a risk for a hackathon demo whose terms or prizes may count as commercial.

### Cited Findings
- The Open University releases OER under CC BY-NC-SA 4.0 wherever possible, with other licences handled case by case. — [OU OER Operating Policy](https://university.open.ac.uk/open-educational-resources/home/open-educational-resources-operating-policy)
- OpenLearn's CC licence excludes third-party material. Acknowledgements sections mark items such as video "© The Open University and its licensor (BBC)" or "Proprietary and used under licence (not subject to Creative Commons Licence)". — [Copyright of OpenLearn](https://about.open.ac.uk/strategy-and-policies/policies-and-statements/copyright-openlearn); [How OpenLearn uses third-party content](https://www.open.edu/openlearn/get-started/how-openlearn-uses-third-party-content)
- SUNY ESF hosts an open-access 1960 time-lapse film, "Seed Germination" (Harlow), showing a wide variety of germination experiments. Its licence and resolution were not checked. — [SUNY ESF Experts](https://experts.esf.edu/esploro/outputs/film/Seed-Germination/99870862704826)

### Inferences
- Treat any NC material (OpenLearn, and MIT OCW, which uses BY-NC-SA per general knowledge) as second choice behind public-domain, CC0 and CC BY sources.

### Gaps
- Not verified in this session: MIT OpenCourseWare's licence wording, Exploratorium video licensing, and the Openverse video search.

## Q5. Ranked shortlist: what is filmed, is it a downloadable file, and how would it look in a demo?

### Takeaway
No single openly licensed source found here fully meets Argus's verdict requirements (control vs treatment, 2 or more replicates each, in one continuous time-lapse). The practical combination is:
- **Hook:** the NASA PH-04 pepper time-lapse (public domain, 1080p, direct MP4).
- **Re-analysis with a real verdict:** a labelled mosaic from the Danforth Setaria CC BY 4.0 image set (water-limited vs well-watered, many replicates).
- **Visual "cool to watch" moment with a real scale bar:** the Futo et al. biofilm videos (CC BY 4.0, Videos 8 and 10).

### Cited Findings
**1. Danforth Setaria Bellwether, Fahlgren et al. 2015**
- What: Setaria shoots imaged over time, water-limited vs well-watered.
- Files: 79,200 JPG (4.4 GB) or PNG (118 GB) via HTTP tar.gz. Figshare has the water treatment data and a camera zoom calibration file.
- Licence: CC BY 4.0. Attribution: Fahlgren et al. 2015, Mol Plant, DOI 10.1016/j.molp.2015.06.005, plus a licence link and a note of changes.
- Published results to check against: the manual height and biomass measurements on Figshare.
- Source: [Danforth data page](https://datasci.danforthcenter.org/data/)
- Demo look: a grid of pots greening and growing, with control and drought diverging in area and height. Argus's verdict and its "next run: try X% water" suggestion land naturally.

**2. Futo et al. 2022 *B. subtilis* biofilms**
- What: wrinkled macrocolonies growing in 90 mm dishes.
- Timing and size: 6-min interval over 3 to 21 days; 1920x1080 at 30 fps (raw frames 6000x4000); 1 cm scale bar.
- Conditions: strains in parallel (Video 8), 3 replicates of strain 108 (Video 10).
- Files: FigShare and YouTube.
- Licence: CC BY 4.0. Attribution: Futo et al., Sci Rep 12:21120 (2022), DOI 10.1038/s41598-022-24431-y.
- Source: [PMC9729682](https://pmc.ncbi.nlm.nih.gov/articles/PMC9729682)
- Demo look: dramatic organic growth in true mm², SAM masks on each colony, and colour and texture change. Replicate consistency is shown well, but there is no treatment arm.

**3. NASA PH-04 chile pepper time-lapse ("Peppers Timelapse Longe Rev 7")**
- What: chile peppers growing aboard the ISS, flight only.
- Format: 59 s, 1920x1080, 30 fps, 135 MiB.
- Files: direct `~orig.mp4` from images-assets.nasa.gov, plus an `.srt` caption file.
- Licence: public domain (NASA). Credit "NASA" or "NASA/Francisco Martin". Do not use the NASA logo or imply endorsement.
- Source: [metadata.json](https://images-assets.nasa.gov/video/Peppers%20Timelapse%20Longe%20Rev%207/metadata.json); [asset manifest](https://images-api.nasa.gov/asset/Peppers%20Timelapse%20Longe%20Rev%207)
- Demo look: a strong opening shot. Argus segments the plant and fruit and charts area and fruit colour ΔE (green → red). It cannot give a verdict, because there is no control.

**4. NASA PH-07 lettuce moisture treatments (jsc2025e047407–410)**
- What: lettuce in the APH ground unit. Control vs flood, and drought vs wilt, side by side on days 7, 14 and 28.
- Format: stills, 6000x4000.
- Files: images.nasa.gov.
- Licence: creator Techshot, Inc., metadata "Copyright: 2021", "courtesy of the PH-07 Team". This is third-party, so permission is needed.
- Source: [images-api PH-07](https://images-api.nasa.gov/search?q=PH-07&media_type=image,video); [metadata](https://images-assets.nasa.gov/image/jsc2025e047409/metadata.json)
- Demo look: a space-relevant control vs treatment comparison, but only 3 stills.

**5. PLOS ONE *Brachypodium* infrared time-lapse, Matos et al. 2014, Movie S3**
- Format: 1280x720, 22 s. The condition labels are burned into the frames.
- Files: direct download from Commons.
- Licence: CC BY 4.0. Attribution: Matos D et al. (2014) PLOS ONE, DOI 10.1371/journal.pone.0100072, CC BY 4.0.
- Source: [Commons](https://commons.wikimedia.org/wiki/File:Daily-Changes-in-Temperature-Not-the-Circadian-Clock-Regulate-Growth-Rate-in-Brachypodium-distachyon-pone.0100072.s004.ogv)
- Demo look: shoots elongating, with a growth-rate changepoint when the regime switches. Good for the measurement and changepoint feature, weak for a between-group verdict.

**6. NASA candle flame, 1g vs microgravity**
- What: a public-domain still pair, watch-only. Credit "NASA" (EurekAlert lists NASA JSC with no usage restrictions).
- Source: [NASA](https://www.nasa.gov/image-article/candle-flame-1g-vs-microgravity/); [EurekAlert](https://www.eurekalert.org/multimedia/734151)
- Demo look: a quick colour and shape comparison (flame ΔE and aspect ratio). It shows the safety stance: watch, never act.

**7. NASA PH-02 radishes**
- What: ground-control stills and harvest video (NASA/Kim Shiflett, NASA/Glenn Benson), plus separate flight-harvest imagery.
- Licence: public domain.
- Source: [images-api](https://images-api.nasa.gov/search?q=plant%20habitat%20ground%20control&media_type=image,video); [Kennedy blog](https://blogs.nasa.gov/kennedy/2020/12/15/kennedy-harvests-radish-crop-as-part-of-ph-02-experiment)
- Demo look: a static before/after comparison. The ground and flight images come from different cameras and framing, which weakens measurement.

**8. Commons "Browning Fuji apple"**
- Format: 32 frames at 1-min intervals, 600x600, 16 s.
- Licence: CC BY-SA 4.0. Attribution: "Vassia Atanassova (Spiritia), CC BY-SA 4.0, via Wikimedia Commons".
- Source: [Commons](https://commons.wikimedia.org/wiki/File:Browning_Fuji_apple_-_32_minutes_in_16_seconds.webm)
- Demo look: a clean ΔE curve. It is low resolution, has no control, and is share-alike.

**9. ColTapp *S. aureus* colony movies**
- What: 22 movies of colonies on blood agar.
- Licence: dataset licence unknown.
- Source: [PMC7528005](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7528005/)
- Not recommended, because the organism is a pathogen.

### Inferences
- Download mechanics: NASA assets come from the manifest at `images-api.nasa.gov/asset/{nasa_id}` and download as `~orig` files. Commons files have a direct "Original file" link. Danforth datasets are HTTP tar.gz files. Futo et al. videos come via the FigShare links in the article's table.
- Keep all third-party footage out of the public repo (rule 6 spirit and licence hygiene). Fetch it with a documented script, and show on-screen attribution in the demo, including the licence name and link for CC items.
- If 2 or more replicates per condition in a single real scene is essential and none of the above suffices, the fallback is the team's own filmed experiment. That is outside this note's scope.

### Gaps
- Not done for any candidate: frame-by-frame checks of real visual quality (lighting flicker, framing changes), because nothing was downloaded.
- Exact Figshare file URLs and sizes for the Futo et al. videos and the Danforth water-treatment table were not retrieved.
- The published numeric results to check against were only identified, not extracted: Setaria height and biomass under water limitation, and biofilm growth metrics.
