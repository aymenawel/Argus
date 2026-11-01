<!-- Method card: seed-germination recipe. Sent with every call for this recipe, after the rules. -->

# Method: seed germination

**What is measured.** SAM finds "mung bean" and "root" in each jar. Argus skeletonizes the roots and reports total root length per jar in millimetres, calibrated by the Argus Card. A jar reads zero until SAM first finds a root; after that, finding no root is a miss (a gap with a "missed" event). A failed segmentation is a gap too.

**Typical curve.** A lag while the beans soak and swell, then roots appearing one by one, then roughly steady growth that may level off. Germination is uneven: a jar's total length mixes how many beans sprouted with how long their roots are.

**What counts as a real change.** Growth above the noise floor between checkpoints, seen in more than one jar of the same condition. Compare treated jars with control jars at the same time, never a jar with its own earlier self alone.

**Rival explanations and their checks.**
- Temperature: jars nearer a heat source or window grow faster.
- Uneven watering: a drier jar slows down; look for interventions and for one jar lagging alone.
- Position in the row: light and warmth differ along the row; conditions should alternate, not sit in blocks.
- Seed batch: beans from one packet vary; replicate jars per condition matter more than any single jar.
- Day and night: if the room goes dark, frames may be rejected; a gap at night is not a stop in growth.
