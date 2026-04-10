---
name: add-test
description: >
  Guides the agent through adding tests to the fargv project using the three-tier test system.
  Use whenever the user says "add a test", "write a test for", "add this to test_spec", or describes
  a bug and wants it regression-tested. The skill determines the correct tier, file, and style,
  and enforces the Tier-3 protection rule.
---

# add-test Skill

This skill governs how tests are added to `test/unittest/`.

---

## Three Tiers

### Tier 1 — Unit / Coverage
Files: `test_legacy.py`, `test_oo.py`, `test_parse.py`, `test_autocomplete.py`, `test_new_types.py`, `test_coverage.py`, `test_new_coverage.py`, `test_coverage_boost.py`

- Agent has **full agency**: add, modify, delete freely.
- Goal: maximize coverage; test individual functions/classes in isolation.
- Style: pytest classes, short methods, one assertion per test is fine.
- Place in the file that matches the module under test.

### Tier 2 — Integration
File: `test_integration.py` (does not exist yet — create when the first Tier-2 test is needed)

- Agent may modify but **must flag non-trivial changes** to the user before writing.
- Goal: test multi-module flows, CLI invocation end-to-end, config file loading, env var override chains.
- Style: scenario-named test functions, minimal mocking, real filesystem where practical.

### Tier 3 — Specification
File: `test_spec.py` (and `test_spec_*.py` if split by domain in future)

- Agent has **no agency**: never add, remove, or modify without explicit user approval in the current conversation.
- Goal: encode invariants and known-correct behaviours the user considers load-bearing.
- Style: dense, human-readable, no scaffolding noise.
  - Prefer grouping related assertions in one function over splitting into micro-tests.
  - No helper functions unless shared across 3+ tests.
  - Each test has a docstring stating the invariant, date added, and who initiated it.

---

## Tier 3 Docstring Format

Every Tier 3 test must have a docstring in this exact format:

```python
def test_something():
    """One-sentence statement of the invariant.
    Added: YYYY-MM-DD, initiated by: <name>.
    """
```

- Default initiator is **Anguelos** unless stated otherwise.
- Use today's date at time of writing.
- If the test is a regression for a known bug, add a third line: `Regression: <short description>.`

---

## Decision Procedure

When the user asks to add a test:

1. **Ask which tier** if not obvious. Default heuristic:
   - Bug regression → Tier 3 (user decides) or Tier 1 (agent decides independently)
   - Covers a new feature path → Tier 1
   - End-to-end scenario → Tier 2
   - User says "I want this guaranteed forever" → Tier 3
   - Exotic/rare-condition bug → Tier 3 (strong candidate)

2. **Identify the target file** using the tier table above.

3. **For Tier 3**: read `test_spec.py` fully, confirm the invariant is not already covered, then present the proposed test to the user for approval **before writing**.

4. **Write the test**, following the style rules for the tier.

5. **Run the test** with `pytest test/unittest/<file>.py -x -q` and confirm it passes (or fails as expected for a red-green-refactor cycle).

---

## Style Reference

### Tier 1 example
```python
class TestFargvBool:
    def test_bare_flag_sets_true(self):
        p, _ = fargv.parse({"verbose": False}, given_parameters=["prog", "--verbose"])
        assert p.verbose is True
```

### Tier 3 example
```python
def test_bool_bare_flag_is_python_true():
    """Bool flag set via bare --flag must return Python True, not a truthy string or int.
    Added: 2026-04-10, initiated by: Anguelos.
    """
    p, _ = fargv.parse({"verbose": False}, given_parameters=["prog", "--verbose"])
    assert p.verbose is True
    assert type(p.verbose) is bool
```

### Tier 3 regression example
```python
def test_choice_default_is_first_element():
    """FargvChoice default must be the first tuple element, not the last seen on argv.
    Added: 2026-04-10, initiated by: Anguelos.
    Regression: choices were resolving to the last matched token under ambiguous prefix.
    """
    p, _ = fargv.parse({"mode": ("train", "eval")}, given_parameters=["prog"])
    assert p.mode == "train"
```
