# Lead Argus's demo with a chemical clock

The strongest honest line-up puts a **household vitamin C iodine clock** at the centre of the video. That one experiment can be the opening hook, the hero live run, the multi-round Ax loop and the X clip. A peer-reviewed kitchen recipe already shows the clear-to-blue-black switch moving from **about 46 s to 227 s across five vitamin C doses, with replicate pairs only 5–15 % apart**. The clock runs at room temperature with supermarket chemicals, fits three Ax rounds into one afternoon and needs no card, because its response is a time. Three things go around it: a **yeast foam tower race with a disclosed warm spot** gives the "caught a rival" moment and an honest Inconclusive; the **salt-stress mung-bean run** is the labelled long replay, or, if it is not recording by tonight, the CC BY 4.0 Genze petri-dish dataset; and **public-domain and CC BY footage** adds B-roll from other fields (NASA's 1080p pepper timelapse from the space station, Futo's biofilm videos with a 1 cm scale bar, CC BY germination clips on Commons). **Drop water beads.** They make the prettiest growth timelapse, but the US Consumer Product Safety Commission (CPSC) has tied them to about **7,000 emergency-room visits in 2018–2022** and an infant's death, and has warned about acrylamide in one brand. That is poor optics for a tool pitched to students and teachers and pushed in a viral clip. Mould, strong peroxide, chemical gardens and the *S. aureus* ColTapp plates fail the same safety screen. To show breadth across fields, the only open dataset found with a numeric dose, untreated controls and replicates from one rig is a **zebrafish inhibitor timelapse from Konstanz (CC BY 4.0)**: a stretch goal for after the core is filmed. Professional looks come from **locking everything that could change**. Grading, deflicker and stabilisation touch only a presentation copy, never the frames Argus measures. The schedule: shopping and pilots Oct 29–30, the Ax loop Oct 31, the rival run Nov 1, screen recording Nov 2, editing Nov 3, and submission plus the X post on Nov 4.

## A vitamin C clock does four jobs in one afternoon

Of all the desk experiments considered, only the household iodine clock is fast, sharp to look at, measurable without a card and already backed by replicated published numbers. Kerr, Thomson and Smith built it from kitchen supplies: one 1000 mg vitamin C tablet dissolved in 30–120 ml of water, 3 % Lugol's iodine, 3 % hydrogen peroxide and powdered laundry starch. They timed the clear-to-blue-black switch twice at each level ([Kerr et al. 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6502385/)). Vitamin C turns iodine back into iodide faster than peroxide can make it, so each cup stays clear until its vitamin C runs out, then turns dark all at once. Across five vitamin C strengths the switch went from **48.1/43.6 s to 243.7/210.9 s**. Across five iodine volumes it fell from **427.0/495.8 s to 19.5/22.6 s** ([Kerr et al. 2019, Table 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC6502385/)). By my arithmetic, the dose means are 45.8, 71.5, 119.6, 160.6 and 227.3 s. Adjacent doses sit 26–67 s apart, while replicate pairs differ by about 5–15 %. A hypothesis that "more vitamin C delays the switch", tested with two cups per dose, should therefore reach a clean SUPPORTED, far above the 3× noise-floor bar. A supermarket version with 2 % iodine tincture and liquid laundry starch was published in *J. Chem. Educ.* in 2002 ([Wright 2002](https://diverdi.colostate.edu/C431/experiments/simultaneous%20spectroscopy%20and%20electrochemistry/references/j_chem_ed_2002_v79_p40a.pdf)). A 2024 model adds peroxide concentration as a third factor ([Alsaleh et al.](https://arxiv.org/abs/2408.04108)).

