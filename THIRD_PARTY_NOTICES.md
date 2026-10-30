# Third-party notices

Argus includes or adapts material from the projects below. Each keeps its own license.

## Claude Code skills in `.claude/skills/` (copied unchanged)

| Skill folder | Source (pinned commit) | License |
| --- | --- | --- |
| experimental-design | K-Dense-AI/scientific-agent-skills @ 5f2bc03 | MIT (K-Dense Inc.) |
| statistical-power | K-Dense-AI/scientific-agent-skills @ 5f2bc03 | MIT (K-Dense Inc.) |
| uncertainty-and-units | K-Dense-AI/scientific-agent-skills @ 5f2bc03 | MIT (K-Dense Inc.) |
| hypothesis-generation | K-Dense-AI/scientific-agent-skills @ 5f2bc03 | MIT (K-Dense Inc.) |
| scientific-critical-thinking | K-Dense-AI/scientific-agent-skills @ 5f2bc03 | MIT (K-Dense Inc.) |
| opencv | tondevrel/scientific-agent-skills @ 6e89d9e | MIT |
| trackpy-particle-tracking | jaechang-hits/SciAgent-Skills @ 55c1bd3 | CC BY 4.0 (jaechang-hits) |

## Prompts adapted from skills

`prompts/system/scientific-rules.md` and `prompts/deep/verdict-critique.md` are condensed adaptations of the hypothesis-generation and scientific-critical-thinking skills from K-Dense-AI/scientific-agent-skills (MIT). The what-if-oracle skill (CC BY-NC-SA 4.0) was deliberately not copied or adapted.

## Published data re-analysed in the demo (not in this repository)

| Dataset | Credit | License | Used as |
| --- | --- | --- | --- |
| Genze & Grimm germination dataset, v3 ([Mendeley Data](https://data.mendeley.com/datasets/4wkt6thgp6/3), doi:10.17632/4wkt6thgp6.3) | Genze N., Bharti R., Grieb M., Schultheiss S.J., Grimm D.G. (2020), "Accurate machine learning-based germination detection, prediction and quality assessment of three grain crops", *Plant Methods* 16:157 | CC BY 4.0 | Six dishes (rye runs 1–2, pearl millet runs 1–2) cropped and tiled by Argus into a virtual plate; the dataset's per-seed labels are compared with Argus's counts |

The data stays out of git (`data/` is ignored). To rebuild the plate, download `GermPredDataset.zip` (840 MB, no login) from the Mendeley page into `data/datasets/genze/`, then run from `worker/`:

```bash
uv run python -m argus dataset genze --zip ../data/datasets/genze/GermPredDataset.zip --out ../data/datasets/genze/plate
```

The command checks the archive's SHA-256 against the published file before using it. Argus credits the data under every frame of it in the app.

---

## License: K-Dense-AI/scientific-agent-skills

```
MIT License

Copyright (c) 2025 K-Dense Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.```

## License: tondevrel/scientific-agent-skills

```
MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## License: jaechang-hits/SciAgent-Skills

```
Creative Commons Attribution 4.0 International (CC BY 4.0)

Copyright (c) 2024 jaechang-hits

You are free to:
  Share — copy and redistribute the material in any medium or format
  Adapt — remix, transform, and build upon the material for any purpose, even commercially.

Under the following terms:
  Attribution — You must give appropriate credit, provide a link to the license,
  and indicate if changes were made. You may do so in any reasonable manner, but
  not in any way that suggests the licensor endorses you or your use.

No additional restrictions — You may not apply legal terms or technological
measures that legally restrict others from doing anything the license permits.

Full license text: https://creativecommons.org/licenses/by/4.0/legalcode

---

This project references claude-scientific-skills
(https://github.com/K-Dense-AI/claude-scientific-skills),
Copyright (c) 2025 K-Dense-AI, licensed under the MIT License.

This project references Biomni
(https://github.com/snap-stanford/Biomni),
Copyright (c) 2025 Biomni Team (Stanford SNAP), licensed under the Apache License 2.0.
The sgRNA Design Guide content adapted in `skills/molecular-biology/sgrna-design-guide`
is licensed under CC BY 4.0.
```

Full CC BY 4.0 text: https://creativecommons.org/licenses/by/4.0/legalcode
