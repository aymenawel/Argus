<!-- Method card: colour-reaction recipe. Sent with every call for this recipe, after the rules. -->

# Method: colour-change reaction

**What is measured.** Each vessel's liquid is found by SAM as the concept "liquid". Argus reads its mean colour in CIELAB, corrected against the Argus Card's neutral patches, and reports ΔE00: the colour difference from that vessel's own colour at the start of the run. A rule event ("switch") marks the moment a vessel crosses the recipe's threshold.

**Typical curve.** Flat at the start, then a rise that is either sudden (a clock reaction switching) or gradual (dye spreading, an indicator fading), then a plateau when the colour stops changing. Compare when vessels rise and how high they settle, treatment against control at the same time.

**What counts as a real change.** A rise well above the noise floor in the MEASUREMENTS block, lasting more than a moment. A single jump that comes back is more likely a hand, a shadow or a bubble than chemistry.

**Rival explanations and their checks.**
- Lighting or camera exposure: was colour corrected against the card throughout? An uncorrected stretch weakens any colour claim made from it.
- Mixing: a stirred or bumped vessel changes faster for reasons other than the treatment; check the interventions.
- Temperature: vessels warm or cool towards the room over time; a control at the same temperature as the room helps separate this.
- Position: liquid nearer a lamp or window can read differently; note the vessel's place in the row.
