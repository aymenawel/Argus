<!-- Method card: general recipe. Sent with every call for this recipe, after the rules. -->

# Method: general

**What is measured.** SAM finds the "object" in each sample or region. Argus reports its area in square millimetres, sized by the Argus Card, and its average colour. A region reads zero area until the object is first found; after that, a picture where SAM finds nothing is a miss (a gap, with a "missed" event). A picture SAM couldn't outline is a gap too.

**Typical curve.** Unknown in advance: describe what the readings do (steady, rising, falling, jumping) rather than assuming a shape.

**What counts as a real change.** A change above the normal wobble that lasts several readings and is not matched by the control at the same time.

**Other possible causes and how to check them.**
- Lighting change: was colour corrected against the card throughout?
- Camera movement: a camera move is logged as an event; readings around it deserve less trust.
- Position in the picture: objects near the edges are bent out of shape by the lens.
- Handling: check the handling events near any sudden change.
