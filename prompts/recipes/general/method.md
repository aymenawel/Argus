<!-- Method card: general recipe. Sent with every call for this recipe, after the rules. -->

# Method: general

**What is measured.** SAM finds the "object" in each vessel or region. Argus reports its area in square millimetres, calibrated by the Argus Card, and its mean colour in CIELAB. A region where nothing was found reads zero area; a failed segmentation is a gap.

**Typical curve.** Unknown in advance: describe what the readings do (steady, rising, falling, jumping) rather than assuming a shape.

**What counts as a real change.** A change above the noise floor that lasts several readings and is not matched by the control at the same time.

**Rival explanations and their checks.**
- Lighting change: was colour corrected against the card throughout?
- Camera movement: a camera move is logged as an event; readings around it deserve less trust.
- Position in the frame: objects near the frame's edges are distorted by the lens.
- Handling: check the interventions near any sudden change.
