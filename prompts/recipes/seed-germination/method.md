<!-- Method card: seed-germination recipe. Sent with every call for this recipe, after the rules. -->

# Method: seed germination

**What is measured.** SAM finds "mung bean" and "root" in each jar. Argus skeletonizes the roots and reports total root length per jar in millimetres, calibrated by the Argus Card. A jar where SAM found no root reads zero; a failed segmentation is a gap, not a zero.

**Typical curve.** A lag while the beans soak and swell, then roots appearing one by one, then roughly steady growth that may level off. Germination is uneven: a jar's total length mixes how many beans sprouted with how long their roots are.

**What counts as a real change.** Growth above the noise floor between checkpoints, seen in more than one jar of the same condition. Compare treated jars with control jars at the same time, never a jar with its own earlier self alone.

**Rival explanations and their checks.**
- Temperature: jars nearer a heat source or window grow faster; position in the row and the control jars help separate this.
- Uneven watering: a drier jar slows down for reasons other than the treatment; look for interventions and for one jar lagging alone.
- Position in the row: light and warmth differ along the row; conditions should alternate, not sit in blocks.
- Seed batch: beans from one packet vary; replicate jars per condition matter more than any single jar.
- Day and night: if the room goes dark, frames may be rejected; a gap at night is not a stop in growth.