The same data makes the Ax loop a real optimisation, not a straight-line fit. A fourfold increase in iodine cut the switch time about **22-fold** (my arithmetic from Table 1). The authors' approximate law, t_sw ≈ (c0 − ϕm0)/(m0²k0) with **k0 ≈ 0.57 M⁻¹s⁻¹**, makes the time roughly proportional to vitamin C and inversely proportional to iodine squared ([Kerr et al. 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6502385/)). Set the objective as "switch closest to 60 s", optionally "using the least iodine", over vitamin C stock volume and Lugol's volume at five levels each. That gives Ax a curved surface to search, and 60 s falls inside Kerr's tested range, between the two most dilute vitamin C stocks at 5 ml iodine. A round takes under ten minutes to pour and run, so three rounds (about 30 cups) fit one afternoon, and the payoff is simple: Argus aimed for 60 s and the cup went dark at the measured time. For a technical-depth moment, Argus fits the c0/m0² law to its own cups in Python and shows the same shape as the published model. The constant will not match, because tincture instead of Lugol's and room temperature instead of Kerr's 40 °C water both shift it, and the video should say so. Kerr's Dryad deposit (Excel results and Matlab code, described as "licensed for reuse") supplies reference numbers, not footage ([Dryad](https://datadryad.org/stash/dataset/doi:10.5061/dryad.68q4hf7)).

The verdict rules need controls and at least two replicates per condition, so the middle dose serves as the reference condition. Add two **negative-control cups with water in place of peroxide**. By the reaction's mechanism these should never turn (my chemistry reasoning; confirm it in the pilot), which shows on camera that the reaction causes the switch, not light or elapsed time. Twelve cups stay under the 16-object cap that SAM 3.1's video mode hit in Argus's own probe ([KB 04](../knowledge-base/04-models-and-api.md)). The practical failure points are known in advance:

- **Start times.** Cups are poured one at a time, so each needs its own start time: a liquid-level jump in a side view, backed by a voice note.
- **Stirring** must be identical in every cup.
- **Temperature** changes the rate, and Kerr lists it as untested future work, so every cup should take water from one jug at room temperature, with that temperature logged.
- **Tablets.** Chewable or orange tablets add colour; use plain white ones.
- **Starch** should be liquid or powdered laundry starch; boiled cornstarch adds heat.
- **The threshold** belongs on the whole-cup mean, because colour can creep down from the surface.

The experiment needs no flame, heat or pressure, and the chemicals are household strength. Iodine stains and is harmful if swallowed, so gloves, glasses and a "not for drinking" label belong in the wizard's safety note. Never stage a rival inside the Ax rounds: one confounded round would make the optimiser look broken.

Against the other candidates, the clock wins on the combination of strengths, not on any single one.

| Experiment | Time per run | Numeric factor (3+ levels) | Published reference | Open footage or data | Best role | Likely verdict |
|---|---|---|---|---|---|---|
| **Vitamin C iodine clock** | 20 s – 8 min | Vitamin C stock, iodine volume | Replicated table ([Kerr 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6502385/)) | Dryad Excel only, no video | Hook, live run, Ax loop, X clip | Clean SUPPORTED |
| **Yeast foam towers vs sugar** | 20–60 min | Sugar g per 100 ml | Direction only; a peak is disputed ([Serendip](https://serendipstudio.org/exchange/comment/reply/3706/144486)) | None | Rival catch, Inconclusive | Mixed by design |
| **Mung-bean salt germination** | 48–72 h | Salt g/L | Own protocol ([KB 20](../knowledge-base/20-demo-experiment-germination.md)) | Genze, ChronoRoot as fallbacks | Long replay | Probably clean; one Ax round |
| Effervescent tablet vs water temperature | 20 s – 5 min | Water °C | 130 s at 2.8 °C to 21 s at 42.2 °C ([Waterloo](https://uwaterloo.ca/centre-advanced-science-education/news/chemistry-alka-seltzer)) | None | Backup fast loop | Clean |
| Apple browning vs ascorbic acid | 2–6 h | Ascorbic acid % | ΔE 2.38 → 4.05 in 60 min ([Foods 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7022590/)) | CC BY-SA single apple on [Commons](https://commons.wikimedia.org/wiki/File:Browning_Fuji_apple_-_32_minutes_in_16_seconds.webm) | Backup Inconclusive | Clean at high dose only |
| Dough rise vs sugar or yeast | 2–6 h | Sugar or yeast % | 0.1–1.5 mm/h in tubes ([eLife](https://elifesciences.org/articles/61644)) | eLife source data, licence unconfirmed | Optional overnight B-roll | Unknown |
| Water beads vs NaCl | Hours | NaCl % | 146 vs 43.5 g/g ([US 6072101](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6072101)) | None | **Dropped (safety optics)** | — |
| Elephant toothpaste, 3 % peroxide | Seconds | Yeast amount | Qualitative only | None | 2 s spectacle at most | Weak |
| Ice melt, rust, Skittles, celery | 10 min – 6 h | Salt or temperature | Classroom reports, no replicated timings | None | Skip | Unknown |
| Crystals, chemical gardens, slime mould | Days, or hazardous | — | — | — | Skip | — |

The chemistry notes ranked the effervescent tablet first for live speed, and its numbers are good. The Waterloo classroom series gives an activation energy of about **29 kJ/mol** ([Waterloo CASE](https://uwaterloo.ca/centre-advanced-science-education/news/chemistry-alka-seltzer)). It loses to the clock as an Ax vehicle for four reasons:

- Its factor is temperature, which each cup loses while it sits.
- Argus cannot read temperature, so every cup needs a thermometer note from the researcher.
- Foam hides the shrinking tablet.
- A suggestion like "31.4 °C" is hard to mix exactly, while the clock's factors are volumes measured by syringe.

Keep the tablet as the fallback if the pilot clock misbehaves. The yeast towers are, in principle, the textbook Bayesian-optimisation case, because sugar may raise CO₂ up to about 10 % and lower it beyond that through osmotic stress ([Serendip](https://serendipstudio.org/exchange/comment/reply/3706/144486)). Student studies disagree on where the peak sits ([OSU JIBI](https://undergradsciencejournals.okstate.edu/index.php/jibi/article/view/6163)), and rounds of 20–60 minutes with collapsing foam would make three rounds a full day. Yeast is better used for the rival.

## A disclosed warm spot and a seed run supply the honesty

The most convincing "caught a rival" moment is a position effect that hits the controls too, and it is visible only because the layout was randomised. Use six to eight identical tall glasses of yeast, sugar and a drop of dish soap at several sugar levels, two glasses each, placed in a randomised order. Then warm one end of the row on purpose. If the warm-end glasses of every dose, controls included, rise faster, Argus can say the effect follows position, not dose, and return INCONCLUSIVE with "rival: warm spot (position)". A desk lamp is the obvious heater, but it also brightens one side of the frame and so confounds the camera as well as the yeast. An out-of-frame heating pad on low under one end warms without changing the light (my inference). No source quantifies how much such a heater warms a glass, so run a 20-minute pilot with a kitchen thermometer. Water temperature dominates yeast activity: fill every glass from one jug and log its temperature. The video must say the warm spot was deliberate. Presenting a staged rival as an accident would be exactly the kind of invented evidence Argus's rules forbid, while saying "I randomised the glasses, then cheated on one end; watch Argus refuse the win" makes the scientific point out loud.

The other honest beats come almost free:

- **TOO_EARLY turning into a verdict.** A live clock or yeast run shows a provisional TOO_EARLY for its first minutes and resolves on screen, demonstrating the provisional verdict updating.
- **The claim checker** striking out a wrong AI number is the strongest proof that models only interpret.
- **Apple browning as a backup.** Golden Delicious ΔE rose only from **2.38 to 4.05 in the first hour**, and citric acid had **no significant effect** ([Shrestha et al., Foods 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7022590/)). Lemon juice is therefore a weak treatment, since citric acid is about 95 % of its acid ([UBC Expedition](https://ojs.library.ubc.ca/index.php/expedition/article/view/197341/192115)). A dissolved vitamin C series is the cleaner choice. A low dose against water after two hours is a natural, unforced INCONCLUSIVE, and switching on a room light mid-run shows the card's neutral patch jumping and colour correction removing most of it.

The long replay depends on one fact: whether the salt run is recording. The planned run uses six jars with three salt levels × two replicates, filmed side-on by the Canon XA50 at ×600 with the Argus Card in the plane of the jar fronts ([KB 20](../knowledge-base/20-demo-experiment-germination.md)). It is the only long run that can show a dose-response and a real next-salt-levels suggestion. Mung beans sprout within about a day, so a 48–72 h run started tonight ends Oct 31 – Nov 1. If it cannot start tonight, switch to the **Genze & Grimm dataset**: 247 top-down 85 mm dishes of maize, rye and pearl millet, photographed every 30 minutes for about 48 hours, with a human-drawn germinated/not-germinated box on every seed in every frame. It is CC BY 4.0 and comes as one **840 MB zip with a no-login link** ([Mendeley Data](https://data.mendeley.com/datasets/4wkt6thgp6/3); [direct file](https://data.mendeley.com/public-files/datasets/4wkt6thgp6/files/4ab46f9f-b34f-4112-a4be-0f3d6c459cf4/file_downloaded); [Genze et al. 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7754596/)). Its conditions are species, not salt, so the hypothesis must compare species, and the per-seed boxes let Argus publish a real accuracy figure. Since Argus accepts a plan only if it was locked before the run began ([KB 15, D-67](../knowledge-base/15-decisions-log.md)), lock the species plan before importing and label the verdict a **retrospective re-analysis of published data**. That label is itself a rigour moment. Genze needs four builds if they do not exist yet:

- an image-sequence importer that keeps timestamps and a source record (URL, DOI, licence, credit line);
- a dish-as-ruler scale;
- a relative pixel mode;
- a ground-truth comparison stored as its own record.

ChronoRoot's CC0 infrared plates can check scale, because their published resolution is about 0.04 mm/px ([HF card](https://huggingface.co/datasets/ngaggion/UnsupervisedRootVideos); [ChronoRoot 2.0](https://arxiv.org/html/2504.14736v2)). Their plate-to-condition key is unpublished, so they cannot carry a verdict.

## Water beads and pathogen plates fail the safety screen

The notes disagree on water beads, and the disagreement is about optics, not physics. The case for them is strong. Sodium polyacrylate took up **146.2 g/g in deionised water versus 43.5 g/g in 0.9 % saline** in patent data ([US 6072101](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6072101)), which works out to about 1.5× the diameter and 2.2× the projected area (my geometry). Salt reverses the swelling ([Carnegie Mellon](https://www.cmu.edu/gelfand/k12-educational-resources/polymers/polymer-and-absorption/super-absorb-powder.html)), and early uptake follows a power law that Argus could fit on screen ([arXiv 1605.00599](https://arxiv.org/pdf/1605.00599)). The case against is stronger:

- The CPSC counted about **7,000 ER visits for water-bead ingestion in 2018–2022**, and a 10-month-old died in 2023 ([Yahoo News/CPSC](https://news.yahoo.com/water-beads-pose-huge-safety-203806111.html); [NBC News](https://www.nbcnews.com/health/kids-health/health-warning-water-bead-toys-danger-rcna144152)).
- In March 2024 the CPSC told consumers to stop using one Amazon-sold brand because of acrylamide above federal limits ([CPSC](https://www.cpsc.gov/Warnings/2024/CPSC-Warns-Consumers-to-Immediately-Stop-Using-Jangostor-Water-Beads-Due-to-Chemical-Toxicity-Hazard-Violation-of-Federal-Ban-of-Hazardous-Substances-Sold-on-Amazon-com)).
- A Ban Water Beads Act was introduced in November 2023 ([Denver7](https://www.denver7.com/news/national/federal-action-on-water-bead-safety-expected-in-2024-following-safety-concerns-for-children)), and major retailers said they would stop selling beads marketed to children ([AARP](https://www.aarp.org/health/conditions-treatments/info-2023/water-beads-recall-warning.html)).

Argus's rule 8 names flame, strong heat, pressure, hazardous chemicals and pathogens, not ingestion hazards, so water beads break no written rule. But the pitch names students and teachers as users, and the Most Viral clip would reach parents. A judge or commenter who knows the warnings would read the beads as a lapse in exactly the safety judgement the wizard advertises. They also measure badly: swollen clear beads nearly vanish in water because their refractive index approaches water's, beads touching each other merge into one mask, and the growth-time figures come from low-quality pages. **Decision: leave them out**, including from the X clip. Yeast towers and germination deliver the "watch it grow" visual without that baggage.

The same screen applied to every candidate gives a short list of exclusions. Argus only watches, so re-analysing someone else's flame or culture footage breaks no hardware rule. The line-up still avoids pathogen footage, because a public video of an AI suggesting the "next run" on a pathogen culture contradicts the stance Argus is selling.

| Candidate | Rule or risk touched | Decision |
|---|---|---|
| Water beads | Ingestion hazard, CPSC warnings (above) | Drop |
| Elephant toothpaste with 12 % peroxide ([CYSF](https://platform.cysf.org/project/65a59d7c-9096-436a-abab-3d56f0ddbd6f/)) | Hazardous chemical | Exclude; 3 % household peroxide only |
| Chemical gardens | Sodium silicate is corrosive; nickel and cobalt salts are carcinogenic sensitisers ([RSC](https://edu.rsc.org/download?ac=15257)) | Exclude at home; no licensed footage found |
| Copper sulfate or borax crystals | Toxicity unverified; take days | Exclude |
| Effervescent tablets in hot water | Strong heat | Warm tap water at or below about 45 °C only; no kettle-hot water |
| Vitamin C clock | Mild household chemicals; Kerr used 40 °C water | Room temperature, gloves, "not for drinking" |
| Yeast towers | Pressure, only if sealed | Open glasses only |
| Home bread mould | Allergenic spores (general knowledge, not sourced here) | Exclude |
| ColTapp *S. aureus* plates on blood agar ([PMC7528005](https://pmc.ncbi.nlm.nih.gov/articles/PMC7528005/)) | Pathogen | Exclude, even though the data are CC BY 4.0 |
| *P. aeruginosa* swarm videos ([JoVE](https://www.jove.com/t/60915)) | Pathogen | Exclude |
| *B. subtilis* biofilms and swarms | Low-risk lab organism | Allowed as published footage |
| NASA 1g vs microgravity candle flame ([NASA](https://www.nasa.gov/image-article/candle-flame-1g-vs-microgravity/)) | Flame, watch-only | Allowed but weak (stills only) |
| Wound-healing cells, zebrafish embryos | Medical-advice optics | Allowed, framed as lab research only |

## Published footage stretches Argus to embryos, cells and space plants

No openly licensed timelapse of the kitchen experiments turned up. A Commons search for crystal, rust, chemical-garden, dough, water-bead, celery and ice-melt timelapses returned 33 files, mostly NASA and CIRA sea-ice animations plus two micro-scale freezing clips ([Commons API](https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch=time-lapse%20crystal%20OR%20rust%20OR%20%22chemical%20garden%22%20OR%20dough%20OR%20%22water%20beads%22%20OR%20celery%20OR%20%22ice%20melting%22%20filetype:video&srnamespace=6&srlimit=50&format=json)). A search for "time-lapse control treatment" returned about 40 journal supplements, almost all cell microscopy ([Commons MediaSearch](https://commons.wikimedia.org/w/index.php?search=time-lapse+control+treatment+filetype%3Avideo&title=Special:MediaSearch&type=video)). Home experiments must therefore be self-filmed, which also fits the hackathon's new-work rule: raw footage may be recorded early, but every analysis shown must come from hackathon code ([KB 01](../knowledge-base/01-hackathon-rules-and-dates.md)). Published footage earns its place in two other ways. It shows that one engine works across fields, and it supplies independent scales and labels to validate against.

| Source | Field and content | Design fit | Scale without a card | Licence | Download | Role |
|---|---|---|---|---|---|---|
| **Konstanz TwinNetworkDataset033** ([B2FIND](https://b2find.eudat.eu/dataset/c5af9e57-60e2-5e0f-92f6-7b5f92a5ae17)) | Zebrafish embryos, 2–26 hours post-fertilisation, 720 frames at 2 min; LDN-193189 at 0, 3.5, 4, 12 µM; SB-505124 at 5, 6 µM | Controls n = 2, doses n = 2–6: verdict and Ax both possible | Not stated, so relative | CC BY 4.0 | tar of unknown size | Stretch re-analysis |
| **Zaritsky wound healing** ([PMC4341232](https://pmc.ncbi.nlm.nih.gov/articles/PMC4341232/)) | 31 scratch-closure movies; DA3 control 6, +HGF 5, PHA 4, PHA+HGF 6 | Strong replicates, categorical factors: verdict but no Ax | In unopened supplementary files | Data CC0 | Cell Image Library; per-image terms to check | Alternative re-analysis |
| **C. elegans dose plates** ([Zenodo 4673706](https://zenodo.org/record/4673706)) | 6 doses plus 2 control types × 4 wells; 16 wells per camera, 25 fps | Dose series, but the readout is motility (needs a new metric) | 12.4 µm/px published | CC BY 4.0 | 3.8 GB zip; may hold tracker output, not video | Stretch |
| **Danforth Setaria** ([Danforth](https://datasci.danforthcenter.org/data/)) | Water-limited vs well-watered plants, 79,200 images | Many replicates; one plant per image is likely, so a labelled mosaic | Camera zoom calibration file | CC BY 4.0 | 4.4 GB JPG over HTTP | Alternative long re-analysis |
| **Genze & Grimm** ([Mendeley](https://data.mendeley.com/datasets/4wkt6thgp6/3)) | 247 germination dishes, 30 min, 48 h | Species as conditions, per-seed ground truth | 85 mm dish rim | CC BY 4.0 | 840 MB, no login | Long-run fallback |
| **Futo et al. biofilms** ([PMC9729682](https://pmc.ncbi.nlm.nih.gov/articles/PMC9729682/)) | *B. subtilis* macrocolonies, 6-min frames, 3–21 days, 1080p | Strains, not treatments; 3 replicates of one strain | 1 cm scale bar | CC BY 4.0 | FigShare plus private YouTube links | B-roll measured in mm |
| **Grobas et al. swarm** ([eLife 62632](https://elifesciences.org/articles/62632/figures)) | Swarm front halting at a kanamycin disk; 30, 100, 200 µg | One video per condition | Not stated | CC BY 4.0 | eLife figure videos | Honest "n = 1, no verdict" beat |
| **NASA PH-04 peppers** ([metadata](https://images-assets.nasa.gov/video/Peppers%20Timelapse%20Longe%20Rev%207/metadata.json)) | Chile peppers growing on the space station, 59 s, 1920×1080 | No control in frame | Relative only | Public domain; credit NASA | Direct 135 MiB MP4 ([manifest](https://images-api.nasa.gov/asset/Peppers%20Timelapse%20Longe%20Rev%207)) | Hook or B-roll |
| **Brachypodium movies** ([Commons](https://commons.wikimedia.org/wiki/File:Daily-Changes-in-Temperature-Not-the-Circadian-Clock-Regulate-Growth-Rate-in-Brachypodium-distachyon-pone.0100072.s004.ogv)) | Infrared seedlings under switching temperature regimes, labelled in frame | Within-subject changepoint | None | CC BY 4.0 | 2 MB | Changepoint B-roll |
| **Commons germination clips** ([lima bean](https://commons.wikimedia.org/wiki/File:Lima_Bean_Time_Lapse.webm), [lettuce](https://commons.wikimedia.org/wiki/File:Timelapse_of_lettuce_emerging.webm)) | Single-condition sprouting | No replicates | None | CC BY 3.0 / 2.0 | 5–63 MB | Cinematic B-roll |
| **BBBC019** ([Broad](https://bbbc.broadinstitute.org/BBBC019)) | Scratch-assay images with manual masks | Validation, not a run | µm/px per set | CC BY 3.0 | 1.5–50.9 MB zips | Computed SAM-vs-human overlap slide |
| **Ripen Banana** ([Mendeley](https://data.mendeley.com/datasets/j9sp322drp/1)) | 4 carbide-treated vs 4 control bananas, every 2 h for 7 days, phone camera | Replicated colour change | None | CC BY 4.0 | Mendeley | Colour backup |
| MEGA-plate ([Commons](https://commons.wikimedia.org/wiki/File:Kishony_lab-The_Evolution_of_Bacteria_on_a_Mega-Plate.webm)) | Bacteria crossing antibiotic bands over 11.7 days | Spectacle | Plate dimensions only | CC BY-SA 3.0 | 7 MB | Unmodified clip at most |
| NASA PH-07 lettuce stills ([metadata](https://images-assets.nasa.gov/image/jsc2025e047409/metadata.json)) | Control, flood, drought and wilt side by side | Three stills | — | Techshot copyright | — | Avoid without permission |

The zebrafish set is the only one found with a numeric dose, untreated controls and replicates from a single rig under an open licence, so it is the best candidate for a breadth re-analysis that ends in a real verdict and an Ax suggestion on someone else's data. Its unknowns must be checked today, before any work starts: the tar size, the µm per pixel, the embryos per well and whether the RADAR repository allows partial downloads ([B2FIND](https://b2find.eudat.eu/dataset/c5af9e57-60e2-5e0f-92f6-7b5f92a5ae17); [DOI 10.48606/91](https://doi.org/10.48606/91)). The textbook expectation that BMP inhibition dorsalises embryos is a hypothesis for Argus to judge, not a known result for this dataset. Zaritsky's wound movies have the cleanest licence and 4–6 replicates per condition, but only categorical factors, so Argus could at most propose an HGF dose series. A 2024 study found that SAM with point prompts segments scratch wounds about as consistently as experts ([arXiv 2407.02187](https://arxiv.org/abs/2407.02187)). The cheapest strong moment is Grobas's swarm: the footage is beautiful, there is one video per condition, and Argus declining a verdict on n = 1 shows its rigour in five seconds.

Licences decide what reaches the video and the repo:

- **NASA** imagery is generally not subject to US copyright, but NASA should be credited, its insignia is not public domain and endorsement must not be implied ([NASA guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/)).
- **ESA** material is CC BY-SA 3.0 IGO only where a page says so ([ESA](https://www.esa.int/ESA_Multimedia/Copyright_Notice_Images)).
- **Open University** material is BY-NC-SA "wherever possible" ([OU policy](https://university.open.ac.uk/open-educational-resources/home/open-educational-resources-operating-policy)), and non-commercial terms are risky for a prize event.
- **YouTube** gives every upload its Standard licence unless the creator picks CC BY ([YouTube Help](https://support.google.com/youtube/answer/2797468?hl=en)), and its Terms forbid downloading except where expressly allowed ([YouTube ToS](https://www.youtube.com/static?template=terms)). Get CC BY YouTube videos from their Commons mirrors instead, which record provenance and run a licence review ([Commons:YouTube files](https://commons.wikimedia.org/wiki/Commons:YouTube_files)).
- **CC BY-SA** footage with Argus overlays arguably becomes an adaptation, which would put the whole demo under share-alike.
- **Fair use** has no safe percentage ([US Copyright Office](https://www.copyright.gov/fair-use/more-info.html)).

Three rules follow. Keep third-party files out of the public repo and fetch them by script. Credit each clip on screen and in the description, as Creative Commons recommends for video ([CC wiki](https://wiki.creativecommons.org/wiki/Recommended_practices_for_attribution)), with a line such as `"<Title>" by <Author>, <URL or DOI>, CC BY 4.0; cropped and annotated with Argus measurements`. Label every imported clip "re-analysis of published data". Pexels and Pixabay clips may appear in the video without credit, but their terms bar redistributing them unchanged, so they stay out of the repo too ([Pixabay](https://pixabay.com/service/license-summary/); [Pexels](https://www.pexels.com/license/)).

### Search phrases that surface more footage

Only the NASA and Commons queries marked "run" were actually executed. The rest are constructed and untested, because the research tools could not render YouTube or Vimeo results.

| Where | Paste this | Targets | Status |
|---|---|---|---|
| images.nasa.gov | `time-lapse plants` | Space-station plant timelapses (found PH-04) | Run |
| images.nasa.gov | `plant habitat ground control` | Ground-control radish and pepper material | Run |
| images.nasa.gov | `Veggie time-lapse` | Other space-station plant runs | Constructed |
| Commons MediaSearch, type video | `time-lapse control treatment filetype:video` | Journal supplements (mostly microscopy) | Run |
| Commons | `incategory:"Time-lapse_videos_of_plants"` | 70 plant, decay and ripening clips | Run |
| Commons | `pone filetype:video time-lapse` | PLOS ONE supplements, all CC BY | Constructed |
| Commons | `ncomms filetype:video time-lapse` | Nature Communications supplements | Constructed |
| Zenodo, open access | `time-lapse dose response video` | Dose screens in worms, cells, fish | Constructed |
| Zenodo | `Tierpsy 96-well` | More Brown-lab worm plates | Constructed |
| B2FIND | `TwinNetworkDataset` and `EmbryoNet Acquifer` | Konstanz zebrafish sets | Constructed from records found |
| figshare, Dryad | `timelapse agar plate colonies treatment` | Colony growth with conditions | Constructed |
| YouTube, Filters → Creative Commons | `iodine clock reaction vitamin C time lapse` | Clock footage | Constructed |
| YouTube, CC filter | `yeast foam sugar experiment time lapse` | Foam races | Constructed |
| YouTube, CC filter | `alka seltzer water temperature experiment` | Effervescent series | Constructed |
| YouTube, CC filter | `apple browning lemon juice time lapse` | Browning with a control | Constructed |
| YouTube, CC filter | `seed germination salt water vs tap water time lapse` | Salt vs control germination | Constructed |
| YouTube, CC filter | `reacción reloj de yodo vitamina C` / `réaction horloge iode vitamine C` | Spanish and French school demos | Constructed |
| Vimeo, Creative Commons → Attribution | `timelapse experiment control` | Semi-professional CC footage | Constructed |

Keep a hit only if it passes eight checks:

- a fixed camera with no zoom, pan or cuts;
- steady LED or infrared light;
- at least two vessels per condition in one frame, with the conditions named;
- a stated frame interval;
- a dish, ruler or scale bar of known size;
- 720p or better;
- no captions or watermarks over the vessels;
- an uploader who plausibly owns the footage.

## Most of the line-up can drop the printed card

The only cardless route to roughly 1 % scale error is a known object in the measured plane. Everything else is either a ratio or a guess. Automatic ruler reading has only recently become reliable: RulerNet reaches **1.19 % and 1.31 %** mean error on two benchmarks, against 14.79–62.11 % for classic tick-frequency reading, but its code and weights carry no licence yet ([RulerNet](https://arxiv.org/html/2507.07077)). A petri dish is a ±3–5 % ruler once maker spread is counted: SPL's "90 mm" lid measures **92.40 mm** ([SPL](https://www.n-genetics.com/files/co/Documents/technicaldata/spl_19477.pdf)), and one glass dish's base is 84 mm against a 90 mm lid ([Findel](https://findel-international.com/product/science/biology/microbiology/glass-petri-dish-90x15mm-pack-of-10/e8a77215)), before allowing for contents sitting below the rim. Monocular depth models are unfit for verdicts. On a benchmark built around transparent and reflective objects, only **27.6–46.6 % of pixels** fall within 25 % of true depth for UniDepth, Metric3D v2 and Depth Pro ([Depth Pro paper](https://arxiv.org/html/2410.02073)). Global white-balance tricks miss by **11.25° (grey-world) to 19.01° (max-RGB)** at the 95th percentile ([UEA benchmark](https://colour.cmp.uea.ac.uk/datasets/illuminant-estimation-errors.html)). Pixel units are normal practice: RhizoVision reports pixels unless the user supplies a pixel size ([Zenodo 7825935](https://zenodo.org/records/7825935)), and ImageJ sets scale from a line drawn over a known distance ([ImageJ](https://imagej.net/ij/docs/menus/analyze.html)).

| Line-up item | Cardless source of scale or colour | Uncertainty | Verdict-safe |
|---|---|---|---|
| Vitamin C clock | Switch time from frame timestamps; colour as ΔE00 against each cup's own start, normalised by a neutral background patch | One frame (1/30 s); background drift becomes the noise floor | Yes |
| Effervescent backup | Time for the tablet to disappear | One frame | Yes |
| Yeast towers | % of glass height, or the two-click ruler on a taped ruler or glass graduations; the card gives mm | Click error, or the card's 0.15 mm accuracy after strong tilt ([KB 09](../knowledge-base/09-measurement-and-calibration.md)) | Yes |
| Own salt run | Argus Card in the jar-front plane (keep it) | Card accuracy | Yes |
| Genze dishes | Ellipse fit to the 85 mm dish rim | ±3–5 % | Yes, with ± shown |
| Futo biofilms | Two-click ruler on the 1 cm scale bar | Click error | Measurement only |
| C. elegans plates | Published 12.4 µm/px ([Zenodo](https://zenodo.org/record/4673706)) | As published | Yes, if used |
| Danforth Setaria | Camera zoom calibration file ([Danforth](https://datasci.danforthcenter.org/data/)) | Per file | Yes |
| Zebrafish, NASA peppers | None, so % of first frame in pixel units | Scale-free while the camera stays fixed | Ratios only |
| Apple browning | Card recommended; the effect is small | ΔE about 1–2 per hour | Card only |

The clock is the clearest case. Its response is a time, and its colour jump from clear to blue-black dwarfs any plausible webcam drift (the pilot's noise floor will confirm this), so the card adds nothing to its verdict. The relative mode is sound only when three conditions hold:

- the camera never moves, zooms or cuts, which Argus can check by registering each frame to frame 0 and flagging any scale change beyond about 1 %;
- frames are never resized;
- growth does not rise toward an overhead camera.

Readings should carry their basis on screen, for example "Area: 412 % of first frame (pixel units; no physical reference)". Grey-world correction would invent colour change as seedlings green, so cardless colour must stay relative to each vessel's own start.

## Professional footage comes from freezing every variable

Most amateur-looking timelapses fail because something changed that should not have: auto exposure, white balance or focus, daylight, a lamp, a bumped camera, a hand in frame. Professionals remove all of it. Neil Bromhall films plants in a blackened, windowless studio, where a grow light acts as the sun and a studio flash makes every exposure identical day and night ([PetaPixel](https://petapixel.com/2021/09/04/a-timelapse-of-a-sunflower-opening-over-10-days/)). The desk version is one kind of constant, flicker-free light, windows blocked, and no other lamps or screens facing the glass. Choose the lighting style by subject:

- **Clear cups (bright field).** Put a light source behind or below them through a diffuser, so they read as dark-edged shapes on a glowing white field ([Sekonic](https://sekonic.com/classroom/whiteline-and-blackline-lighting/); [PopPhoto](https://www.popphoto.com/how-to/2014/07/how-to-using-backlight-to-photograph-glassware/)). This suits the clock: cups turning from glowing to black read instantly.
- **Foam, bubbles and plants (dark field).** A black background with lights behind and to the sides draws bright rims ([DIY Photography](https://www.diyphotography.net/?p=819)). This suits the yeast towers.
- **Petri dishes.** An A4 LED tracing pad gives even light from below, but flat pads work best for thin, translucent subjects ([Photofocus](https://photofocus.com/photography/lighting-photography/using-a-light-pad-for-photography/)).
- **Glare.** Matte black cards beside and above the camera stop the glass reflecting bright surroundings. A polariser cuts what remains, but only if fixed for the whole run, because it changes measured intensity ([NYIP](https://www.nyip.edu/photo-articles/archive/how-to-use-a-polarizing-filter)).

A curved seamless sweep of matte card replaces the grey wall from earlier runs. It hides the line where desk meets wall ([Expert Photography](https://www.expertphotography.com/diy-infinity-curve)) and gives SAM a uniform background.

Framing turns improvised into designed. In side views, set the lens at the height of the liquid's middle so surfaces read as flat lines, and use identical vessels in a straight row parallel to the sensor, spaced so outlines never touch. Leave 10–15 % of the frame empty for overlays, so numbers never sit on top of the evidence. Print the Argus Card on matte paper (lamination glares) and stand it in the vessels' front plane, in a corner. For the clock, put a vertical LED panel or tracing pad with a baking-paper diffuser behind a row of twelve cups, the webcam square-on at liquid height, and pours done by syringe from behind the row so hands never cross the cups. A second camera, the XA50 in 4K at 45°, shoots close-up B-roll that is never analysed. Hands that do enter frame belong in a declared intervention window, which Argus marks and the presentation copy cuts.

Lock the camera only after the lights have warmed up. Windows exposes a power-line-frequency property with 50 Hz, 60 Hz and automatic states ([Microsoft](https://learn.microsoft.com/en-us/windows-hardware/drivers/stream/ksproperty-videoprocamp-powerline-frequency)): set it to the local mains. Turn off auto exposure, white balance and focus, and enter a fixed Kelvin value ([Ceedo](https://www.ceedo.com/how-to-adjust-webcam-exposure-white-balance/)). Keep the shutter at a flicker-safe value (1/60 or 1/120 s on 60 Hz mains, 1/50 or 1/100 s on 50 Hz), never 1/48 s on 60 Hz ([Ulanzi](https://www.ulanzi.com/en-eu/blogs/knowledges/ambient-flicker-high-speed-outdoor-video-guide)). Then record 10 s and scrub it for banding. Whether the Nuroum webcam exposes all these controls is unverified, so check today with `ffmpeg -f dshow -list_options true` before any colour run. Record at native 1440p, which leaves cropping room in a 1080p edit. The timelapse interval follows simple arithmetic, interval = event duration ÷ (clip length × fps) ([Imagen AI](https://imagen-ai.com/tools/timelapse-interval-calculator/)): a 45-minute yeast run shown in 10 s at 30 fps needs a frame every 9 s, while the clock is shot at full frame rate, since its events last seconds. The XA50's infrared lamp works at 850 nm from the detachable handle ([Canon](https://www.canon-europe.com/video-cameras/xa55-xa50/specifications/)). Infrared frames are monochrome, so use them only for shape measurements across a whole run, never for colour, and never switch modes mid-run. Mount cameras on a tripod or clamp, not a phone stand, with taped feet and a slack, taped cable.

Everything done for looks happens on a copy. ffmpeg's `deflicker` filter averages frame brightness over a window of 2–129 frames ([ffmpeg](https://ffmpeg.org/doxygen/8.0/vf__deflicker_8c.html)), and two-pass `vidstabdetect`/`vidstabtransform` stabilises ([vid.stab](https://github.com/georgmartius/vid.stab)). Both alter pixels, so both are presentation-only, and if the camera really moved, that is an event for Argus to flag, not to hide. Grade globally and identically across vessels, never with local masks that exaggerate the effect. Render every outline and number from Argus's stored measurements instead of drawing them in the editor, use one colour per condition everywhere, and burn in a speed badge ("×600") plus a real-time clock. A one-line caption, "display copy colour-corrected; analysis on raw frames", heads off judges' doubts. A validation card (switch time against a stopwatch, mm against a ruler, Argus's sprout calls against Genze's labels where used) turns rigour into a visual.

The app capture needs the same care. Record OBS at a 1920×1080 output with CQP around 18, saved to MKV and remuxed to MP4 afterwards, so a crash cannot destroy the file ([Castr](https://castr.com/blog/obs-screen-recording/); [OBS-versions](https://obs-versions.com/blog/obs-recording-guide)). Use a clean browser profile at 125–150 % zoom, with notifications off. Judges may stop at three minutes, guides advise opening on the working product rather than an introduction ([hackathon.com](https://tips.hackathon.com/article/creating-the-best-demo-video-for-a-hackathon-what-to-know); [Reskilll](https://blogs.reskilll.com/hackathon-demo-presentation-tips-pitch-3-minutes-win-2026/)), and long model calls should be cut with a visible time-skip label. Self-driving-lab pitches sell the closed loop, from Ada's "design, run, learn" ([UBC Chemistry](https://chem.ubc.ca/node/32800)) to Coscientist's coloured well plates ([Boiko et al.](https://arxiv.org/pdf/2304.05332)). Argus should say "human in the loop": the researcher pours, Argus decides. Pixabay music needs no attribution ([Pixabay FAQ](https://pixabay.com/service/faq/)). Whether YouTube Audio Library tracks may be used outside YouTube is disputed ([LicenseOrg](https://licenseorg.com/guide/music-audio/youtube-audio-library)), so prefer Pixabay.

| Time | Beat | Footage | On-screen proof |
|---|---|---|---|
| 0:00–0:08 | Hook | Clock cups going dark one after another; per-cup timers freeze; "target 60 s, measured …" | Speed badge; "every number from a real run" |
| 0:08–0:25 | Problem and promise | Plan → watch → measure → judge → next run loop diagram; webcam and printed card | — |
| 0:25–0:55 | Live run | Wizard, SAM 3.1 masks on cups, plan locked, pours, live ΔE traces; provisional TOO_EARLY becomes SUPPORTED | Lower thirds naming each model |
| 0:55–1:25 | Ax loop | Round 1 grid, Ax suggestion with Muse's explanation, rounds 2–3 converging; fitted law | Round numbers; prediction vs result |
| 1:25–1:55 | The catch | Yeast race with randomised layout; warm spot disclosed; INCONCLUSIVE with rival; claim checker strikes a wrong number | "Staged on purpose" caption |
| 1:55–2:25 | Long run | Three days in 20 s, root lengths in mm, verdict with ±, one next-salt suggestion | "Recorded Oct 29–31, ×600" |
| 2:25–2:40 | Any field | 3-second cuts: biofilm in mm from its scale bar, NASA peppers in relative units, swarm "n = 1: no verdict" | Credits and licences |
| 2:40–3:00 | Close | Python computes, Muse interprets, Muse Wonder critiques; validation card; replay link; "built Oct 27 – Nov 4" | — |

For the Most Viral prize, cut the clock story as "Argus, make this clock go off at 60 s". It works muted: 0–2 s of cups going dark under a large timer, three rounds converging, then the hit and one line about a webcam, a printed card and Meta's SAM 3.1 and Muse. X recommends vertical 9:16 video ([X Help](https://help.x.com/en/business-and-advertising/creative-ad-specifications)). A 2026 study puts the hook in the first 2–5 s ([PaperTok](https://arxiv.org/pdf/2601.18218)), and clips under 20 s keep viewers but draw less engagement ([Geoscience Communication](https://gc.copernicus.org/articles/5/363/2022/)), which favours a full 20–25 s. Burn in captions, keep text away from the edges, post the replay link in the first reply, and use the yeast "Argus caught me" moment as a second post. Engagement counts until Nov 8 ([KB 13](../knowledge-base/13-demo-and-pitch.md)).

## Six days, with two protected for the edit

| Role | Pick | Source and licence | Fallback |
|---|---|---|---|
| Opening hook | Clock payoff | Self-filmed | Germination, 3 days in 5 s |
| Hero live run | One clock round run live with the app on screen | Self-filmed | Effervescent tablets vs water temperature |
| Ax loop | Clock, two factors, target 60 s, three rounds | Self-filmed | Yeast towers vs sugar |
| Rival and Inconclusive | Yeast towers with a disclosed warm spot | Self-filmed | Apple browning, low dose vs water |
| Long-run replay | Mung-bean salt run, if recording by tonight | Self-filmed, Argus Card | Genze dishes, CC BY 4.0, retrospective |
| B-roll | Self-shot close-ups; NASA PH-04 (public domain); Futo biofilms (CC BY 4.0); Commons lima bean and lettuce (CC BY); Grobas swarm (CC BY 4.0) | Credited on screen | Brachypodium (CC BY 4.0) |
| X clip | Clock "make it go off at 60 s" | Self-filmed | "Argus caught me" yeast clip |
| Stretch | Zebrafish dose re-analysis | CC BY 4.0, labelled published data | Zaritsky (CC0) or Danforth (CC BY 4.0) |

| Day | Bench and camera | Build | Production |
|---|---|---|---|
| **Thu Oct 29** | Start the salt run tonight, or commit to Genze. Buy plain white vitamin C tablets, Lugol's or 2 % tincture (note which), 3 % peroxide, laundry starch, 16 identical clear cups, syringes, gloves, instant yeast, sugar, dish soap, 8 identical tall glasses, a kitchen thermometer, a heating pad, an LED panel or tracing pad, matte black and white card | Check webcam controls with ffmpeg. If Genze: download and inspect the 840 MB zip. Check the zebrafish tar size, Futo's FigShare links and the NASA MP4 | Log the line-up and the water-bead decision in the decisions log |
| **Fri Oct 30** | Build the sweep, backlight, flags and rig; 10 s flicker test. Clock pilot: 5 doses × 2 cups plus 2 negative controls, measuring the noise floor and range, then choose the target | Per-cup switch-time event, relative ΔE mode and a two-factor Ax target objective, if not already built | Settle the overlay style and colours |
| **Sat Oct 31** | Lock the plan, then film three clock rounds; record the hero live take with OBS running; yeast warm-spot pilot with the thermometer; the salt run ends about now | Fix whatever the rounds expose | XA50 close-up B-roll of pours and the colour cascade |
| **Sun Nov 1** | Yeast rival run, randomised and disclosed, plan locked first; optional apple backup on the second camera | Import the salt run (time-scale factor 600) or Genze (dish ruler, relative mode, ground truth) | Rough narration script |
| **Mon Nov 2** | Re-shoots only | Export the replay page; zebrafish only if everything else is finished | Screen-record every segment on real data; render overlays; cut the X clip; write the attribution file |
| **Tue Nov 3** | — | Freeze the code; README credits | Edit, captions, music, end credits; under 3:00; watch once muted and once on a phone; upload unlisted |
| **Wed Nov 4** | — | Check the repo is public and the video link opens | Submit well before 9 PM ET; post the X clip; share the replay link |

If time slips, cut from the bottom of the priorities. The stretch re-analysis goes first, then the apple backup, then Genze if the own salt run exists. The clock loop and the yeast rival must survive, because together they carry the live demo, the loop, the honesty beat and the viral clip.

## Conclusion

The binding constraint of this hackathon is rounds per day, not image quality, and that favours chemistry over biology. An experiment whose response is a time solves three problems at once. It needs no scale reference, its effect is huge next to webcam noise, and a full plan → watch → judge → next-run cycle takes minutes, so Ax can be seen learning instead of being described. Germination shows the slow-science side, but only the clock shows the loop closing three times on camera. The honest moments also turn out to be designed, not found. Randomising positions is what lets Argus catch the warm spot, negative-control cups are what let it rule out light and time, and disclosing the staging is what keeps the catch from becoming fabricated evidence.

Safety optics reach past the five hazards written into rule 8. Water beads break none of them, yet they would undercut the product's credibility with exactly the audience it targets. The setup wizard's safety check should therefore also flag consumer-product warnings such as ingestion hazards, and the decisions log should record that choice. Published footage, meanwhile, earns its place through breadth and validation rather than verdicts. Only one open dataset found, the Konstanz zebrafish set, meets Argus's own bar of controls, replicates and a numeric dose. Argus judging published data and refusing to overclaim on it would show the strictness that a simple image analyser cannot fake.
