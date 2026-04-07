---
name: commisar
description: >
  Enforces and evolves the coding philosophy of a Python or C++ project via a MANIFESTO.md file.
  Use this skill whenever the user wants to: audit code against project standards, enforce naming conventions
  or design patterns, check compliance of a function/file/module/project with its principles, improve
  code to better match the MANIFESTO, or revise the MANIFESTO itself to reflect actual code evolution.
  Trigger on phrases like "check compliance", "enforce standards", "does this follow our manifesto",
  "audit this code", "update the manifesto", "revise our principles", "commissar", "commisar",
  "what are our conventions", "does this follow our style", or any request to align code with documented
  project philosophy. Works for Python and C++ projects.
---

# Commisar

The Commisar enforces and evolves a project's **MANIFESTO.md** — a living document capturing design philosophy,
coding conventions, naming habits, UI mentality, and design patterns.

---

## MANIFESTO.md Structure

**Format principles:** The MANIFESTO is dense and scannable. Each section contains short, declarative paragraphs — no bullet soup, no padding. Every sentence earns its place. Rules are stated as facts, not suggestions. Omit sections that don't apply; rename any to fit the project's voice.

The MANIFESTO is written in a register that matches the project's culture — terse and technical for systems code, more expressive for creative tools. But always compact: if a rule needs more than 3 sentences, it's two rules.

```markdown
# Project MANIFESTO

## 1. Design Philosophy
State the 2–4 load-bearing architectural values. No elaboration beyond what a new contributor needs to make the right call when stuck. Example: "Data flows downward. State lives at the boundary. No business logic in the UI layer."

## 2. Coding Conventions
Rules that go beyond the language's default style guide. Line length, file length limits, comment philosophy (why, not what), type annotation stance. One short paragraph per topic.

## 3. Naming Conventions
State the pattern, then give a ✅ / ❌ pair. Cover: variables, functions, classes, files, modules, constants, and any domain-specific terms that must be spelled consistently.

## 4. Error Handling
How errors surface (exceptions vs result types), how they propagate (re-raise vs wrap), how they're reported (logs vs stderr vs UI). One paragraph, decisive.

## 5. UI Mentality & Design Patterns
Layout philosophy (e.g., "structure first, style second"). Component granularity. State management approach. Visual hierarchy rules. Accessibility non-negotiables. Each as its own short paragraph.

## 6. Module & Package Organization
What lives where, and why. Allowed dependency directions between modules. Import hygiene rules (no circular imports, star imports, etc.). How public API surfaces are delimited.

## 7. Testing Philosophy
What must be tested, what need not be. Test naming convention. Mocking stance. Coverage targets if any. One short paragraph each.

## 8. Dependency Philosophy
The bar for adding a dependency. Vendoring stance. Pinning policy. One short paragraph.
```

---

## The Three Modes

### Mode 1: Compliance Check

Audit code against MANIFESTO.md at different granularities.

**Workflow:**
1. Read `.claude/MANIFESTO.md` from the project (or ask user for its location).
2. Identify the granularity requested: `function`, `file`, `module`, or `project`.
3. For the target scope, read the relevant code.
4. For each MANIFESTO section, flag violations with:
   - **Severity**: `CRITICAL` (breaks core philosophy) / `WARN` (convention drift) / `NOTE` (style suggestion)
   - **Location**: file + line number or function name
   - **Violation**: what rule is broken
   - **Suggestion**: what it should look like

**Output format:**
```
COMPLIANCE REPORT — [scope: function/file/module/project]
Target: <name>
MANIFESTO version: <date or version if present>

[CRITICAL] src/renderer.py:42 — naming
  `processData()` violates snake_case convention.
  → rename to `process_data()`

[WARN] src/renderer.py — structure
  File mixes UI logic and data transformation.
  → per §6, UI components should not import from `data/`

Summary: 1 CRITICAL, 1 WARN, 0 NOTES
Overall compliance: PARTIAL
```

