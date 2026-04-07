---
name: focus-group
description: >
  Simulates a panel of virtual users reviewing Python/C++/JS project APIs, docs, and code.
  Use whenever the user wants to: run a focus group on an API or module, add or propose virtual users,
  audit code/docs from a user's perspective, simulate user reactions, check how accessible an interface
  is to different skill levels, or maintain VIRTUAL_USERS.md. Trigger on phrases like "focus group",
  "virtual users", "how would a biologist see this", "user perspective", "add a virtual user",
  "run the focus group", "what would Alice think", "discuss this as users", or any request to evaluate
  code/docs through the lens of realistic end-users. Companion to commisar: is aware of MANIFESTO.md
  but focuses on user-facing perspective rather than internal code philosophy.
---

# Focus Group

The Focus Group skill maintains a panel of **virtual users** in `.claude/VIRTUAL_USERS.md` and role-plays
their reactions to project APIs, docs, and interfaces. It bridges internal code quality (commisar's
domain) with external usability and adoptability.

---

## `.claude/VIRTUAL_USERS.md` Structure

```markdown
# Virtual Users

## Demographics
[2–4 paragraphs describing the broad audience: domains, skill ranges, use patterns, AI-usage habits.
Inferred from the codebase and stated project goals. Dense, no bullet soup.]

---

## Virtual Users

### [Name] — [Role]
**Gender/Age:** ...  
**Background:** 1–2 sentences on domain expertise and technical level.  
**Toolchain:** What languages/tools they use day-to-day.  
**AI usage:** None / occasional / heavy (and how: Copilot, agents, etc.)  
**Task:** The specific job they'd use this project for.  
**Status:** active | archived  

#### Review History
| Date | Target | Adopt | Effort | Utility | Clarity | Note |
|------|--------|-------|--------|---------|---------|------|
[appended by focus-group review]
```

---

## Scoring Dimensions

Each virtual user scores on a **-5 to +5** scale per dimension:

| Dimension | What it means |
|-----------|--------------|
| **Adopt** | Willingness to adopt (-5 = would avoid, +5 = would switch immediately) |
| **Effort** | Perceived effort to adopt (-5 = prohibitive, +5 = trivially easy) |
| **Utility** | Expected utility for their specific task (-5 = useless, +5 = transformative) |
| **Clarity** | Clarity of the API/docs as encountered (-5 = confusing, +5 = immediately clear) |

Custom dimensions can be added per project.

---

## Commands

### `focus-group init`
Bootstrap `.claude/VIRTUAL_USERS.md` for a new project.

