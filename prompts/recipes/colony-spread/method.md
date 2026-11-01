<!-- Method card: colony-spread recipe. Sent with every call for this recipe, after the rules. -->

# Method: colony spread

**What is measured.** SAM finds the "microbial colony" in each dish, one dish at a time. Argus reports its area in square millimetres, calibrated by the Argus Card or by the dish rim of stated diameter. A dish reads zero until SAM first finds the colony; after that, a scan where SAM finds nothing is a miss (no reading, a "missed" event). A failed segmentation is a gap too. SAM misses small, faint colonies, so an early zero is not proof that nothing grew.

**Typical curve.** A lag after inoculation, then a spreading phase whose area grows quickly, then a slowdown as the colony nears the dish wall or the agar dries. A swarm can spread in bursts (rings or branches) rather than smoothly.

**What counts as a real change.** A difference in area or spreading rate between conditions that holds over several readings and is larger than the spread between dishes of the same condition. With one dish per condition, say that the difference may be dish-to-dish variation.

**Rival explanations and their checks.**
- Temperature: dishes nearer a heat source spread faster.
- Agar drying: drier agar slows swarming.
- Inoculum size: a bigger starting drop starts a bigger colony; compare the first readings.
- Position on the plate: light and warmth differ across a scanner or incubator shelf.
- Plate batch: agar from one pour varies; replicate dishes per condition matter more than any single dish.
