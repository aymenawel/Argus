<!-- Method card: colony-spread recipe. Sent with every call for this recipe, after the rules. -->

# Method: colony spread

**What is measured.** SAM finds the "microbial colony" in each dish, one dish at a time. Argus reports its area in square millimetres, sized by the Argus Card or by the dish rim of known width. A dish reads zero until SAM first finds the colony; after that, a picture where SAM finds nothing is a miss (no reading, a "missed" event). A picture SAM couldn't outline is a gap too. SAM misses small, faint colonies, so an early zero is not proof that nothing grew.

**Typical curve.** A quiet start after the colony is placed, then a fast-spreading stretch, then a slowdown as the colony nears the dish wall or the agar dries. A swarm can spread in bursts (rings or branches) rather than smoothly.

**What counts as a real change.** A difference in area or spreading speed between conditions that holds over several readings and is bigger than the difference between dishes of the same condition. With one dish per condition, say that the difference may just be how dishes differ.

**Other possible causes and how to check them.**
- Temperature: dishes nearer a heat source spread faster.
- Drying: drier agar slows spreading.
- Starting drop: a bigger starting drop starts a bigger colony; compare the first readings.
- Place on the shelf: light and warmth differ across a scanner or incubator shelf.
- Agar batch: agar from one pour varies; repeat dishes per condition matter more than any single dish.