**Granularity guidance:**
- `function`: Check naming, docstring presence, single-responsibility, error handling
- `file`: Check structure, imports, file naming, class/function count, mixed concerns
- `module`: Check inter-module dependencies, public API surface, cohesion
- `project`: Sample across all modules; check for systemic drift

---

### Mode 2: Improve Compliance

Rewrite or refactor code to comply with MANIFESTO.md.

**Workflow:**
1. Run a compliance check first (Mode 1) to identify issues.
2. Present the list of changes to be made before applying them.
3. Apply fixes at the requested granularity.
4. For each change, annotate with which MANIFESTO rule it satisfies.
5. Do **not** change behavior — only style, structure, naming, and organization.

**When refactoring:**
- Rename symbols consistently across call sites
- Move code only if scope is `file` or above
- Flag any changes that would break public APIs as `BREAKING`
- Offer a migration note for BREAKING changes

---

### Mode 3: Revise MANIFESTO

Update MANIFESTO.md to better reflect the actual codebase, or suggest principled changes.

**Two sub-modes:**

#### 3a. Descriptive revision (code → manifesto)
"The code has evolved; update the MANIFESTO to match reality."

1. Scan the codebase for consistent patterns that contradict or aren't covered by the MANIFESTO.
2. Propose additions/amendments with reasoning.
3. Flag patterns that are inconsistent (some code does X, some does Y) — ask the user to decide which to canonize.

Output:
```
MANIFESTO REVISION PROPOSALS

§3 Naming Conventions — AMENDMENT
  Observed pattern: async functions consistently suffixed with `_async` (14 occurrences).
  Current MANIFESTO: silent on async naming.
  Proposed addition: "Async functions are suffixed with `_async` to aid greppability."

§5 UI Patterns — NEW SECTION
  Observed: all UI components follow a Presenter/View split (8 components).
  Proposed new section: [draft text here]
```

#### 3b. Prescriptive revision (philosophy → manifesto)
"I want to change our conventions; update the MANIFESTO."

1. Accept the user's stated philosophy changes.
2. Draft updated MANIFESTO sections.
3. Optionally run a compliance check to show the delta — how much existing code would need to change.

---

## Initialization: Creating a MANIFESTO from scratch

If no `.claude/MANIFESTO.md` exists:

1. Ask the user: *"Should I infer principles from the existing code, start from scratch, or both?"*
2. If inferring from code: scan for patterns across naming, structure, imports, error handling, UI.
3. Draft a MANIFESTO.md using the structure above. Write in dense, short paragraphs — declarative, no hedging, no bullet lists. Each rule is one to three sentences max.
4. Annotate each rule with confidence: `[inferred]`, `[conventional]` (language best practice), or `[stated]` (user-provided).
5. Present for review before writing.
6. Write to `.claude/MANIFESTO.md`.

**Style when writing the MANIFESTO:** Be the voice of the codebase, not a style guide committee. State rules as facts. If a rule requires a caveat, fold it into the rule or drop it. The MANIFESTO should read like a dense internal memo, not documentation.

---

## Language-specific notes

### Python
- Check for PEP8 baseline before MANIFESTO-specific rules
- Watch for: naming (`snake_case` vs `camelCase` drift), type hint consistency, docstring style (Google vs NumPy vs reStructuredText), `__init__.py` usage
- Tools to suggest if available: `ruff`, `mypy`, `pylint`

### C++
- Watch for: header guard style (`#pragma once` vs `#ifndef`), namespace conventions, `const`-correctness, RAII adherence, smart pointer usage, `.hpp` vs `.h` extension consistency
- Note: C++ projects often have stronger opinions on include order, forward declarations, and template placement — probe for these if not in MANIFESTO

---

## Tips

- Always read `.claude/MANIFESTO.md` fresh at the start of each task — don't rely on memory from prior turns.
- When the MANIFESTO is ambiguous, note the ambiguity and ask the user to clarify rather than guessing.
- Compliance reports should be **actionable**, not exhaustive. Prefer surfacing the top 5–10 issues over listing every minor infraction.
- When improving compliance, always show a diff or before/after, never silently overwrite.
- The MANIFESTO is the user's document — the Commisar proposes, the user decides.
