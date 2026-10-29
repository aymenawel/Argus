# Hero experiments for the Argus 3-minute demo (brainstorm, ranking and demo craft)

Scope: rank 8–15 desk-safe experiments by demo impact for the Meta Global AI Developer Hackathon video (due Nov 4, 2026, 9 PM ET; filming by Nov 3) and the 20–30 s "Most Viral" X clip, plus what makes science and AI product demos look professional. Hardware: Nuroum 1440p webcam, Canon XA50 (IR night mode), printed Argus Card. Argus measures area, height, length, count and colour ΔE per vessel; verdict rules need controls, at least 2 replicates per condition, a noise floor (effects under ~3x the noise floor are "not real yet") and a smallest effect that matters; Ax needs a numeric factor with 3+ levels. Research done Oct 29, 2026. Vocabulary follows `docs/knowledge-base/18-glossary.md`. Context from the repo: the salt-stress mung-bean germination run (6 jars, Canon side view) is already the chosen long run, with only one Ax round possible (`docs/knowledge-base/20-demo-experiment-germination.md`); the demo plan wants a multi-round Ax loop on a fast experiment (D-42) and no smart plug (D-44) (`docs/knowledge-base/13-demo-and-pitch.md`).

## Q1. Which desk-scale experiments give the most satisfying timelapses in minutes to hours, and which have a clear dose-response that makes Ax's next-run suggestion meaningful?

### Takeaway
The strongest pair is a **vitamin C iodine clock** (fast, sharp colour events, published dose-response data, room for 2–3 real Ax rounds in one afternoon) plus **water beads swelling in salt vs fresh water** (the most satisfying growth timelapse, large effect, 4–12 h). The yeast foam tower vs sugar is the best third option because its response probably has a peak (osmotic inhibition at high sugar), which is the case where Bayesian optimisation looks smart rather than trivial. Most other kitchen classics either have no published numbers, are hard to segment (transparent ice, foam hiding a tablet) or are too slow to finish before Nov 3 (slime mould, phototropism from seed, crystals).

### Cited Findings

