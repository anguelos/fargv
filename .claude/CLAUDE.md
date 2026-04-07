# fargv — Project Instructions for Claude

## Claude Instructions

At the start of every session, read these skill files:
- `.claude/skills/commisar/SKILL.md`
- `.claude/skills/focus-group/SKILL.md`

When the user says "commisar" , follow the commisar skill instructions.
When the user says "focus-group", follow the focus-group skill instructions.


## Project Overview

`fargv` is a Python CLI argument parser library — easy to use, zero required effort from the user.

- **Package location**: `fargv/` (migration to `src/fargv/` is planned but not done)
- **PyPI name**: `fargv`
- **Author**: Anguelos Nicolaou (anguelos.nicolaou@gmail.com)
- **Docs**: Sphinx with MyST (Markdown only, no `.rst`)

---

## Architecture

### Legacy API (`fargv/fargv_legacy.py`)
The original function-based API. Exposed as `from fargv import fargv` (the `fargv.fargv` callable).

**Key design**: pass a `default_switches` dict; types are inferred from the Python type of the default value:
- `int` → integer param
- `float` → float param
- `bool` → boolean flag (bare `-flag` sets to True)
- `str` → string param (supports `{key}` interpolation across params)
- `tuple` → choice param (first element is default)
- `set` → positional param (catch-all for unmatched tokens, tab-separated internally)

Returns `(namespace, help_str)` — namespace is `SimpleNamespace` by default, also supports `dict` and `namedtuple`.

Built-in auto-params: `--help`/`-h`, `--bash_autocomplete`, `-v` (verbosity).
Backward compatibility is **utmost importance**.

### New API (`fargv/parse.py`)
Main entry point: `fargv.parse(definition)` — returns `(namespace, help_str)`.

Additional entry points: `fargv.parse_and_launch(fn)`, `fargv.parse_here()`.

`definition` can be:
- **dataclass class** — recommended; returns a dataclass instance (see below)
- **dict** — type-inferred from Python literals (same rules as legacy, but double-dash flags)
- **callable** — type-inferred from type-annotated function signature
- **`ArgumentParser`** — used directly (advanced/low-level)

#### Dataclass API (recommended for new code)

```python
from dataclasses import dataclass, field
import fargv

@dataclass
class Config:
    """Program description shown in --help."""
    lr: float = 0.01
    "Learning rate."           # bare string literal → shown as param description in --help
    epochs: int = 10
    dataset: tuple = ("mnist", "cifar10", "svhn")  # tuple default → FargvChoice (first is default)
    cmd: dict = field(default_factory=lambda: {     # nested dict default → FargvSubcommand
        "train": {"output": "model.pt"},
        "eval":  {"checkpoint": "model.pt"},
    })
    "Subcommand."

p, _ = fargv.parse(Config, subcommand_return_type="nested")
# p is a Config instance
# p.dataset is the chosen string; p.cmd is SimpleNamespace(name="train", output="model.pt")
```

Type inference for dataclass fields:
- `int` annotation or `int` default → `FargvInt`
- `float` annotation or `float` default → `FargvFloat`
- `bool` annotation or `bool` default → `FargvBool`
- `str` annotation or `str` default → `FargvStr`
- `tuple` default → `FargvChoice` (first element is default)
- `list` / `set` default → `FargvPositional`
- nested `dict` default (all values are dicts/callables/`ArgumentParser`) → `FargvSubcommand`
- `FargvParameter` instance as default → used as-is (set via `field(default_factory=...)`)
- Fields with no default are mandatory (`REQUIRED` sentinel internally)
- Bare string literals immediately after a field definition become the parameter description in `--help`

#### Dict API

```python
p, _ = fargv.parse({
    "lr": 0.01,
    "mode": ("train", "eval", "export"),   # FargvChoice
    "cmd": {                                # FargvSubcommand
        "fit":     {"output": "model.pt"},
        "predict": {"checkpoint": "model.pt"},
    },
})
```

#### Function API

```python
def train(lr: float = 0.01, epochs: int = 10): ...

p, _ = fargv.parse(train)
# or shorthand:
fargv.parse_and_launch(train)
```

### Auto-params (injected automatically, can be disabled per-param)
- `--help` / `-h` — print help and exit
- `--verbosity` / `-v` — integer verbosity level (`is_count_switch=True`)
- `--bash_autocomplete` — print bash completion script and exit
- `--config <path>` — load JSON/YAML/TOML/INI config; default: `~/.{appname}.config.json`
- `--user_interface` — choose `cli` / `tk` / `qt` (when GUI backends are installed)

### Override priority
coded default → config file → env var (`APPNAME_PARAMNAME` uppercased) → CLI/UI

### Subcommands
A nested dict where all values are dicts/callables/`ArgumentParser` is inferred as `FargvSubcommand`.
The subcommand token may appear anywhere in argv; flags are routed by name not position.

`subcommand_return_type` options for `fargv.parse(...)`:
- `"flat"` (default) — sub-params merged into top-level namespace; subcommand key = selected name string
- `"nested"` — subcommand key holds `SimpleNamespace(name=..., **sub_params)`
- `"tuple"` — returns `((name, sub_ns, parent_ns), help_str)`

**With dataclass definitions, use `"nested"` or `"tuple"`** — `"flat"` drops sub-params not declared as dataclass fields.

### Parameter classes (all exported from `fargv` top-level)

| Class | Notes |
|---|---|
| `FargvInt` | integer; `is_count_switch=True` enables `-vvvv` = 4 style |
| `FargvFloat` | float |
| `FargvBool` | boolean flag |
| `FargvStr` | string with `{key}` cross-interpolation |
| `FargvChoice` | enum from a list; first item is default |
| `FargvPositional` | ordered list of unmatched positional tokens |
| `FargvStream` / `FargvInputStream` / `FargvOutputStream` | file/stdin/stdout/stderr |
| `FargvPath` / `FargvExistingFile` / `FargvNonExistingFile` / `FargvFile` | path with validation |
| `FargvTuple` | fixed-length typed tuple (via `ast.literal_eval`) |
| `FargvSubcommand` | git-style nested sub-parser |
| `REQUIRED` | sentinel marking a parameter as mandatory |

---

## Planned Features

1. **`src/` layout migration** — move `fargv/` → `src/fargv/`
2. **Sphinx docs** — MyST (Markdown), auto-generated from docstrings
3. **Sub-command design with dataclasses** — nested dataclass fields as subcommand definitions
4. **Google Fire-like decorator** — `@fargv.cli` wrapping any function
5. **Dynamic return type** — re-parseable namespace object

---

## Caution

- `fargv/__init__.py` imports `fargv_legacy` — exists at `fargv/fargv_legacy.py`
- `setup.py` calls `open('README.md').read()` — `README.md` is deleted; fix before publishing
- `.pypi_token` exists — **never commit this file**

---

## Conventions

- Python 3.6+ target (see `setup.py` classifiers)
- No external runtime dependencies (currently `install_requires=[]`)
- Tests in `test/unittest/`; coverage excludes `src/` folder
- Only `.md` files for documentation (Sphinx via MyST)
- Env var naming: `APPNAME_PARAMNAME` (uppercased, auto-derived from program name)