**Workflow:**
1. Read project files: source tree, README, existing docs, `.claude/MANIFESTO.md` if present.
2. Infer candidate demographics (domains, skill levels, AI usage patterns).
3. Ask the user **3–5 targeted questions** to refine demographics (e.g. "Is this tool intended for
   wet-lab biologists or bioinformaticians?", "Do you expect non-programmers to use the API directly?").
4. Write the `## Demographics` section.
5. Propose 3–5 seed virtual users sampled from the demographics. Present each one-by-one for
   **yes/no approval** before writing to file. Rejected users are discarded; accepted ones are appended.
6. Write approved users to `.claude/VIRTUAL_USERS.md`.

**Demographic breadth heuristic:** Aim for diversity across: technical skill (novice → expert),
domain (e.g. biologist vs. ML engineer), AI usage (none vs. agent-heavy), seniority, and
task specificity. Avoid a panel of near-identical power users.

---

### `focus-group add-user [--random N]`
Add one or more virtual users to the panel.

- Without `--random`: Claude proposes one new user and asks for approval.
- `--random N`: Claude samples N users from the demographics distribution and presents them
  one-by-one for yes/no approval. Each approved user is appended; rejected ones are discarded.
- After approval, write the user block (without review history) to `.claude/VIRTUAL_USERS.md`.
- New users should not duplicate existing active users in role/task.

---

### `focus-group review <target> [--user NAME] [--random N] [--all]`
Audit a target (function, class, module, or doc section) through the eyes of virtual users.

**Target granularities:**
- `function <name>` — signature, docstring, argument names, return type
- `class <name>` — public interface, method naming, docstring, usage pattern
- `module <path>` — public API surface, import ergonomics, overall coherence
- `docs <file>` — a documentation file or README section

**User selection:**
- `--user Alice` — invoke a specific named user
- `--random N` — sample N active users randomly
- `--all` — invoke all active users

**Workflow:**
1. Read `.claude/VIRTUAL_USERS.md` to load selected user profiles.
2. Read the target file(s) fresh.
3. For each user, role-play their perspective given their background and task.
4. Output a **scorecard table** (see format below).
5. Append results to that user's `#### Review History` in `.claude/VIRTUAL_USERS.md`.

**Scorecard output format:**
```
FOCUS GROUP REVIEW — [target] — [date]
Granularity: [function|class|module|docs]

| User          | Role              | Adopt | Effort | Utility | Clarity | Verdict       |
|---------------|-------------------|-------|--------|---------|---------|---------------|
| Alice Navarro | Genomics postdoc  |  +3   |  -1    |  +4     |  +2     | Cautious yes  |
| Ben Okafor    | CV engineer       |  +4   |  +3    |  +3     |  +4     | Strong yes    |
| ...           |                   |       |        |         |         |               |

Panel summary: mean Adopt +3.2 · mean Effort +1.0 · mean Utility +3.5 · mean Clarity +3.0
Weakest signal: Effort — 2 users flagged onboarding friction.
```

Each user gets one terse **Verdict** phrase (e.g. "Strong yes", "Curious but wary", "Hard pass").
No prose by default — the table is the output. Use `focus-group discuss` to go deeper.

---

### `focus-group discuss <topic> [--users Alice,Ben] [--mode independent|roundtable]`
Invoke one or more users in conversational mode on a specific issue.

- `--mode independent` (default): each user speaks in character without seeing others' views.
- `--mode roundtable`: users see each other's prior statements and may respond/push back.
  Claude moderates and synthesizes at the end.

**Each user's voice should reflect:**
- Their domain vocabulary (a biologist uses different words than an ML engineer)
- Their AI usage habits (a heavy-agent user will ask "can this be tool-called?")
- Their task urgency and patience level
- Their prior review scores (if any) — they should be consistent

**Roundtable output format:**
```
ROUNDTABLE — [topic]

Alice: "I tried calling `fit()` without reading the docs first and got a cryptic KeyError.
  Coming from scikit-learn I expected keyword defaults. Effort score stays at -1."

Ben: "Agree on the error message — but the method chain is clean once you know it.
  Alice, did you check the `quick_start.ipynb`?"

Alice: "I didn't see it linked from the README."

Moderator synthesis: Discoverability of examples is the core friction. API shape is broadly
  acceptable; error messaging needs work.
```

---

### `focus-group history <user>`
Print the full review history for a named user, formatted as a readable table.
Archived users can be viewed but are flagged `[ARCHIVED]`.

---

### `focus-group archive <user>`
Set a user's status to `archived`. They are excluded from `--random` sampling and `--all` invocations
but their history is preserved. Can be re-activated by editing `.claude/VIRTUAL_USERS.md` directly.

---

## Relationship to commisar

Focus Group and Commisar are complementary:

| Commisar | Focus Group |
|----------|-------------|
| Internal code philosophy | External user perspective |
| `.claude/MANIFESTO.md` | `.claude/VIRTUAL_USERS.md` |
| "Does this follow our conventions?" | "Would a biologist adopt this?" |
| Author's point of view | Audience's point of view |

When both are active, Focus Group should read `.claude/MANIFESTO.md` to understand the project's
self-stated design intent — and flag gaps between intent and user perception.

---

## Tips

- Always read `.claude/VIRTUAL_USERS.md` fresh at the start of each task.
- Virtual users should be **consistent across sessions** — their scores and voice should not
  contradict prior history without an in-character explanation.
- When proposing new users during `init` or `add-user`, aim for the demographic gap not yet
  covered — don't fill the panel with similar profiles.
- A virtual user's task should be **specific enough to generate genuine friction** — "uses Python"
  is not a task; "runs batch genomic variant calls overnight via CLI" is.
- Scores near 0 are not neutral — prompt the user to `discuss` to surface ambivalence.
- Roundtable mode works best with 2–4 users. More than 5 becomes noise.
- Focus Group does not rewrite code. It surfaces perception gaps. commisar fixes code.
