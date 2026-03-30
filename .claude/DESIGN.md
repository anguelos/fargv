# fargv — Design Notes

Decisions and rationale for planned and in-progress features.
Update this file whenever a design choice is made or revised.

---

## Planned parameter types

### `FargvSubcommand`

**Default Python literal:** `dict`

A dict whose keys are subcommand names and whose values are parameter
definitions (dicts, `ArgumentParser` instances, or callables — anything
accepted by `definition_to_parser`).

#### CLI syntax

Positional-first (git-style) is the default:

```
myscript train --lr=0.1
myscript --subcommand=train --lr=0.1   # flag style, also supported
```

Both styles may be active simultaneously on the same parser.

#### Subcommand selection

- If mandatory (sentinel value or `mandatory=True` kwarg): no subcommand →
  `FargvError` at parse time.
- Otherwise: first key in the dict is the default subcommand.

#### Global parameters

Parent-level parameters are shared across all subcommands.
Defining a `FargvPositional` at the parent level while subcommands are
active raises a warning on `sys.stderr` (positional token is ambiguous
— is it a subcommand name or a positional value?).

#### Nesting

Nested subcommands are supported by design: a subcommand's own definition
may itself contain a `FargvSubcommand` entry.  No artificial depth limit.

#### Return value

`parse()` gains a `subcommand_return_type` parameter:

| Value | Shape |
|-------|-------|
| `"flat"` (default) | `ns.subcommand = "train"`, `ns.lr = 0.001`, global params merged in |
| `"nested"` | `ns.subcommand = "train"`, `ns.train.lr = 0.001` |
| `"tuple"` | `(subcommand_name, subcommand_ns, global_ns)` |

---

### `FargvInputStream` / `FargvOutputStream`

Subclasses of the existing `FargvStream`, hard-coding the mode so it is
visible in the type name and help output.

| Class | Mode | Default |
|-------|------|---------|
| `FargvInputStream` | `"r"` (text read) | `sys.stdin` |
| `FargvOutputStream` | `"w"` (text write) | `sys.stdout` |

`FargvStream` itself remains for cases where mode is inferred from the
default (e.g. an already-open file).

Binary mode and append mode are **TODO**.

---

### `FargvPath` / `FargvExistingFile` / `FargvNonExistingFile` / `FargvFile`

All return `pathlib.Path` as `.value`.

Base class:

```python
FargvPath(
    default,
    must_exist: bool = False,
    must_not_exist: bool = False,
    parent_must_exist: bool = False,
    name=None, short_name=None, description=None,
)
```

Validation runs inside `ingest_value_strings` and raises `FargvError`
immediately if the constraint is violated.

Three named subclasses:

| Class | Constraint | Typical use |
|-------|-----------|-------------|
| `FargvExistingFile` | `must_exist=True` | Input file that must already be on disk |
| `FargvNonExistingFile` | `must_not_exist=True` | Output file that must not overwrite anything |
| `FargvFile` | `parent_must_exist=True` | Output path whose parent directory must exist |

**TODO** — `FargvDir` and its variants (`FargvExistingDir`, `FargvNewDir`)
follow the same pattern but validate directories.

---

### Config-file auto-parameter

#### Motivation

Many scripts need a config file to override defaults before CLI flags are
applied.  fargv injects this automatically so the user never writes the
boilerplate.

#### Priority order

```
coded defaults  →  config file  →  env vars  →  CLI / UI
```

#### Injection

Controlled by `auto_define_config: bool = True` in `fargv.parse()`.
When enabled, two parameters are injected:

| Auto-param | Default | Effect |
|-----------|---------|--------|
| `--config` | `~/.{app_name}.config.json` | Path to JSON config; if the file exists its keys override defaults |
| `--auto_configure` | `False` (flag) | Print the current parameter set as JSON to stdout, then exit |

`app_name` is derived from `guess_program_name()`, dots and path separators
stripped.

#### Validation

A key present in the config file that does not match any defined parameter
raises `FargvError`.  (Avoids silent misconfiguration.)

#### Format

JSON for now.  The design should make it easy to add YAML / TOML / INI
later, likely via optional extras (`pip install fargv[yaml]`).  YAML and
TOML are not bundled because fargv has zero required runtime dependencies.

#### Future

Consider a `fargv_config` CLI tool (installed as a console-script entry
point) and/or a `config` built-in subcommand for reading, writing, and
diffing config files.  Deferred to later milestone.

---

### `FargvTuple` — typed tuple via `typing.Tuple`

#### Motivation

Many numerical parameters are naturally pairs or triples:
`--size 224 224`, `--crop 0 0 224 224`.  Python's `typing.Tuple` is a
natural way to express their structure.

#### CLI syntax

The entire tuple is passed as a **single string** (no space splitting):

```
--size=(224,224)
--crop=(0,0,224,224)
--offset=(-10,5)
```

Parsed with `ast.literal_eval`, so standard Python tuple syntax is accepted.

#### Supported element types

All basic Python literal types that `ast.literal_eval` handles:
`int`, `float`, `str`, `bool`, `bytes`.
The annotation `Tuple[T1, T2, ...]` drives type-checking after eval.

#### `Optional[Tuple[...]]`

`'()'` (empty tuple string) evaluates to `None`.
Any other valid tuple string is parsed normally.

#### Integration with `function_to_parser`

```python
from typing import Tuple

def crop(size: Tuple[int, int] = (224, 224)):
    ...

p, _ = fargv.parse(crop)
# CLI: --size=(640,480)
```

`_annotation_to_fargv_cls` is extended to recognise `Tuple[...]`
annotations and return `FargvTuple` with the element types baked in.

---

## TODO list

- `FargvDir`, `FargvExistingDir`, `FargvNewDir` — directory variants of
  the path types (same `FargvPath` base, `is_dir` validation flag).
- `FargvInputStream` / `FargvOutputStream` binary mode variants.
- `FargvStream` append mode.
- Config file: YAML / TOML / INI support as optional extras.
- `fargv_config` CLI tool / `config` built-in subcommand.
- `FargvTuple`: `List[T]` typed list via `typing.List` (same ast path).
- `Optional[Tuple]` full round-trip: serialise `None` back to `'()'` in
  `auto_configure` output.
- Sub-command `"nested"` and `"tuple"` return modes.
- Sub-command flag style (`--subcommand=train`) implementation.
- Sub-command: decide whether to allow a global positional alongside
  subcommands or hard-error.
- GUI modes: `"tk"`, `"qt"`, `"jupyter"` (currently raise `NotImplementedError`).
- `src/` layout migration (`fargv/` → `src/fargv/`).
- Sphinx docs for OO API.
