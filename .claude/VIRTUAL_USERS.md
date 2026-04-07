# Virtual Users

## Demographics

The primary audience is domain scientists — biologists, physicists, earth scientists, social
scientists — who write Python to automate analysis but do not think of themselves as software
engineers. They prototype locally, often in notebooks, and periodically need to harden a script
for cluster deployment or hand it to a collaborator. The CLI is a means to an end, not a craft.
They currently compromise between hardcoding values and grudgingly reaching for `argparse` when
sharing becomes unavoidable.

A secondary audience is technically fluent developers (ML engineers, data scientists, experienced
research software engineers) whose bottleneck is collaboration, not their own comfort. They know
`argparse` or `click` well but find the friction of teaching collaborators how to use a CLI
unnecessarily high. They want a parser that produces a clean, self-documenting interface without
forcing them to write boilerplate.

Both groups span local development and HPC (SLURM/PBS) environments. Notebook-to-script and
script-to-notebook portability is a real workflow, making the GUI backends and config-file features
directly relevant. AI-assisted coding (Copilot, agents) is common in the technical tier and growing
in the domain-scientist tier — copy-paste from a chatbot is a primary onboarding path for both.

---

## Virtual Users

### Miriam — Computational biology postdoc
**Gender/Age:** Female, 29
**Background:** Genomics pipeline developer; comfortable with Python and bash but self-taught, no CS degree. Shares scripts with wet-lab colleagues who have never touched a terminal.
**Toolchain:** Python, Snakemake, SLURM. Jupyter for EDA, `.py` scripts for production runs.
**AI usage:** Occasional — pastes error messages into ChatGPT, uses Copilot for boilerplate.
**Task:** Replace hardcoded file paths and parameters at the top of her pipeline scripts with a proper CLI, without intimidating the biologists she shares them with.
**Status:** active

#### Review History
| Date | Target | Adopt | Effort | Utility | Clarity | Note |
|------|--------|-------|--------|---------|---------|------|
| 2026-04-03 | defining_parsers.md (all styles) | +4/+2/+3/+1 | +5/+2/+3/-1 | +4/+3/+3/+2 | +4/+2/+3/+1 | Strong yes on dict-literal; wary of Fargv* imports; dataclass too much |

---

### Lars — Physics PhD student
**Gender/Age:** Male, 26
**Background:** Numerical simulations and data analysis; strong maths, solid Python, learned software habits informally. Has used `argparse` but finds the setup-to-payoff ratio poor for research scripts.
**Toolchain:** Python, NumPy, SciPy, matplotlib. Runs jobs on university HPC cluster. Occasionally uses Jupyter for exploration.
**AI usage:** Heavy — uses Copilot daily, sometimes runs agentic coding sessions for scaffolding.
**Task:** Parametrise simulation scripts (step size, solver, output path) so he can sweep parameters from the command line without editing source files, and submit reproducible job arrays to SLURM.
**Status:** active

#### Review History
| Date | Target | Adopt | Effort | Utility | Clarity | Note |
|------|--------|-------|--------|---------|---------|------|
| 2026-04-03 | defining_parsers.md (all styles) | +5/+3/+4/+2 | +5/+2/+4/+1 | +4/+4/+4/+3 | +4/+3/+4/+2 | Immediate adopt on dict-literal; function style natural fit |

---

### Sofia — Data analyst at a mid-size logistics company
**Gender/Age:** Female, 34
**Background:** Business/statistics background, learned Python on the job. Comfortable with pandas and Jupyter; the terminal is unfamiliar territory. Thinks of `argparse` as something "real programmers" use.
**Toolchain:** Python, pandas, Jupyter, occasionally VS Code. No HPC — everything runs locally or on a shared company server via JupyterHub.
**AI usage:** Heavy — drafts most boilerplate via ChatGPT, rarely reads docs directly.
**Task:** Convert a Jupyter analysis notebook into a script her manager can run on a schedule without her having to explain command-line flags each time.
**Status:** active

#### Review History
| Date | Target | Adopt | Effort | Utility | Clarity | Note |
|------|--------|-------|--------|---------|---------|------|
| 2026-04-03 | defining_parsers.md (all styles) | +4/+1/+2/-1 | +4/-1/+2/-2 | +3/+2/+3/+2 | +4/0/+1/-1 | Dict literal only; Fargv* and dataclass are hard pass |

---

### Kwame — Senior ML engineer
**Gender/Age:** Male, 38
**Background:** CS degree, 10 years industry experience. Uses `click` or `fire` fluently. His bottleneck is not his own comfort — it is that research collaborators and interns cannot run his training scripts without a hand-holding session.
**Toolchain:** Python, PyTorch, Docker, Git. Develops locally on a workstation, deploys to cloud GPUs. Uses config files (YAML/TOML) for experiment tracking.
**AI usage:** Moderate — uses Copilot for repetitive code, skeptical of agents for anything non-trivial.
**Task:** Wrap ML training scripts with a CLI that self-documents, supports config-file overrides for experiment reproducibility, and requires zero explanation for a collaborator cloning the repo for the first time.
**Status:** active

#### Review History
| Date | Target | Adopt | Effort | Utility | Clarity | Note |
|------|--------|-------|--------|---------|---------|------|
| 2026-04-03 | defining_parsers.md (all styles) | +2/+4/+3/+5 | +5/+3/+4/+3 | +2/+4/+3/+5 | +4/+4/+3/+4 | Prototype on dict; dataclass is the real target |

---

### Nadia — Bioinformatics core facility staff scientist
**Gender/Age:** Female, 43
**Background:** 15 years building analysis tools for researchers across departments. Writes robust, reusable Python; treats CLI design as part of software quality. Currently maintains tools built with `argparse` and is evaluating lighter alternatives.
**Toolchain:** Python, Nextflow, Conda, SLURM. No notebooks in production — everything is scripts and pipelines. Reads source code before adopting a library.
**AI usage:** None — distrusts AI-generated code for scientific reproducibility; reads docs and source.
**Task:** Evaluate fargv as a drop-in replacement for `argparse` in core facility tools that serve dozens of research groups, where CLI consistency, config-file support, and env-var overrides are non-negotiable for reproducibility.
**Status:** active

#### Review History
| Date | Target | Adopt | Effort | Utility | Clarity | Note |
|------|--------|-------|--------|---------|---------|------|
| 2026-04-03 | defining_parsers.md (all styles) | +1/+4/+1/+4 | +5/+3/+2/+3 | +2/+4/+2/+5 | +4/+3/+1/+3 | Dict too bare; Fargv* and dataclass viable; silent-skip on unannotated None is dangerous |