**Vitamin C clock (iodine + vitamin C + 3% hydrogen peroxide + starch)**
- Kitchen recipe used in a peer-reviewed study: Solution A = 5 ml vitamin C stock (one 1000 mg tablet in 30–120 ml water) + 2.5–10 ml of 3% w/v Lugol's iodine + 60 ml warm (40 °C) tap water; Solution B = 15 ml 3% hydrogen peroxide + 1 level teaspoon powdered laundry starch + 60 ml warm water; mix A and B, stir 5 s, time clear-to-blue — [Kerr et al., Royal Society Open Science 2019 (PMC6502385)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6502385/)
- Mechanism: vitamin C reduces iodine back to iodide faster than peroxide oxidises iodide to iodine, so the mixture stays clear until vitamin C is nearly used up, then starch turns blue — [Kerr et al. 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6502385/)
- Measured switch times, two repeats per level, vitamin C series (iodine fixed): 48.1/43.6 s at the most dilute stock (c0 = 0.00163 M), 68.7/74.3 s, 116.9/122.3 s, 153.0/168.1 s, 243.7/210.9 s at the most concentrated (0.00653 M) — [Kerr et al. 2019, Table 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC6502385/)
- Iodine series (vitamin C fixed): 427.0/495.8 s at 2.5 ml Lugol's, 285.4/246.3 s at 3.75 ml, 116.9/122.3 s at 5 ml, 55.7/43.7 s at 7.5 ml, 19.5/22.6 s at 10 ml — [Kerr et al. 2019, Table 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC6502385/)
- The paper's approximate switch-time formula is t_sw ≈ (c0 − ϕm0)/(m0²k0), with fitted k0 ≈ 0.57 M⁻¹s⁻¹ and ϕ ≈ 0, i.e. roughly proportional to vitamin C and inversely to iodine squared; the authors call the switch time "repeatable" and suggest temperature (Arrhenius) as future work — [Kerr et al. 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6502385/)
- A follow-up paper gives switch-time expressions that also include the hydrogen peroxide concentration (a third factor) — [Alsaleh et al., arXiv 2408.04108](https://arxiv.org/abs/2408.04108)

**Water beads (sodium polyacrylate superabsorbent)**
- Equilibrium water uptake of sodium polyacrylate particles depends strongly on the salt concentration of the medium and on crosslink density — [Sohn & Kim study record, SKKU](https://pure.skku.edu/en/publications/theoretical-and-experimental-investigation-of-the-swelling-behavi/)
- Teaching figures: absorbs about 800x its weight in distilled water but about 300x in tap water (secondary, educational) — [Carnegie Mellon Gelfand Center](https://www.cmu.edu/gelfand/k12-educational-resources/polymers/polymer-and-absorption/super-absorb-powder.html); "over five hundred times its weight in pure water, but less in salty water" — [Temple chem demo](https://sites.temple.edu/chemdemo/?p=66)
- Mechanism (osmotic): sodium inside the network draws water in; salt outside shrinks the gradient so uptake drops — [Carnegie Mellon](https://www.cmu.edu/gelfand/k12-educational-resources/polymers/polymer-and-absorption/super-absorb-powder.html)
- Early swelling of polyacrylamide gel beads scales roughly as t^0.45 (diffusion-dominated uptake) — [arXiv 1605.00599](https://arxiv.org/pdf/1605.00599)
- Classroom template: students measure size over time and compute swelling rate and percent increase — [CMU "Swelling Creatures"](https://www.cmu.edu/gelfand/lgc-educational-media/polymers/polymer-and-absorption/swelling-creatures.html)
- A Grade 6 project (single trial) reported plain water caused no shrinkage of swollen beads while salt made them about 50% smaller over 1–24 h — [CYSF project "How Orbeez Work"](https://platform.cysf.org/project/9ed00f4c-d20f-411d-8ce2-71a529eefc12)
- Growth time claims of 4–12 h for standard 3–5 mm beads come from a low-quality web page; treat as rough — [nimss.org page (low reliability)](https://new.nimss.org/article/the-science-backed-guide-to-speeding-up-orbeez-growth)
- A 2024 university abstract studied shrinking water beads in hyperosmolar solutions because of ingestion risk (results not available) — [ETSU ASRF 2024](https://dc.etsu.edu/asrf/2024/schedule/67)

**Yeast (foam tower / CO2) vs sugar**
- A teaching resource expects CO2 production to rise with sucrose up to about 10% and notes very high sucrose can lower it, "perhaps due to osmotic effects" — [Serendip Studio yeast lab discussion](https://serendipstudio.org/exchange/comment/reply/3706/144486)
- Student studies disagree: one found 2% dextrose beat 1% and 3% — [OSU J. Introductory Biology Investigations, corn sugar](https://undergradsciencejournals.okstate.edu/index.php/jibi/article/view/6163); others found less CO2 at higher sugar, attributed to osmotic stress — [OSU JIBI "Sugar Rush"](https://undergradsciencejournals.okstate.edu/index.php/jibi/article/view/7025) (which student paper reported which trend is from a search summary; not opened)

**Elephant toothpaste (yeast catalyst + 3% peroxide + soap)**
- More catalyst should release oxygen faster (qualitative) — [ChemTalk](https://chemistrytalk.org/make-elephant-toothpaste/)
- Student project: 12% peroxide foam left the beaker after 2 s vs 3 s for 3%; 3% gives the same reaction, smaller — [CYSF "Foam Wars"](https://platform.cysf.org/project/65a59d7c-9096-436a-abab-3d56f0ddbd6f/); data tables in such projects use inconsistent units — [CYSF science fair PDF](https://platform.cysf.org/media/Science_fair_TVgTA90.pdf)

**Effervescent tablet (Alka-Seltzer) vs water temperature**
- Hot water: about 20–30 s to dissolve; ice-cold: most dissolves in 2–3 min with residue still bubbling at 6 min — [Science Buddies activity](https://www.sciencebuddies.org/stem-activities/alkaseltzer-science-the-effect-of-temperature-on-reaction-time)
- A Science Buddies project version times the reaction from the fizzing sound with a phone app — [Science Buddies Chem_p027](https://www.sciencebuddies.org/science-fair-projects/project-ideas/Chem_p027/chemistry/alka-seltzer-effect-of-temperature-on-reaction-time)
- Student data: 51 s at 15 °C vs 22 s at 45 °C — [all-science-fair-projects](https://www.all-science-fair-projects.com/project1302_details.html); 129 s at 20 °C vs 23.7 s at 80 °C for bubbles to stop — [Scribd student lab](https://www.scribd.com/document/338571372/Lab)

**Apple browning vs ascorbic acid (vitamin C)**
- Inhibition by ascorbic acid is dose-dependent over 24 h; 0.5% browned very rapidly with the highest ΔE, 3% performed about as well as ascorbic acid plus ultrasound — [2009 abstract, Ciência e Tecnologia de Alimentos (SciELO)](https://www.scielo.br/j/cta/a/qwdJ4KJ8gJM8Vgg7xzxPtxr/abstract/?lang=en) (attribution of this abstract to this URL comes from a search summary)
- Ascorbic acid treatments showed a significantly smaller drop in L* than a water control at 4 h, and most still did at 24 h — [sodium chlorite vs browning study, AGRIS](https://agris.fao.org/search/en/records/65de7d09b766d82b18fdba33)
- Browning is non-uniform across a slice, so surface-averaged L* can hide local differences — [Characterizing the Variability of Enzymatic Browning in Fresh-Cut Apple Slices](https://investigadores.anid.cl/es/public_search/work?id=268861); 1% ascorbic acid + 1% CaCl2 kept L* higher; lightness falls from day one — [Lunadei thesis, U. Chile](https://repositorio.uchile.cl/xmlui/bitstream/handle/2250/120183/Lunadei_Loredana.pdf?sequence=1)

**Paper wicking (capillary rise)**
- The Lucas-Washburn law (1908) predicts the liquid front advances with the square root of time — [Terzis, spontaneous imbibition thesis, Technion](https://aerospace.technion.ac.il/wp-content/uploads/2020/12/ATerzis_Spontaneous_Imbibition.pdf)
- Paper-towel upward wicking front position has been fitted to Lucas-Washburn in ~10 min experiments under controlled humidity and temperature — [Soft Matter supplementary, RSC](https://www.rsc.org/suppdata/sm/c2/c2sm07080d/c2sm07080d.pdf)
- The wetting front can warm by up to about 10 °C during water wicking, depending on the paper — [Terzis thesis](https://aerospace.technion.ac.il/wp-content/uploads/2020/12/ATerzis_Spontaneous_Imbibition.pdf) (attribution from a search summary)

**Slime mould (Physarum polycephalum) maze**
- Plasmodium inoculated in a maze's outer channel grows toward an oat flake in the central chamber — [Adamatzky, arXiv 1108.4956](https://arxiv.org/abs/1108.4956)
- A student study reported maze completion within a 48 h window — [Davidoff et al. 2023, Scipedia](https://www.scipedia.com/public/Davidoff_et_al_2023a)
- Home version: start from dormant sclerotium with oat flakes; crayon walls failed (it grew over them), acetate mazes worked; it avoids light, so keep it dark — [Science Buddies blog](https://www.sciencebuddies.org/blog/slimy-but-smart-slime-mold-science)

**Gummy bear osmosis**
- Only lab-report templates were found: water gives gain, salt or concentrated sugar gives loss; percent change = (final − initial)/initial × 100; weak sugar may still swell. No measured values — [template PDF (low-quality mirror)](https://cms.theglasshouse.org/Download_PDFS/mL0536/600233/Lab%20Report%20Gummy%20Bear%20Experiment%20Osmosis.pdf)

### Inferences

#### Ranking (demo impact, adjusted for what can be filmed by Nov 3)

| Rank | Experiment | Best role in the video | Duration | Ax fit | Verdict likely clean? | Viral |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Vitamin C iodine clock, dose series | Live run + multi-round Ax loop | 20 s – 8 min per run | Very good (2 factors, target time) | Yes | High |
| 2 | Water beads, salt vs fresh water | Hook + X clip + long-ish timelapse | 4–12 h | OK (find half-size salt level) | Yes | Very high |
| 3 | Yeast foam towers vs sugar | Second fast loop or rival moment | 20–60 min | Best (likely has a peak) | Partly (peak may be Inconclusive) | High |
| 4 | Apple browning vs vitamin C | Colour ΔE + honest Inconclusive | 1–4 h | Good ("lowest dose that works") | Yes at high dose, not at low | Medium |
| 5 | Mung-bean germination vs salt (already planned) | Long run, IR night frames, labelled replay | 60–72 h | One round only | Probably | Medium-high |
| 6 | Skittles rainbow vs water temperature or sugar | X clip filler, fast colour | 1–3 min | OK | Probably | High |
| 7 | Ice cubes vs salt dose (lamp rival staged) | "Caught a rival" set piece | 20–60 min | OK | Deliberately not (rival) | Medium |
| 8 | Effervescent tablet vs water temperature | Quick dose-response | 20 s – 3 min | OK (1D) | Yes | Medium |
| 9 | Elephant toothpaste vs yeast amount | Spectacle shot | 5–60 s | Weak (monotonic) | Yes | High |
| 10 | Paper wicking vs sugar (viscosity) | Physics-law fit moment | 10–20 min | OK | Yes | Low-medium |
| 11 | Gummy bear osmosis vs salt | Cute B-roll; "isotonic point" search | 12–24 h | OK (root-finding) | Probably | Medium-high |
| 12 | Phototropism of cress seedlings | Day/night IR shot | 4–5 days growing + hours bending | Weak | Unknown | Medium |
| 13 | Slime mould maze | Re-analysed published footage only | 1–2 days + shipping | Weak | n/a | Very high |
| (also considered) | Red cabbage pH indicator, marker chromatography, baking soda balloon, salt/borax crystals, brine shrimp hatching | Mostly no | instant / 10 min / seconds / days / 24–36 h | Weak or none | — | — |

#### Candidate cards

**1. Vitamin C iodine clock (the loop experiment)**
- Story: "Argus tuned a chemical clock to go off at exactly 60 seconds, in three rounds."
- Visual: 6–10 clear cups in a row on white paper with the Argus Card; all clear, then cups snap to blue-black one after another like dominoes; each vessel's outline flashes as its switch event fires and a per-cup timer freezes ("t_switch 61.2 s"). A strip chart of ΔE per vessel jumps from near zero to a plateau. Real time 2–8 min per round, shown at 4–8x.
- Fit in 3 minutes: 35–45 s for the whole loop (round 1 grid, Ax suggestion card with Muse's explanation, round 2/3 cups, "target 60 s, got 60.4 s"). Each round takes under 10 min to set up and run, so three rounds fit one afternoon (Oct 30 or 31).
- Factor and levels: vitamin C stock dilution, 5 levels (30, 45, 60, 90, 120 ml per 1000 mg tablet, as in Kerr) and/or Lugol's volume (2.5, 3.75, 5, 7.5, 10 ml). Two replicates per level.
- Ax: objective "switch time closest to 60 s" over two factors (vitamin C × iodine), optionally "using the least iodine". The iodine response is strongly nonlinear (22x change in time over a 3.8x change in iodine, from Kerr Table 1, my arithmetic), so a 2-factor target search is a real optimisation problem, not a straight line. 60 s and 90 s targets both lie inside the tested range (between the 120 ml and 90 ml vitamin C dilutions at 5 ml iodine).
- Expected effect: means from Kerr Table 1 (my arithmetic) are 45.8, 71.5, 119.6, 160.6, 227.3 s across the vitamin C series, roughly linear; replicate pairs differ by 5–15% (one iodine pair by 24%). Adjacent levels differ by 25–67 s, far above replicate spread. A smallest effect that matters of 10 s or 15% would be cleared easily.
- Bonus technical moment: Argus fits t_sw ∝ c0/m0² to its own data and compares the fitted rate constant with the published k0 ≈ 0.57 M⁻¹s⁻¹ (only if concentrations are known; with US 2% tincture of iodine instead of 3% Lugol's the constant will differ, so phrase it as "same shape as the published model").
- What could go wrong: start-time sync across cups (pour one cup at a time; log t0 per vessel from the pour, or a voice note per cup); unequal stirring; water temperature differences between pours (rate depends on temperature; a natural rival); chewable or orange-coloured vitamin C tablets add colour (use plain white tablets); starch must be dispersed (powdered laundry starch as in Kerr, or liquid starch; avoid boiling cornstarch to stay within "no strong heat"); hands occluding cups during pours; dark blue can creep in from the top of an unstirred cup, so the ΔE threshold should be on the whole-vessel mean.
- Materials and cost (estimates): plain vitamin C 1000 mg tablets, Lugol's or 2% tincture of iodine, 3% hydrogen peroxide, starch, 12 clear 9 oz cups, 2–3 dosing syringes, gloves. About $30–40.
- Safety: household-strength chemicals, but iodine is harmful if swallowed and stains; gloves and glasses, label "not for drinking", no heat needed (room-temperature water works; times get longer). The wizard should mark it as a mild-chemical experiment with no automatic actions.
- Verdict: clean SUPPORTED for "more vitamin C delays the switch" with 2 replicates per level.

**2. Water beads in salt vs fresh water (the hook)**
- Story (if the run shows it): "Argus watched 10 water beads grow for 6 hours and caught salt cutting their growth by more than half."
- Visual: top-down grid of single beads in clear cups (one bead per vessel) on the Argus Card; outlines inflate like balloons, diameter in mm ticking up beside each; a growth curve per bead with a fitted power law. 6 h → 8–12 s.
- Fit: 10–15 s as the cold open and the core of the X clip.
- Factor and levels: NaCl 0 (distilled), 1, 3, 10, 30 g/L, 2 beads/cups per level. Add tap water as an extra arm (see rival section).
- Ax: response is monotonic, so frame the goal as "find the salt level that halves final diameter" (target search) or "predict seawater (35 g/L)". Less impressive than the clock, which is why this is the hook, not the loop.
- Expected effect: 800x vs 300x uptake by weight in distilled vs tap water (CMU, secondary) implies about (800/300)^(1/3) ≈ 1.4x larger diameter in distilled water than in tap water alone (my arithmetic, assuming volume ∝ mass of water); salt water roughly halves size in a single-trial school project. Early growth should follow about t^0.45 (polyacrylamide data), which Argus can fit and print ("diffusion-limited swelling, exponent 0.4–0.5") as a technical-depth moment.
- What could go wrong: swollen clear beads are nearly invisible in water because their refractive index approaches water's (use dark-coloured beads, white background, even diffuse light, top-down view); beads touching merge into one mask (one bead per cup); dry beads vary in size (normalise to d/d0 per bead); beads in strong salt may crack (seen in a blog); meniscus reflections at cup edges; IR night mode turns coloured beads grey, so use the webcam with constant LED light, not the Canon IR mode.
- Materials and cost (estimates): bag of water beads, 1 gallon distilled water, table salt, 10–12 clear cups or a clear ice-cube tray. About $10–15.
- Safety: water beads are an ingestion hazard for young children and pets (the ETSU study was motivated by ingestion risk); keep out of reach, bin them (don't flush).
- Verdict: clean SUPPORTED for 0 vs 10–30 g/L; low salt (1 g/L) vs 0 may land under 3x the noise floor early on (a natural TOO_EARLY that resolves later).

**3. Yeast foam towers vs sugar**
- Story: "Argus found the sugar sweet spot for yeast, and noticed when too much sugar slowed it down."
- Visual: 5–6 identical tall glasses or 100 ml graduated cylinders, foam columns racing upward, height (mm) and rise rate per vessel, leaderboard-style bars. 45 min → 10 s.
- Fit: 15–25 s; can carry the rival moment (lamp or warm-water cup) or serve as a second Ax loop. Matches the application's own example ("warmer water makes it rise faster").
- Factor and levels: sugar 0, 2, 5, 10, 20, 40 g per 100 ml, with fixed yeast, soap and water temperature.
- Ax: likely non-monotonic (rise, then osmotic inhibition), so "maximise rise rate" over sugar (and optionally yeast amount) is the textbook BO case: Ax should place points around the peak.
- Expected effect: direction supported (increase to ~10%, decrease at very high sugar, per a teaching resource) but no reliable magnitude; student results disagree on where the peak sits. Expect a clean difference between 0% and ~5%; the peak position may be INCONCLUSIVE with 2 replicates.
- What could go wrong: water temperature dominates yeast activity, so cups filled from a cooling jug drift (measure and log water temperature with a kitchen thermometer); foam collapses or sticks to walls; vessels must be identical (height depends on cross-section); yeast clumps; overflow ends the measurement (detect as an overflow event).
- Materials and cost (estimates): instant yeast (3-pack), sugar, dish soap, 6 identical tall glasses or a cylinder set, kitchen thermometer. About $10–20.
- Safety: food-grade; warm tap water only.
- Verdict: clean for some contrasts, honest INCONCLUSIVE likely for the exact peak.

**4. Apple browning vs vitamin C dose**
- Story: "Argus measured browning in colour units and found the smallest vitamin C dose that still works."
- Visual: slices from one apple on a white plate next to the Argus Card colour patches; each slice outline with live ΔE; a colour swatch strip per slice showing its colour every 15 min; split-screen raw vs ΔE heat map.
- Fit: 10–20 s; best place for the honest INCONCLUSIVE (low doses vs control within noise).
- Factor and levels: ascorbic acid 0 (water dip), 0.25, 0.5, 1, 2% (tablets dissolved in water); lemon juice as a reference arm; 2–3 slices per dose.
- Ax: "lowest dose with ΔE < threshold at 2 h" is a cost-aware objective that makes the suggestion sound like a real lab decision.
- Expected effect: dose-dependent; 0.5% fails quickly vs 3% holding up over 24 h; ascorbic acid beats water at 4 h. No room-temperature ΔE-per-hour figure was found.
- What could go wrong: webcam auto white balance and exposure will fake or erase ΔE (lock them, and colour-correct to the card patches); slice-to-slice variation (cut all slices from the same apple, randomise dose to slice, cut quickly or in random order to avoid a time-since-cut rival); non-uniform browning (measure a fixed inner ROI); drying and curling over hours; daylight from a window changing.
- Materials and cost: 2 apples, a lemon, vitamin C tablets (shared with the clock). About $5.
- Verdict: clean SUPPORTED for water vs 1–2%; INCONCLUSIVE for 0.25% vs water is plausible.

**5. Mung-bean germination vs salt (already planned long run)**
- Story: "3 days of seeds in 25 seconds, every sprout counted and every root measured."
- Visual: side view of 6 jars, sprout onset events popping per bean, root lengths in mm, IR night frames from the Canon.
- Fit: 20–30 s as the labelled replay ("recorded Oct 27–30, analysed by Argus, 600x").
- Ax: one round only (suggested next salt levels shown, not run). Effect sizes are covered in the existing germination notes, not re-researched here.

**6. Skittles rainbow vs water temperature (or sugar in the water)**
- Story: "Argus timed how fast the rainbow spreads, and warm water won."
- Visual: top-down plates with a ring of candies; colour bands flow inward; Argus draws the colour front radius in mm.
- Factor: water temperature (ice water, cold tap, room, warm tap ≤45 °C) or sugar pre-dissolved in the water (0, 10, 20, 40%), 2 plates per level.
- Risks: pouring disturbs the bands; uneven water depth and non-level plates skew flow; colours merge in the centre. Cost under $5. No measured data found, so effect size is unknown (gap).

**7. Ice cubes vs salt dose (the staged rival)**
- Story: "Argus caught the desk lamp, not the salt, melting the ice."
- Visual: coloured or clear ice cubes on a dark tray, area shrinking, time to 50% area per cube; a heat-map arrow showing the side nearest the lamp melting faster in every dose.
- Factor: salt 0, 0.5, 1, 2, 4 g per cube, randomised positions, 2 cubes per dose.
- Risks: transparent ice and meltwater are hard to segment (food-coloured ice dyes the puddle, so use clear ice on black with side light, or a side view of cube height); cubes vary in starting size (normalise). No sourced numbers (gap).

**8. Effervescent tablet vs water temperature**
- Story: "Argus timed the fizz to the second at four temperatures."
- Visual: tablets in clear cups, shrinking disc area or foam ring; times frozen per cup.
- Factor: ice water, cold tap, room, warm tap (≤45 °C). Expected: roughly 20–30 s hot vs 2–3 min ice-cold (Science Buddies); 51 s at 15 °C vs 22 s at 45 °C (student).
- Risks: foam hides the tablet (measure from the side, or time the end of bubble motion as an event); warm cups cool during the run. Cost about $6. The lava-lamp variant (oil, water, food colouring) is prettier but much harder to measure.

**9. Elephant toothpaste vs yeast amount**
- Spectacle and very shareable, but the response is monotonic and over in seconds; foam leaves the frame and ends the measurement; messy. Good as a 2-second B-roll beat, weak as the Ax experiment.

**10. Paper wicking vs sugar (viscosity)**
- Story: "Argus rediscovered a 1908 physics law from a paper towel."
- Visual: strips dipped in dyed water, front height climbing, an h vs √t line overlay with fitted exponent near 0.5.
- Factor: sugar 0, 10, 20, 30, 40% (higher viscosity should slow the front; magnitude not sourced).
- Risks: the dye front can lag the water front (a built-in rival explanation: Argus measures the dye, not the water); evaporation and strip curl; wetting-front warming. Cost about $3.

**11. Gummy bears vs salt**
- Story: "Argus found the salt level where a gummy bear neither grows nor shrinks."
- Factor: salt 0, 0.5, 1, 2, 5%; Ax objective: size change = 0 (root finding). 12–24 h; gelatin softens and loses outline; bears tip over. Must start by Nov 1. No measured data found.

**12. Phototropism**: needs seedlings grown for several days first and an angle measurement that Argus does not list; too tight for Nov 3. **13. Slime mould**: very viral, but culture shipping plus 1–2 days of growth makes it infeasible; use only as "re-analysed published footage" if a clearly licensed clip is found.

#### Suggested set for the video (inference)
- Cold open and X clip: water beads (growth with mm numbers) cut with the clock's blue cascade.
- Live run and multi-round Ax loop: the vitamin C clock (Oct 30–31, three rounds, about 30 cups total).
- Rival explanation: lamp-side position effect on yeast towers or ice (randomised layout makes it detectable).
- Honest INCONCLUSIVE: apple browning at 0.25% vs water, or the yeast peak position.
- Long run: the existing germination replay with IR frames.
- Schedule sketch: shop Oct 29–30; clock rounds Oct 30–31; water beads overnight Oct 30–31; yeast and apple Nov 1; germination ends Oct 30–Nov 1; record and edit Nov 2–3.

### Gaps
- No measured data were found for ice melting vs salt dose, Skittles spreading speed, gummy bear percent change, or yeast foam height vs sugar; their effect sizes must come from a pilot run.
- No primary table of water-bead diameter vs NaCl molarity was found; the 800x/300x figures are educational, and growth-time figures come from low-quality pages.
- Phototropic bending time for cress and Physarum growth speed in mm/h were not found.
- Whether the Nuroum webcam exposes manual white balance and exposure through UVC/OpenCV was not checked; it matters for every ΔE experiment.
- Material prices are estimates, not looked up.

## Q2. Which experiments give a good "caught a rival explanation" moment and an honest "Inconclusive" moment?

### Takeaway
The cleanest on-camera rival is a **position or lighting effect that hits the control too**: a desk lamp on one side of randomised cups (yeast or ice), a hand bump that shifts the frame, or an exposure/white-balance jump that moves ΔE in every vessel at once. The cleanest honest INCONCLUSIVE is a **small dose vs control difference under 3x the noise floor** (apple at 0.25% vitamin C, yeast peak position), or TOO_EARLY on the first hour of water beads at low salt.

### Cited Findings
- Yeast activity depends on conditions beyond sugar, and high sugar can reduce CO2 through osmotic effects, so temperature and dose effects can be confused — [Serendip Studio](https://serendipstudio.org/exchange/comment/reply/3706/144486)
- Effervescent reaction time changes several-fold with water temperature (20–30 s hot vs 2–3 min ice-cold), so unequal water temperature is a large rival in any timed reaction — [Science Buddies](https://www.sciencebuddies.org/stem-activities/alkaseltzer-science-the-effect-of-temperature-on-reaction-time)
- The vitamin C clock recipe specifies 40 °C water and the authors list temperature dependence as untested future work — [Kerr et al. 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6502385/)
- Tap water already cuts superabsorbent uptake (800x distilled vs 300x tap), so a "fresh water" control made with tap water is itself a rival — [Carnegie Mellon](https://www.cmu.edu/gelfand/k12-educational-resources/polymers/polymer-and-absorption/super-absorb-powder.html)
- Browning varies within and between apple slices, so averaging can hide local differences — [ANID record](https://investigadores.anid.cl/es/public_search/work?id=268861)
- Professional plant timelapse uses a light-tight studio with a grow light for the plant and a flash for exposure, so frames look the same day and night — [PetaPixel on Neil Bromhall's sunflower](https://petapixel.com/2021/09/04/a-timelapse-of-a-sunflower-opening-over-10-days/)

### Inferences
- **Lamp position effect (best rival set piece).** Randomise dose positions, then put a warm desk lamp (incandescent or halogen, not LED) near one end. If the lamp-side cups of every dose, including the control, rise or melt faster, Argus can say "the effect follows position, not dose" and return INCONCLUSIVE with "rival: lamp heat (position)". This works only because the layout was randomised, which is itself a good science point to say out loud. Yeast is the better host (big temperature sensitivity, no segmentation trouble); ice is more intuitive for viewers.
- **Lighting change.** Switch a room light on mid-run in the apple experiment: ΔE jumps in every slice at the same frame, including the Argus Card's neutral patch. Argus flags an intervention-like event and a rival (lighting), and colour correction to the card should remove most of it; showing the before/after correction is strong technical evidence.
- **Hand bump.** Nudge the tray in the water-bead run: all outlines jump together; Argus re-registers to the card's ArUco markers and logs an intervention instead of reporting fake growth.
- **Tap water control.** In the water-bead run, a tap-water arm next to distilled shows that "fresh water" is not one thing; Muse can raise it as a rival when the control is tap water.
- **Temperature drift in the clock.** Pour the second replicate of one level from a warmer jug; the replicate pair disagrees by more than the usual 5–15%. Argus cannot measure temperature itself, so the honest output is "replicates disagree beyond the noise floor; possible rival: water temperature (researcher note)", which demonstrates the researcher-note path.
- **Honest INCONCLUSIVE choices.** Apple 0.25% vs water at 2 h (likely within noise, given slice variation); yeast "peak at 10%" claim when 5%, 10% and 20% overlap with 2 replicates; water beads at 1 g/L vs 0 in the first hour (TOO_EARLY that later turns into SUPPORTED, which also shows the provisional verdict updating live).
- Avoid staging a rival in the clock rounds used for the Ax loop: a confounded round would make the optimisation segment look broken.

### Gaps
- No source quantified how much a desk lamp warms a nearby cup or ice cube; a 20-minute pilot with a kitchen thermometer would size the effect.
- Whether the webcam's auto exposure reacts to a room-light change fast enough to create a clean single-frame jump was not tested.

## Q3. What do winning hackathon demos and polished science/AI product videos do?

### Takeaway
They open on the working product and the result (not an intro), map each beat to the judging criteria, show real data and the closed loop, keep lighting and framing consistent, and make long processes watchable by compressing them hard with numbers drawn on. Self-driving-lab demos sell the loop (design, run, learn) and colour is their favourite visual; long-running timelapse channels show audiences will watch days compressed into about 90 seconds.

### Cited Findings
- Begin by demonstrating the project immediately instead of a long introduction — [hackathon.com tips](https://tips.hackathon.com/article/creating-the-best-demo-video-for-a-hackathon-what-to-know)
- Judges often see only the video, map features to each judging criterion, show the product rather than code, add stand-out elements (quick intros, graphics, music), keep under the length limit and link a live demo — summarised from [hackathon.com tips](https://tips.hackathon.com/article/creating-the-best-demo-video-for-a-hackathon-what-to-know), [DEV: How to make your Devpost submissions not suck](https://dev.to/jacklyn/how-to-make-your-devpost-submissions-not-suck-37i0), [AngelHack demo tips](https://angelhack.com/blog/10-tips-to-help-you-rock-your-next-hackathon-demo/) and [Reskilll 3-minute pitch tips](https://blogs.reskilll.com/hackathon-demo-presentation-tips-pitch-3-minutes-win-2026/) (which tip comes from which page was not verified one by one)
- Past Meta Llama hackathon winners were mostly practical agents and tools: Llama Impact Hackathon SF first place "Llama Navigator AI", a Chrome extension guiding users through websites — [lablab.ai summary](https://lablab.ai/ai-articles/llama-impact-hackathon-sf-summary); London Llama Impact top three shared $50,000 plus six weeks of mentorship — [Meta newsroom](https://about.fb.com/news/2024/11/metas-llama-impact-hackathon-pioneering-ai-solutions-for-public-good/); LlamaCon hackathon winners post — [Meta AI blog](https://ai.meta.com/blog/llamacon-hackathon/), with "OrgLens" 1st and "Llama CCTV Operator" 3rd per a Meta for Developers Reddit recap — [Reddit mirror](https://redlib.hbubli.cc/user/MetaforDevelopers/submitted)
- Ada (UBC, Berlinguette group) was presented as the first self-driving lab for thin-film materials, a closed loop that designs, runs and learns from its own experiments — [UBC Chemistry news](https://chem.ubc.ca/node/32800); [TechConnect 2021 abstract](https://techconnectworld.com/World2021/a.php?i=152); paper in [Science Advances 6(20) eaaz8867](https://advances.sciencemag.org/content/6/20/eaaz8867)
- Baird & Sparks define a "minimal working example" self-driving lab as under 100 USD, under 0.1 m² of desk and under 1 h setup — [Matter, DOI 10.1016/j.matt.2022.11.007](https://doi.org/10.1016/j.matt.2022.11.007); their demos (light-mixing with a Pico W, LEDs, a light sensor and Bayesian optimisation; liquid- and solid-mixing) are open source — [GitHub sparks-baird/self-driving-lab-demo](https://github.com/sparks-baird/self-driving-lab-demo); [STAR Protocols "Hello World" build guide (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10244891)
- Coscientist's liquid-handler tasks used red, yellow and blue samples on 96-well plates with a UV-Vis read per well to identify colours — [Boiko et al., arXiv 2304.05332](https://arxiv.org/pdf/2304.05332)
- Neil Bromhall controls interval, grow light with blind, and track/rotating head with a bespoke control box; studio flash keeps exposure even day and night; the sunflower took 10 days — [PetaPixel](https://petapixel.com/2021/09/04/a-timelapse-of-a-sunflower-opening-over-10-days/); an acorn germinating underground used a 2-hour interval — [Faena Aleph](https://faena.com/aleph/from-acorn-to-oak-tree-a-3-minute-time-lapse-recorded-over-eight-months) (source of the interval detail per a search summary)
- Boxlapse (plant and fungi timelapses) has about 3M subscribers and 1.5B views per a third-party tracker snapshot dated July 4, 2026 — [speakrj](https://www.speakrj.com/audit/report/UCiL9l2J57t5OG2aZ0huswZw/youtube/media-stats/); one video compresses 13 days of oyster mushrooms into 90 seconds — [Nerdist](https://nerdist.com/article/mushroom-growing-time-lapse-boxlapse/)

### Inferences
- **Open on the payoff.** First 5 s: the water beads inflating with mm numbers and a SUPPORTED badge, or the clock cascade freezing on "60.4 s (target 60)". Title card and problem statement come after the viewer has seen it work.
- **One beat per criterion.** Impact (who it's for, $30 webcam + printed card), Meta tooling (SAM 3.1 masks becoming mm, Muse notes passing the claim checker, Muse Wonder critique, Ax), technical depth (noise floor, ±, claim checker rejecting a wrong number on screen), demo (live run, rival caught, loop). Put a small lower-third naming the model used at each beat ("SAM 3.1 · masks", "Muse Spark · note", "Ax · next run").
- **Show the loop explicitly.** Ada's pitch is design → run → learn. A visible loop diagram that lights up as Argus moves through plan → watch → measure → judge → next run, with real round numbers (round 1, 2, 3 converging on the target), is the self-driving-lab signature. The Baird & Sparks "under $100, under 0.1 m², under 1 h" bar is a useful framing line, but say "human-in-the-loop": the researcher pours the cups, Argus decides.
- **Colour is the house visual of AI lab demos** (Coscientist's coloured plates). The clock and apple experiments give Argus its own colour story with ΔE numbers instead of a plate reader.
- **Timelapse craft.** Lock focus, exposure and white balance; light with constant, flicker-free LED (or consistent IR at night) as Bromhall does with flash; never move the camera; burn in a clock and speed label ("×600"); a consistent colour per condition across overlays, charts and legend; outlines thin and semi-transparent so the subject stays visible; numbers placed next to each vessel, not in a far-off table.
- **Formats that read instantly:** split screen raw vs overlay; before/after wipe; race/leaderboard bars for the yeast towers; prediction vs result ("Argus predicted 60 s → 60.4 s"); a claim-checker moment where a wrong AI number gets struck through and corrected.
- **Credibility signals:** "Every number on screen is from a real run" caption; labelled replays with recording dates; a validation slide (Argus mm vs ruler, switch time vs stopwatch); the public replay page link at the end.
- **Voiceover:** plain, first person, short sentences, no hype; captions burned in, since many viewers watch muted (see Q4).

### Gaps
- Opentrons and Emerald Cloud Lab marketing videos were not reviewed within the tool budget; no specific structure from them is cited.
- Devpost galleries for this hackathon (and video lengths or structures of past Meta hackathon winners) were not retrievable; no winning demo video was watched.
- No source gave Boxlapse's or Bromhall's on-screen graphics conventions; the craft notes above are inference.

## Q4. What 20–30 s clip formats work on X for science content?

### Takeaway
There is little science-specific evidence for X. What exists says the opening 2–5 s decide whether people keep watching, very short clips keep viewers but get less engagement, and X recommends short vertical video. For the viral prize, a 20–25 s vertical clip that opens on motion plus a number, has burned-in captions, and ends on a payoff (verdict or prediction hit) is the best-supported format.

### Cited Findings
- X's current ad specs recommend video under 15 s (up to 2:20 supported) and 9:16 vertical, with 16:9 and 1:1 also accepted — [X Help Center, creative ad specifications](https://help.x.com/en/business-and-advertising/creative-ad-specifications); an older page lists 16:9 or 1:1 and says 1:1 crops to 16:9 in the mobile timeline — [X Business (old specs)](https://business.x.com/en/help/campaign-setup/creative-ad-specifications-old)
- Standard accounts' organic videos are capped at 140 s — [Captions.ai (third party)](https://www.captions.ai/blog-post/twitter-video-length-limit)
- Many viewers watch muted, so subtitles are recommended (third party, not X) — [Requestly captioning guide](https://requestly.com/blog/video-captioning-best-practices/)
- Geoscience TikTok study: videos under 20 s had high retention but often low engagement; lecture-style videos of about 40 s to 2 min did better on reach and engagement — [Geoscience Communication 5, 363 (2022)](https://gc.copernicus.org/articles/5/363/2022/)
- A 2026 study of short research videos defines the hook as the first 2–5 s; a participant said viewers decide in about 2 s whether to keep watching — [PaperTok, arXiv 2601.18218](https://arxiv.org/pdf/2601.18218)
- Long compressed growth timelapses draw very large audiences (Boxlapse ~1.5B views; e.g. 13 days of mushrooms in 90 s) — [speakrj](https://www.speakrj.com/audit/report/UCiL9l2J57t5OG2aZ0huswZw/youtube/media-stats/); [Nerdist](https://nerdist.com/article/mushroom-growing-time-lapse-boxlapse/)

### Inferences
- **Format A, "watch it grow, measured" (best):** 0–2 s water beads already inflating with mm counters; 2–12 s six hours compressed, curves drawing; 12–18 s "salt water: NN% smaller" (placeholder; use the measured value from the run) with the verdict badge; 18–25 s card: "A webcam + a printed card. Built in 9 days with Meta's SAM 3.1 and Muse." Loopable last frame.
- **Format B, "prediction vs reality":** "Argus, make this clock go off at 60 s." Three rounds in 20 s, ending on the cup turning blue at 60.4 s. Suspense plus payoff, works muted with a big on-screen timer.
- **Format C, "the AI caught me":** a lamp left on one side; Argus refuses to call it a win and points at the lamp. Self-deprecating and different from typical AI hype clips; good as a reply or second post.
- Shoot or crop for 9:16 (or 1:1 as a safe fallback), keep text away from edges, burn in captions, no reliance on audio, and post the replay-page link in the first reply.
- 20–30 s sits between the "high retention" and "better engagement" bands in the TikTok study; the prize format forces 20–30 s anyway, so pack it with one story, not a feature tour.

### Gaps
- No peer-reviewed or platform data specific to science clips on X (as opposed to TikTok or ads) was found.
- No data on how hackathon "most viral" prizes have been won before (likes vs reposts vs views) was found; the rule that engagement counts until Nov 8 comes from the repo's own notes, not from this research.
