# Online timelapse videos of slow lab experiments (germination first): where to find them, licences, and search phrases

Scope: finding professional or semi-professional timelapse videos (or image sequences) of slow experiments, above all seed germination with treatments vs controls, that Argus Labs may legally analyse and show in a public 3-minute demo video (YouTube/X) and possibly keep in a public GitHub repo. Research date: 29 Oct 2026. Nothing was downloaded or redistributed; every finding below comes from public web pages and APIs.

Overall bottom line: no single **verified-CC** video was found that shows ≥2 controls and ≥2 treatments side by side under one fixed camera with a ruler. The cleanest legal options are (a) **CC BY 4.0 supplementary movies from open-access papers** (mirrored on Wikimedia Commons by the Open Access Media Importer), including a set of 18 Brachypodium seedling movies under different temperature/light regimes, (b) a **CC BY 4.0 top-down petri-dish image dataset** (Genze et al., Mendeley Data; 85 mm dishes give a known-size scale), and (c) single-condition CC BY / CC BY-SA germination timelapses on Commons. Treatment-vs-control videos with good designs exist mainly on YouTube or university video sites under all-rights-reserved terms, so they need the creator's permission.

---

## 1. Licensing: can footage be analysed, shown in a public demo, and kept in a public repo?

### Takeaway
CC BY and CC BY-SA footage (YouTube CC, Wikimedia Commons, open-access journal supplements) can be analysed, shown and redistributed if you give TASL attribution (BY-SA also needs share-alike for adaptations). Pexels and Pixabay footage can be shown in the demo without credit but should **not** sit as raw files in a public repo. Standard-licence YouTube videos need the creator's permission. Fair use for a hackathon demo is uncertain, because no clip length is automatically safe.

