# Quickstart

![fargv data-flow: definition → config → env vars → CLI / GUI / Jupyter](_static/fargv_flow.svg)

Define your parameters once; fargv builds the full stack — config file,
environment variable overrides, and CLI / GUI / Jupyter interface — automatically.

## Installation

```bash
pip install fargv
```

---

## Four ways to define parameters

fargv supports four definition styles. All use `--name=value` (double-dash)
syntax and produce the same auto-generated `--help`, bash completion, config
file, and env-var overrides.

| Style | Best for |
|---|---|
| [Plain dict](#plain-dict-style) | scripts, notebooks, rapid prototypes |
| [Dict with `Fargv*` types](#dict-with-fargv-types-style) | descriptions, rich types, mandatory params |
| [Dataclass](#dataclass-style) | typed config, IDE autocompletion, larger projects |
| [Function signature](#function-signature-style) | exposing existing callables as CLI tools |

---

(plain-dict-style)=
### Plain dict

Pass a `dict` of default values — fargv infers types from the Python type of each default:

```python
import fargv

p, _ = fargv.parse({
    "name":    "world",
    "count":   1,
    "verbose": False,
    "mode":    ("fast", "slow", "medium"),   # choice; first element is default
    "files":   [],                           # variadic list (extra CLI tokens)
})
print(f"Hello, {p.name}! count={p.count}")
```

```bash
python myscript.py --name=Alice --count=3 --verbose --mode=slow a.txt b.txt
```

String parameters support `{key}` cross-references:

```python
p, _ = fargv.parse({
    "base": "/tmp",
    "out":  "{base}/results",   # resolved to /tmp/results at parse time
})
# --base=/data  →  p.out == "/data/results"
```

> **Two-element tuple pitfall** — a `tuple` whose second element is a `str`
> is treated as `(default, "description")` for `--help`, **not** as a
> two-item choice. Use three or more elements for a binary choice, e.g.
> `("yes", "no", "auto")`, or pass an explicit `FargvChoice`.

---

(dict-with-fargv-types-style)=
### Dict with `Fargv*` types

Replace bare literals with `Fargv*` parameter objects for descriptions,
mandatory values, and rich types. Plain literals and `Fargv*` objects can be
mixed freely in one dict.

```python
import sys, fargv

p, _ = fargv.parse({
    "weights": fargv.FargvStr(fargv.REQUIRED,
                   description="Path to pretrained weights (mandatory)"),
    "epochs":  fargv.FargvInt(100,
                   description="Total training epochs"),
    "lr":      fargv.FargvFloat(0.01),
    "arch":    fargv.FargvChoice(["resnet50", "vit_b16", "efficientnet"],
                   description="Model architecture"),
    "img_size":fargv.FargvTuple((int, int), default=(640, 640),
                   description="Input resolution (width height)"),
    "log":     fargv.FargvStream(sys.stderr,
                   description="Log destination (file path, stderr, or stdout)"),
    "verbose": fargv.FargvInt(0, short_name="v", is_count_switch=True),
    "ckpts":   fargv.FargvPositional(default=[],
                   description="Extra checkpoint files to evaluate"),
})
print(f"Training {p.arch}  weights={p.weights}  img_size={p.img_size}")
```

```bash
python train.py --weights=model.pt --lr=1e-4 --img_size="(1280,1280)" -vv a.pt b.pt
```

---

(dataclass-style)=
### Dataclass

Pass a `@dataclass` **class** (not an instance) — the return value is an
instance of your class, so every IDE autocompletes `cfg.lr`, `cfg.arch`, etc.

```python
from dataclasses import dataclass
import fargv

@dataclass
class Config:
    data_root:  str   = "/datasets/imagenet"
    arch:       str   = "resnet50"
    "Model architecture identifier."    # bare string literal → shown in --help
    epochs:     int   = 90
    lr:         float = 0.1
    amp:        bool  = False

cfg, _ = fargv.parse(Config)
print(f"Training {cfg.arch} for {cfg.epochs} epochs")   # cfg.arch autocompletes
```

```bash
python train.py --arch=vit_b16 --epochs=30 --amp
```

**Mandatory fields** — omit the default:

```python
@dataclass
class InferConfig:
    checkpoint: str           # no default → mandatory on the CLI
    threshold:  float = 0.5
```

---

(function-signature-style)=
### Function signature

Pass any callable — fargv introspects its type-annotated signature and uses
the docstring in `--help`:

```python
import fargv

def train(
    corpus:    str,
    tokeniser: str  = "wordpiece",
    vocab:     int  = 30_000,
    lower:     bool = True,
) -> None:
    """Tokenise *corpus* and save the resulting vocabulary."""
    print(f"tokenising {corpus!r}  vocab={vocab}  lower={lower}")

p, _ = fargv.parse(train)
train(**vars(p))
```

```bash
python tok.py --corpus=/data/wiki.txt --vocab=50000
```

Use `parse_and_launch` to parse and call in one step:

```python
fargv.parse_and_launch(train)
```

Or invoke any importable callable without writing a script at all:

```bash
python -m fargv numpy.linspace --start=0 --stop=6.283 --num=8
```

![python -m fargv numpy.linspace in a terminal](_static/fargv_bash.png)

---

## Parameter types (quick reference)

| Default / class | CLI example |
|---|---|
| `False` / `FargvBool` | `--verbose` or `--verbose=false` |
| `42` / `FargvInt` | `--count=3` |
| `3.14` / `FargvFloat` | `--lr=1e-4` |
| `"hello"` / `FargvStr` | `--name=Alice` |
| `("a","b","c")` / `FargvChoice` | `--mode=b` |
| `[]` / `FargvPositional` | `a.txt b.txt` (leftover tokens) |
| `FargvPath` | `--model=/weights/best.pt` |
| `FargvExistingFile` | `--weights=model.pt` *(must exist)* |
| `FargvInputStream` | `--data=corpus.txt` or `--data=stdin` |
| `FargvOutputStream` | `--out=results.txt` or `--out=stdout` |
| `FargvTuple` | `--size=(640,480)` |
| `{"sub": {...}}` / `FargvSubcommand` | `prog train --lr=0.1` |

See [parameter_types.md](parameter_types.md) for the full reference.

---

## Built-in flags

Every script gets these automatically (all can be disabled individually):

| Flag | Alias | Description |
|---|---|---|
| `--help` | `-h` | Print help and exit |
| `--bash_autocomplete` | — | Print bash completion script and exit |
| `--verbosity` | `-v` | Verbosity level (`-vvvv` = 4) |
| `--config` | — | Load a JSON / YAML / TOML / INI config file |

---

## Subcommands

A nested dict whose values are dicts is automatically a subcommand tree:

```python
p, _ = fargv.parse({
    "shared_flag": True,
    "cmd": {
        "train": {"lr": 0.01, "epochs": 10},
        "eval":  {"dataset": "val"},
    },
})
# python prog.py train --lr=0.5 --shared_flag false
```

## GUI backends

```bash
python train.py --user_interface=tk    # Tk dialog
python train.py --user_interface=qt    # Qt/PySide dialog
```

![fargv Tk GUI — numpy.linspace](_static/fargv_linspace_tk.png)

---

## Legacy API (backwards compatibility)

Scripts written with `fargv.fargv(...)` (single-dash `-name=value` syntax)
continue to work unchanged. New scripts should use `fargv.parse`.

```python
# Single-dash legacy style — supported for backwards compatibility
p, _ = fargv.fargv({"name": "world", "count": 1, "verbose": False})
# python script.py -name=Alice -count=3 -verbose
```

See [Legacy API reference](api_legacy.md) for full details.

---

For the complete definition-style guide — including pros/cons, common
mistakes, and worked examples — see [defining_parsers.md](defining_parsers.md).
