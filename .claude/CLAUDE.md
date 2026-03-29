# fargv — Project Instructions for Claude

## Project Overview

`fargv` is a Python CLI argument parser library — easy to use, zero required effort from the user.

- **Package location**: `src/fargv/` (migration from `fargv/` planned)
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

### New OO API (`fargv/oo_fargv.py`)
Class hierarchy rooted at `FargvParameter` (ABC):

| Class | Legacy equivalent | Notes |
|---|---|---|
| `FargvInt` | `int` default | |
| `FargvFloat` | `float` default | |
| `FargvBool` | `bool` default | bare flag sets True |
| `FargvStr` | `str` default | supports `{key}` cross-ref |
| `FargvChoice` | `tuple` default | first item is default |
| `FargvPositional` | `set` default | ordered list; unmatched tokens collected and assigned in postprocessing |
| `FargvStream` | *(new)* | wraps file/stdin/stdout/stderr |
| `FargvCountSwitch` | *(new)* | `-vvvv` = 4; `-vvv -v` also = 4 |

**Type inference ("intermediary representation")**: a plain Python literal implies its `Fargv*` type — `int` → `FargvInt`, `tuple` → `FargvChoice`, etc. This is how the legacy dict API maps to OO internally.

**Required parameters**: use a sentinel value (e.g. `FargvInt()` with no default, or a dedicated `REQUIRED` sentinel). No separate subclass.

**Sub-commands**: TBD — either `main_` function convention or dict-of-dicts. Undecided.

---

## Planned Features (priority order from CLAUDE_INITIAL.md)

1. **`FargvCountSwitch`** — `-vvvv` style verbosity counter
2. **Config file support** — JSON, YAML, TOML, INI (all formats); zero user effort
3. **Env var override** — auto-derived names (e.g. `SCRIPTNAME_PARAMNAME`); no annotation needed
4. **Google Fire-like decorator** — wrap any function, auto-generate CLI from its signature
5. **Dynamic return type** — special object that can be re-parsed or updated at runtime
6. **GUI / interactive mode** — auto-select: CLI in scripts, `ipywidgets` in Jupyter, explicit GUI engines (tkinter, Qt) when requested
7. **Sub-commands** — design TBD
8. **`src/` layout migration** — move `fargv/` → `src/fargv/`
9. **Sphinx docs** — MyST (Markdown), auto-generated from docstrings

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
- Env var naming: `SCRIPTNAME_PARAMNAME` (uppercased, auto-derived)