### Cited Findings
**YouTube**
- Every upload gets the Standard YouTube License unless the creator changes it. YouTube calls it "the default setting for all YouTube uploads" and points to the Terms of Service for its terms — [YouTube Help: License types](https://support.google.com/youtube/answer/2797468?hl=en)
- If a creator marks a video CC BY, "other creators can reuse your work subject to the terms of the CC BY license." The creator keeps the copyright. Reusers must give credit; YouTube suggests including title, author, source URL and a note that the work "is licensed under CC BY", as a text overlay or voiceover — [YouTube Help: License types](https://support.google.com/youtube/answer/2797468?hl=en)
- To find CC videos, select "Creative Commons" in the advanced search filters, or look in the description. YouTube "can't grant rights to someone else's content". For Standard-licence content it suggests contacting the creator directly — [YouTube Help: License types](https://support.google.com/youtube/answer/2797468?hl=en)
- YouTube's Terms of Service say users may not "access, reproduce, download, distribute, transmit" Content except "as expressly authorized by the Service" or "with prior written permission from YouTube". Embedding through the YouTube player is allowed — [YouTube Terms of Service](https://www.youtube.com/static?template=terms)
- Wikimedia Commons does not accept the Standard YouTube License because it "is not free enough", but it accepts YouTube CC BY. Some channels upload content they don't own and mislabel it CC BY ("license laundering"). Commons keeps a list of questionable YouTube channels and offers a {{LicenseReview}} process to "permanently document" that a video was available under the licence — [Commons:YouTube files](https://commons.wikimedia.org/wiki/Commons:YouTube_files)
- **CC BY version conflict:** the fetched Commons:YouTube files page names CC BY 4.0 as YouTube's option but also has a template for videos "released under CC BY 3.0" — [Commons:YouTube files](https://commons.wikimedia.org/wiki/Commons:YouTube_files). YouTube-sourced files on Commons from older uploads carry **CC BY 3.0** (e.g. Lima Bean Time Lapse, Borevitz's Arabidopsis video) — [Commons API metadata](https://commons.wikimedia.org/wiki/File:Lima_Bean_Time_Lapse.webm). YouTube's help page just says "CC BY" — [YouTube Help](https://support.google.com/youtube/answer/2797468?hl=en)

**Attribution practice (Creative Commons)**
- Credit Title, Author, Source (original URL) and License, linked to the licence deed (TASL). Note light changes (e.g. "Cropped from original"). For an adaptation, credit the original and state that your work is adapted from it. ND licences forbid adaptations — [CC wiki: Recommended practices for attribution](https://wiki.creativecommons.org/wiki/Recommended_practices_for_attribution)
- For video, CC recommends attribution "both in the description box and in ... the video recording itself" — [CC wiki](https://wiki.creativecommons.org/wiki/Recommended_practices_for_attribution)

**Stock sites**
- Pixabay: free use, no attribution required, you may modify content "into new works". You may **not** sell or distribute content "on a Standalone basis", meaning substantially unchanged from the site. Third-party rights (trademarks, people) are the user's responsibility — [Pixabay licence summary](https://pixabay.com/service/license-summary/)
- Pexels: "Attribution is not required", and you may modify the videos. Don't "sell unaltered copies", and don't "redistribute or sell" the content on other stock or wallpaper platforms. The licence page doesn't mention code repositories or raw-file distribution — [Pexels licence](https://www.pexels.com/license/)
- Videvo: each clip has its own licence. Clips under the "Videvo Attribution License" must credit Videvo on screen or in text. Some clips are CC 3.0 or public domain with a specific credit line. Videvo's guide says you "may NOT redistribute the clip(s) in their original form" — [Videvo blog: Licenses and Usage](https://www.videvo.net/blog/?p=314); summarised also by [licenseorg.com](https://licenseorg.com/guide/video/videvo) (third-party, possibly dated)
- Vimeo has a Creative Commons collection you can browse by licence: BY, BY-SA, BY-ND, BY-NC, BY-NC-SA, BY-NC-ND and Public Domain Dedication. The Attribution collection lists about 2.8M videos. The page doesn't say whether downloads are enabled — [Vimeo Creative Commons](https://vimeo.com/creativecommons)

**Fair use (US)**
- The four factors are purpose and character (commercial vs nonprofit educational, transformative), nature of the work (factual favours fair use more than creative), amount used ("If the use includes a large portion of the copyrighted work, fair use is less likely to be found"), and effect on the market — [US Copyright Office: More information on fair use](https://www.copyright.gov/fair-use/more-info.html)
- "there is no formula to ensure that a predetermined percentage or amount of a work" may be used without permission — [US Copyright Office](https://www.copyright.gov/fair-use/more-info.html)
- University guides warn that educational use "does not automatically result in a finding of fair use", because all four factors are weighed — [Missouri S&T LibAnswers](https://mst.libanswers.com/copyrightfairuse/faq/396117); [UC Copyright: fair use](https://copyright.universityofcalifornia.edu/use/fair-use.html)

### Inferences
- **Safest rule for Argus:** use only CC BY, CC BY-SA, CC0/public-domain or permission-granted footage. Treat fair use as a last resort. The demo is for a prize-awarding hackathon (arguably commercial), and analysing a whole timelapse uses "the whole work". Transformation (measurement overlays, verdicts) helps the argument but doesn't guarantee it.
- **Analysis vs display vs repo:**
  - *Analysing* a lawfully obtained copy locally is low-risk under every licence above.
  - *Showing* it in the demo needs a licence that allows public display: CC, Pexels/Pixabay or permission.
  - *Committing* the raw file to the public repo is a redistribution. That's fine for CC BY and CC BY-SA if an ATTRIBUTION file is included, but arguably "standalone" distribution for Pixabay/Pexels/Videvo. For those sources, commit a `fetch_demo_video.py` or README link instead of the file.
- **CC BY-SA catch:** Commons germination clips such as Mung bean, Germinacion 2, Germination of two little plants and Pea de-etiolation are BY-SA. If the demo overlays masks or measurements on them, the overlaid version is likely an adaptation, so it should be released under CC BY-SA too. One simple approach is to label the demo video "CC BY-SA 4.0" on YouTube or in its description. CC BY sources avoid this.
- **Attribution template** for the demo end card and the YouTube description: `"<Title>" by <Author>, <source URL>, licensed CC BY 4.0 (<deed URL>); cropped and annotated with Argus measurements.`
- **Permission request (for Standard-licence YouTube or university videos):** send a short, specific email or YouTube/channel contact message. Include:
  - who you are, the hackathon name and deadline (Nov 4, 2026)
  - the exact video URL
  - the intended uses: analysed by software, a clip of ≤X seconds shown in a public demo on YouTube/X, credited on screen and in the description, not resold, file not redistributed
  - a request for the original frame interval and any scale info
  - a request for written consent by reply
  
  Keep the written reply as the licence record. With 6 days left, send requests now and keep a CC fallback ready.

### Gaps
- Pixabay's full Terms (pixabay.com/service/terms/) and Videvo's current licence page weren't read in full. The standalone-distribution reading for a GitHub repo is an inference, because neither licence mentions repositories.
- I could not confirm whether YouTube's CC option is currently CC BY 3.0 or 4.0 (sources conflict, see above).
- I didn't confirm the hackathon's own rules on third-party footage. Check the official rules.

---

## 2. Where do suitable videos live, and which concrete candidates exist?

### Takeaway
The best verified-licence sources are Wikimedia Commons (category "Time-lapse videos of plants", 70 files, plus open-access paper supplements imported by the Open Access Media Importer bot) and the CC BY 4.0 Genze et al. petri-dish dataset. True treatment-vs-control comparisons in a single frame were found only in permission-only sources: YouTube school or hobby videos, a UC Davis course video and a fertiliser company blog.

### Cited Findings
**A. Verified CC, with a treatment or comparison element (strongest legal candidates)**
- **Brachypodium distachyon temperature/light series (18 movies, s002–s019):** infrared timelapses of several seedlings under alternating temperature and light regimes (constant, inverted, photocycle), from Matos et al. 2014, PLOS ONE, DOI 10.1371/journal.pone.0100072.
  - Example s004: "12 hr light, 28°C and 12 hr dark, 12°C", then constant light at 28°C. Conditions are labelled in each frame.
  - 1280×720, ~22 s, **CC BY 4.0**.
  - [Commons file s004](https://commons.wikimedia.org/wiki/File:Daily-Changes-in-Temperature-Not-the-Circadian-Clock-Regulate-Growth-Rate-in-Brachypodium-distachyon-pone.0100072.s004.ogv); the series of 18 is listed in a [Commons search](https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch=filetype:video%20(salt%20OR%20salinity%20OR%20drought%20OR%20seedlings%20OR%20%22time-lapse%22%20seedling)&srnamespace=6&srlimit=50&format=json)
- **Genze et al. germination image dataset (Mendeley Data, DOI 10.17632/4wkt6thgp6.3, v3, 24 Jul 2023):** **CC BY 4.0**, top-down Raspberry Pi Camera v2.1 about 40 cm above the dishes, one photo every 30 min for ~2 days.
  - 12 petri dishes (85 mm) in a 4×3 grid on black cloth, ~10 seeds per dish.
  - Maize (824 seeds), rye (811) and pearl millet (814), with bounding boxes labelled germinated or non-germinated.
  - The only "treatment" is water spraying at the start, so the built-in comparison is between species or cultivars, not treatment vs control.
  - Code: GitHub grimmlab/GerminationPrediction — [Mendeley Data](https://data.mendeley.com/datasets/4wkt6thgp6)
  - Paper: Genze et al. 2020, *Plant Methods* 16:157, CC BY, PMC7754596, ">23,000 images" — [Europe PMC record](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:10.1186/s13007-020-00699-x&resultType=core&format=json)
- **Pea de-etiolation:** a pea grown in darkness for 13 days, then constant light for 31 h. One image per minute, played at 20 fps. 1630×2229 (portrait), 92.6 s, **CC BY-SA 3.0**. A dark→light treatment over time, not side by side — [Commons](https://commons.wikimedia.org/wiki/File:Pea_de-etiolation.ogv). A sibling file "Pea de-étiolation with circadian cycle.ogv" also exists — [Commons category](https://commons.wikimedia.org/wiki/Category:Time-lapse_videos_of_plants)
- **Phototropism in Solanum lycopersicum.webm** (directional light) and **Apex reorientation in Pinus pinaster** (inclination; BMC Plant Biology supplement) are also on Commons. Their licences weren't individually checked, though Commons accepts only free licences — [Commons search](https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch=filetype:video%20(salt%20OR%20salinity%20OR%20drought%20OR%20seedlings%20OR%20%22time-lapse%22%20seedling)&srnamespace=6&srlimit=50&format=json)

**B. Verified CC, single-condition germination (good for segmentation and growth demos, not for verdicts)**
- **Lima Bean Time Lapse** by David Marvin: several lima beans sprouting over 6 days from more than 1,600 photos. 1280×720, 119 s, **CC BY 3.0**. Original on YouTube https://www.youtube.com/watch?v=iZMjBO6A7AE (channel @davelansingmi) — [Commons](https://commons.wikimedia.org/wiki/File:Lima_Bean_Time_Lapse.webm); [YouTube oEmbed](https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=iZMjBO6A7AE&format=json)
- **Mung bean germination** (Reigate College science technicians; Canon PowerShot A590 with CHDK): ~10 days, 1080×810, 65 s, **CC BY-SA 3.0** — [Commons](https://commons.wikimedia.org/wiki/File:Mung_bean_germination.ogv)
- **Germinacion 2** (Akronix): several tomato plants, one photo every 5 min, 119 photos at 4 fps. 1920×1080, 26 s, **CC BY-SA 3.0** — [Commons](https://commons.wikimedia.org/wiki/File:Germinacion_2.webm)
- **Germination of two little plants** (Quasipodo): 2 tomato seedlings, one photo every 10 min. 1920×1080, 11.5 s, **CC BY-SA 3.0** — [Commons](https://commons.wikimedia.org/wiki/File:Germination_of_two_little_plants.webm)
- **Growing of corn** / **Growing of wheat** (Szabolcs Turuczki): sprouting and root growth. 640×480, 80 s / 57 s, **CC BY-SA 4.0** — [Commons corn](https://commons.wikimedia.org/wiki/File:Growing_of_corn.webm); [Commons wheat](https://commons.wikimedia.org/wiki/File:Growing_of_wheat.webm)
- **Timelapse of lettuce emerging** (Dwight Sipler): one frame every 30 s, ~4 days from seeding to germination, 105 mm macro. 1280×720, 19 s, **CC BY 2.0** — [Commons](https://commons.wikimedia.org/wiki/File:Timelapse_of_lettuce_emerging.webm)
- **Lentil sprouting time lapse** (Always Shooting, via Flickr): lentils sprouting over 5 days on a Haft-Seen table, with music. 1280×720, 112 s, **CC BY 2.0** — [Commons](https://commons.wikimedia.org/wiki/File:Lentil_sprouting_time_lapse-XorAOcaaIk4.webm)
- **Arabidopsis thaliana plants growing in a Growth chamber** (Justin Borevitz; YouTube E1FD_eS3yEE): 1080×720, 10 s, **CC BY 3.0** — [Commons](https://commons.wikimedia.org/wiki/File:Arabidopsis_thaliana_plants_growing_in_a_Growth_chamber.webm)
- Other plant timelapses in the category: Lentil microgreens, Sabzeh sprouting seeds, sunflower germination (GIF, 220×384), MaiszeitrafferErdQuerschnitt (maize in soil cross-section, GIF), Timelapse-Basil-growing, Aerogarden 4 weeks tomatoes and basil, Seedlings.webm (grass, ~150 min). The category also has decay timelapses: Rotting carrot, Pourrissement tomate, Browning Fuji apple, Time Lapse Banana Ripening — [Commons category: Time-lapse videos of plants](https://commons.wikimedia.org/wiki/Category:Time-lapse_videos_of_plants)
- **Open-access paper supplements on Commons (CC BY 4.0, imported from PubMed Central):**
  - Germination platform setup movies (Sizmur et al. 2014, PLOS ONE): mostly assembly footage, not growth — [Commons](https://commons.wikimedia.org/wiki/File:A-Simple-and-Versatile-2-Dimensional-Platform-to-Study-Plant-Germination-and-Growth-under-pone.0096730.s002.ogv)
  - NLP8 nitrate germination paper movie: actually a 20 s confocal subcellular clip, not seed-scale — [Commons](https://commons.wikimedia.org/wiki/File:NIN-like-protein-8-is-a-master-regulator-of-nitrate-promoted-seed-germination-in-Arabidopsis-ncomms13179-s4.ogv)

**C. Treatment vs control designs found, but all-rights-reserved or licence unknown (permission needed)**
- **UC Davis PLS100 "Lab 3: Plant Responses to Temperature – Experimental Demo":** "seed germination for three species: melon, tomato, lettuce, at 8 different temperatures", photographed daily for 12 days. This is the best experimental design found, but it's on a university Kaltura site with no stated licence, and daily photos give few frames — [video.ucdavis.edu](https://video.ucdavis.edu/media/PLS100BL+Lab+3+Plant+Responses+to+Temperature+Experimental+Demo/1_8qcws5se)
- **Wellspring Gardens, 28-day banana plant timelapse:** "Banana Fuel fertilizer vs. plain water", two Dwarf Cavendish plants (n=1 per condition), from a commercial blog — [Wellspring Gardens](https://wellspringgardens.com/blogs/greener-times-ahead-a-blog-by-wellspring-gardens/28-day-banana-plant-time-lapse-banana-fuel-fertilizer-vs-plain-water)
- **"Bread mould one month time lapse - effect of water"** on YouTube; licence and channel not visible to the fetch tool — [YouTube EWVWEIFLZ-E](https://www.youtube.com/watch?v=EWVWEIFLZ-E)
- **Other bread mould timelapses on YouTube** (licences unverified):
  - [YeuI30NQJwo](https://www.youtube.com/watch?v=YeuI30NQJwo)
  - [LAKSuC5_nlw](https://www.youtube.com/watch?v=LAKSuC5_nlw), macro
  - [hN30qCROz9Y](https://www.youtube.com/watch?v=hN30qCROz9Y), mould growth experiment
  - [DTL0nE03XfA](https://www.youtube.com/watch?v=DTL0nE03XfA), 6-month lab timelapse with a freshness card, i.e. a treatment
  - [mLPN9Qwscr0](https://www.youtube.com/watch?v=mLPN9Qwscr0), 38 days
  
  These came from a web search limited to youtube.com. The fetch tool couldn't render YouTube pages, so none of these licences were checked.
- **Neil Bromhall** (seed germination and growth timelapses, including underground sweet corn and wheat): featured by The Kid Should See This and Britannica, with Britannica licensing — [TKSST](https://thekidshouldseethis.com/post/seed-germination-to-growth-time-lapses-by-neil-bromhall); [Britannica cress video](https://www.britannica.com/video/Time-lapse-photography-cress-seeds-water/-16519)
- **Boxlapse** (soil cross-section plant timelapses, e.g. kidney bean and spinach): professional quality, no treatment comparison seen — [TKSST Boxlapse](https://thekidshouldseethis.com/post/boxlapse-time-lapse-plant-videos); [TKSST kidney bean](https://thekidshouldseethis.com/post/kidney-bean-and-spinach-plants-soil-cross-section-time-lapses)
- **Aleš Kladnik "Germination timelapse" on Vimeo:** five species over one week, one photo every 5 min. Licence not verifiable because Vimeo showed a bot check — [Vimeo 30074251](https://vimeo.com/30074251)
- **Paid stock** (Getty, Adobe Stock, Envato): many bean and seed germination clips, all paid licences — [Getty bean germination](https://www.gettyimages.in/detail/video/time-lapse-of-germinating-bean-stock-footage/485018122)
- **Non-video salt-vs-water results:** a Gift of Curiosity home experiment (plain water sprouted all three seed types; salt water gave no sprouts) is written up, not filmed — [Gift of Curiosity](https://www.giftofcuriosity.com/seed-experiment-5-what-liquids-help-seeds-grow/)

### Inferences
- **Best legally clean demo options, ranked for Argus:**
  1. **Genze petri-dish dataset.** Fixed top-down camera, 12 vessels of known size and a ~30-minute interval, so time and scale are both known. Turn the frames into a video with ffmpeg. Use the species or cultivar split as the "conditions" (e.g. maize dishes vs rye dishes), or apply a hypothesis such as "maize germinates later than rye".
  2. **Brachypodium series.** Pick two movies with different regimes (e.g. temperature cycling vs constant), each showing multiple seedlings. They could be shown side by side with ffmpeg `hstack`, with the change noted for CC BY. This isn't strictly "one camera, one frame", but it's the same rig and lab.
  3. **Lima Bean (CC BY 3.0) or Mung bean (BY-SA).** Single-condition segmentation and growth demo only.
- No verified-CC video met the full brief (≥2+2 vessels, one frame, ruler). If a side-by-side treatment verdict is essential, the realistic paths are a permission request (UC Davis, or a YouTube school creator) or a short self-filmed cress or radish run. Cress or radish in a petri dish usually germinates in 1–3 days, so it's feasible before Nov 4 but tight.
- The Commons Open Access Media Importer convention (`<paper-title>-pone.XXXXXXX.s00N.ogv`) is a rich vein: every file is CC BY from PMC, scientifically designed, and often labelled with conditions. Searching Commons for `pone filetype:video seedling` or similar is worth the user's time.

### Gaps
- No verified-CC video was found showing salt vs fresh water, temperature, or fertiliser vs control side by side in one frame.
- Licences for the YouTube bread-mould videos, Wellspring Gardens, the UC Davis video and Kladnik's Vimeo clip couldn't be read. YouTube and Vimeo pages didn't render for the fetch tool.
- The Genze dataset's image resolution and total size aren't stated on the Mendeley page. I didn't confirm whether v3's "various seed cultivars" includes quality or treatment groups.
- The 17 other Brachypodium movies weren't opened individually, so which regimes each shows, and whether any includes a mutant vs wild type, is unconfirmed.

---

## 3. Which candidates show a ruler or known-size object?

### Takeaway
None of the verified candidates is documented to show a ruler. The Genze dataset gives a reliable known-size object: 85 mm petri dishes at a fixed ~40 cm camera height. Elsewhere, scale has to come from a known object such as a dish, seed size or pot, or be marked "uncalibrated".

### Cited Findings
- Genze et al.: 85 mm petri dishes in a 4×3 grid with a fixed top-down camera at ~40 cm — [Mendeley Data](https://data.mendeley.com/datasets/4wkt6thgp6)
- Brachypodium s004: no scale bar or ruler mentioned on the file page, though conditions are labelled in frame — [Commons](https://commons.wikimedia.org/wiki/File:Daily-Changes-in-Temperature-Not-the-Circadian-Clock-Regulate-Growth-Rate-in-Brachypodium-distachyon-pone.0100072.s004.ogv)
- NLP8 and Sizmur supplement pages mention no scale bar — [Commons NLP8](https://commons.wikimedia.org/wiki/File:NIN-like-protein-8-is-a-master-regulator-of-nitrate-promoted-seed-germination-in-Arabidopsis-ncomms13179-s4.ogv); [Commons Sizmur](https://commons.wikimedia.org/wiki/File:A-Simple-and-Versatile-2-Dimensional-Platform-to-Study-Plant-Germination-and-Growth-under-pone.0096730.s002.ogv)
- Several Commons files state their frame interval, which calibrates time:
  - Germinacion 2: 5 min
  - Germination of two little plants: 10 min
  - Lettuce: 30 s
  - Pea: 1 min, played at 20 fps
  - Lima bean: more than 1,600 photos over 6 days
  
  Source: [Commons API metadata](https://commons.wikimedia.org/wiki/File:Germinacion_2.webm)

### Inferences
- For Argus, a stated frame interval is as important as a ruler. Without it, growth rates can't be expressed per hour. Prefer candidates whose description gives the interval, and record it in the import metadata.
- Lima bean averages roughly 5.4 min per frame (6 days ≈ 8,640 min / ~1,600 photos). This is an estimate; the exact interval is unknown.
- Dish-based scale (85 or 90 mm Petri dish) works top-down. Side-on pot videos need a pot rim of known diameter or a ruler.

### Gaps
- I didn't visually inspect the frames of any candidate to look for rulers, grid paper or labels. The user should check by eye.

---

## 4. Practical: downloading legitimately, typical resolutions, and checking for a true fixed-camera timelapse

### Takeaway
Get files from the licence-holding source: Wikimedia Commons file pages (which host the original file), Mendeley Data, or the creator by email. YouTube's Terms forbid downloading except where expressly authorised or with permission, even for CC videos. Commons and dataset sources avoid that tension. Typical resolutions found range from 640×480 to 1920×1080, and one portrait file is 1630×2229.

### Cited Findings
- YouTube's Terms of Service prohibit downloading except "as expressly authorized by the Service" or "with prior written permission from YouTube" — [YouTube ToS](https://www.youtube.com/static?template=terms)
- Commons mirrors CC BY YouTube videos (e.g. Lima Bean, Borevitz Arabidopsis) as files with recorded provenance. Commons also notes that archived versions of the Lima Bean video exist at archive.org — [Commons Lima Bean](https://commons.wikimedia.org/wiki/File:Lima_Bean_Time_Lapse.webm)
- Commons offers a {{LicenseReview}} record and lists questionable YouTube channels, which helps confirm that a CC label is genuine — [Commons:YouTube files](https://commons.wikimedia.org/wiki/Commons:YouTube_files)
- Resolutions observed:
  - 1920×1080: Germinacion 2, Germination of two little plants
  - 1280×720: Lima Bean, Lettuce, Lentil, Brachypodium
  - 1080×810: Mung bean
  - 1080×720: Arabidopsis
  - 640×480: corn, wheat
  - 1630×2229: Pea
  
  Source: [Commons API metadata](https://commons.wikimedia.org/wiki/File:Mung_bean_germination.ogv)
- Commons and PMC-derived files are often Ogg Theora (.ogv) or WebM, e.g. Brachypodium is Ogg Theora at ~803 kbps — [Commons](https://commons.wikimedia.org/wiki/File:Daily-Changes-in-Temperature-Not-the-Circadian-Clock-Regulate-Growth-Rate-in-Brachypodium-distachyon-pone.0100072.s004.ogv)

### Inferences
- **On yt-dlp:** it is widely used, but downloading from YouTube conflicts with YouTube's ToS even when the video is CC BY. The CC licence covers copyright, not YouTube's access terms. Preferred order:
  1. Commons original file
  2. the journal or PMC supplementary file
  3. a file sent by the creator
  4. yt-dlp only for a video you have permission for, accepting the ToS risk
- **Ogg/WebM:** convert to MP4 with the ffmpeg CLI, which is already in the stack, before import. Theora at ~200–800 kbps is quite compressed, so expect block artefacts that may affect fine root-length measurement.
- **Checklist for a true fixed-camera timelapse (all automatable in Python/OpenCV):**
  1. **No cuts:** detect scene changes (e.g. ffmpeg `select='gt(scene,0.3)'`, or a frame-difference spike on the static background). There should be none, apart from intro and outro titles.
  2. **No camera motion:** phase correlation or ECC registration of a background patch (dish rim, tray edge) across frames should be ~0 px drift. A slow zoom or pan rules a video out.
  3. **Constant lighting:** track mean luminance of a background region. Day/night flicker is common; IR or constant-LED videos like Brachypodium are best. Flicker is fixable by per-frame normalisation, but must be logged.
  4. **Known interval:** the description should state it; otherwise frame count over stated duration gives an average only.
  5. **Clean frame:** no music-only cuts, captions or watermarks over the vessels. Lentil, for example, has music.
  6. **Vessel layout:** ≥2 vessels per condition, all in one frame, top-down or orthogonal side-on.
  7. **Resolution:** ≥720p, and ideally ≥40 px across each seedling, for SAM masks.
  8. **Duration:** must cover the change (radicle emergence → seedling).

### Gaps
- I didn't look up yt-dlp documentation or the legal status of ripping tools.
- I didn't verify whether Commons offers MP4 transcodes for every file. The NLP8 page listed VP9 240p and MP4 360p transcodes, but the originals are what matter.

---

## 5. Search phrases (YouTube, Commons, Vimeo, stock sites, universities) and what to look for

### Takeaway
Combine an experiment phrase with a licence filter: YouTube Filters → Features → Creative Commons, Commons `filetype:video`, Vimeo CC browse, or the stock-site search. Add non-English school-experiment phrasing to surface classroom comparisons. Accept a hit only if it passes the checklist in section 4.

### Cited Findings
- YouTube supports a "Creative Commons" search filter — [YouTube Help](https://support.google.com/youtube/answer/2797468?hl=en)
- Commons suggests Vera's Tool and the SearchFreeMedia gadget for finding open-licensed YouTube videos per channel. For Shorts, change the URL to `youtube.com/watch?v=ID` to see the licence — [Commons:YouTube files](https://commons.wikimedia.org/wiki/Commons:YouTube_files)
- Commons MediaSearch and the API support `filetype:video` with a keyword, and returned 69 hits for "germination" — [Commons MediaSearch](https://commons.wikimedia.org/w/index.php?search=germination+filetype%3Avideo&title=Special:MediaSearch&type=video)
- Vimeo CC can be browsed by licence (BY, BY-SA, etc.) — [Vimeo CC](https://vimeo.com/creativecommons)

### Inferences (recommended search phrases; constructed for this task, not tested one by one)

**YouTube (apply Filters → Features → Creative Commons first, then repeat without it to find permission targets)**

*Germination, treatment vs control*
1. `seed germination salt water vs tap water time lapse`
2. `salinity stress germination timelapse petri dish`
3. `NaCl seed germination experiment time lapse control`
4. `radish seeds salt concentration germination timelapse`
5. `cress germination salt experiment time lapse`
6. `seed germination different temperatures time lapse`
7. `germination cold vs warm timelapse`
8. `mung bean germination light vs dark time lapse`
9. `plants with and without fertilizer time lapse`
10. `allelopathy germination time lapse` (seed germination inhibited by extracts)
11. `germination test petri dish time lapse lab`
12. `seed vigor test time lapse petri dishes`
13. `phototropism time lapse seedlings`

*Other slow experiments*

14. `bread mold time lapse comparison` / `bread mould effect of water time lapse`
15. `mold growth different conditions time lapse`
16. `yeast balloon experiment time lapse sugar`
17. `yeast fermentation sugar concentration time lapse`
18. `fruit ripening ethylene banana time lapse comparison`
19. `apple browning lemon juice time lapse`

**Wikimedia Commons** (search box or `Special:MediaSearch`, type = video)

20. `germination filetype:video`
21. `seedlings filetype:video`
22. `incategory:"Time-lapse_videos_of_plants"`
23. `pone filetype:video seedling` (PLOS ONE supplements, all CC BY)
24. `time-lapse Arabidopsis filetype:video growth`
25. `mould OR mold time-lapse filetype:video`

**Vimeo** (vimeo.com/creativecommons → Attribution → search)

26. `germination timelapse`
27. `seedlings time lapse experiment`

**Pexels / Pixabay / Videvo** (stock: usable in the demo, but don't commit raw files)

28. `seed germination time lapse`
29. `sprouting beans timelapse`
30. `seedlings growing petri dish`
31. `mold timelapse`

**University and science sites** (web search; usually permission needed)

32. `site:video.ucdavis.edu germination temperature`
33. `site:edu germination time lapse treatment control`
34. `plant phenotyping time lapse salt stress video supplementary`
35. `"S1 Movie" germination time-lapse` (PLOS supplements on journals or PMC)

**Non-English** (school and university experiments)

- Spanish:
  - `germinación de semillas agua salada experimento timelapse`
  - `germinación frijol control y tratamiento time lapse`
  - `germinación semillas distintas temperaturas`
  - `moho en el pan timelapse experimento`
- German:
  - `Keimung Zeitraffer Salzwasser Kresse`
  - `Keimversuch Kontrolle Zeitraffer`
  - `Kresse Keimung Temperatur Versuch`
  - `Schimmel Brot Zeitraffer Versuch`
- French:
  - `germination graines eau salée expérience accéléré`
  - `expérience germination témoin time lapse`
  - `germination lentilles accéléré`
  - `moisissure pain time lapse expérience`
- Arabic:
  - `تجربة إنبات البذور بالماء المالح`
  - `إنبات البذور تايم لابس`
  - `تجربة الإنبات مجموعة ضابطة`
- Portuguese:
  - `germinação de sementes água salgada experimento timelapse`
- Italian:
  - `germinazione semi acqua salata esperimento timelapse`
- Japanese:
  - `発芽 タイムラプス 塩水 実験`
- Chinese:
  - `种子发芽 延时摄影 盐水 对照`

**What to look for in a candidate (quick screen before deeper checks)**
- **Licence:** CC BY or CC BY-SA shown under the description, or a Commons file page. Otherwise, mark it "ask permission".
- **Fixed camera:** no zoom, pan or cuts; the background stays still.
- **Constant lighting:** LED or IR, little day/night flicker.
- **Layout:** ≥2 vessels per condition in one frame, with conditions labelled on vessels or in the description.
- **Scale and time:** a ruler, grid paper or known-size dish in frame, and a stated frame interval.
- **Quality:** ≥720p (1080p preferred); no music-only edits, captions or watermarks over the vessels.
- **Duration:** covers the full change, e.g. radicle emergence for germination.
- **Uploader:** credible (lab, college or educator) and not a reupload. Check Commons' questionable-channel list for license laundering.

### Gaps
- The phrases weren't run one by one on YouTube, because the fetch tool can't render YouTube results. Yield is unknown.
- The commonly used YouTube CC filter URL parameter (`&sp=EgIwAQ%253D%253D`) was tried but the page didn't render, so it's unverified here. Use the Filters menu in the browser instead.
