<!-- Method card: colour-reaction recipe. Sent with every call for this recipe, after the rules. -->

# Method: colour-change reaction

**What is measured.** SAM finds the "liquid" in each sample. Argus reads its colour, corrected against the Argus Card's grey patches, and reports the colour change in ΔE: how far the colour has moved from that sample's own colour at the start (about 1 ΔE is the smallest change an eye can see). A "set threshold was crossed" event marks the moment a sample passes the recipe's threshold.

**Typical curve.** Flat at the start, then a rise that is either sudden (a clock reaction switching) or gradual (dye spreading, an indicator fading), then levelling off when the colour stops changing. Compare when samples rise and where they level off, each against the control at the same time.

**What counts as a real change.** A rise well above the normal wobble in the MEASUREMENTS block, lasting more than a moment. A single jump that comes back is more likely a hand, a shadow or a bubble than chemistry.

**Other possible causes and how to check them.**
- Lighting or camera exposure: was colour corrected against the card throughout? A stretch without the card weakens any colour claim made from it.
- Mixing: a stirred or bumped sample changes faster for reasons that aren't the test; check the handling events.
- Temperature: samples warm or cool towards the room over time; a control at room temperature helps tell this apart.
- Position: liquid nearer a lamp or window can read differently; note the sample's place in the row.
