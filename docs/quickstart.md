# Quickstart

## Installation

```bash
pip install fargv
```

## Two APIs

fargv provides two APIs.  Both infer parameter types from default values.

| Feature | Legacy API (`fargv.fargv`) | New OO API (`fargv.parse`) |
|---|---|---|
| Flag style | `-name=value` (single dash) | `--name=value` (double dash) |
| Input | Plain dict | Dict, function, or `ArgumentParser` |
| Return | `(SimpleNamespace, help_str)` | `(SimpleNamespace, help_str)` |
| Short flags | Not supported | `-v`, combined `-vd` |
| Config file | No | Yes (`--config=path`) |
| Subcommands | No | Yes (`FargvSubcommand`) |

---

## Legacy API

Define parameters as a plain dict — types are inferred from the default values:

```python
import fargv

p, _ = fargv.fargv({
    "name":    "world",           # str
    "count":   1,                 # int
    "verbose": False,             # bool flag
    "mode":    ("fast", "slow", "medium"),  # choice, first is default
    "files":   set(),             # positional list
})

print(f"Hello, {p.name}! count={p.count}")
```

```bash
python myscript.py -name=Alice -count=3 -verbose -mode=slow file1.txt file2.txt
```

---

## New OO API

Uses `--long` / `-s` Unix-style syntax.  Accepts the same plain dict:

```python
import fargv

p, _ = fargv.parse({
    "lr":      0.001,             # float
    "epochs":  10,                # int
    "verbose": False,             # bool flag
    "mode":    ("fast", "slow", "medium"),  # choice
    "files":   [],                # positional list
})
```

```bash
python train.py --lr=1e-4 --epochs=50 --verbose data/train.txt
```

### Function-based definition

Pass a function directly — its signature is inspected to infer types:

```python
def train(lr: float = 0.01, epochs: int = 10, debug: bool = False):
    ...

p, _ = fargv.parse(train)
# python train.py --lr=1e-4 --epochs=50
```

### Mandatory parameters

Use `REQUIRED` as the default to force the user to supply a value:

```python
from fargv import parse, REQUIRED, FargvStr

p, _ = parse({"name": FargvStr(REQUIRED, name="name")})
# python script.py --name=Alice  ✓
# python script.py               → FargvError
```

---

## Parameter Types (quick reference)

| Default | Class | CLI example (OO API) |
|---|---|---|
| `False` | `FargvBool` | `--verbose` or `--verbose=true` |
| `42` | `FargvInt` | `--count=3` |
| `3.14` | `FargvFloat` | `--lr=1e-4` |
| `"hello"` | `FargvStr` | `--name=Alice` |
| `("a","b","c")` | `FargvChoice` | `--mode=b` |
| `[]` or `set()` | `FargvPositional` | `a.txt b.txt` |
| — | `FargvPath` | `--model=/weights/best.pt` |
| — | `FargvInputStream` | `--data=corpus.txt` or `--data=stdin` |
| — | `FargvOutputStream` | `--out=results.txt` or `--out=stdout` |
| — | `FargvTuple` | `--size=(640,480)` |
| `{"cmd1": {...}}` | `FargvSubcommand` | `prog train --lr=0.1` |

See [parameter_types.md](parameter_types.md) for the full reference.

---

## String Interpolation

String parameters support `{key}` references to other parameters:

```python
p, _ = fargv.parse({
    "base": "/tmp",
    "out":  "{base}/results",   # becomes /tmp/results
})
# --base=/data  →  p.out == "/data/results"
```

## Help Strings

Attach a description to any parameter using a two-element tuple:

```python
p, _ = fargv.parse({
    "epochs": (10,    "Number of training epochs"),
    "lr":     (0.001, "Learning rate"),
})
```

Run with `--help` to print the generated help message.

> **Note:** A two-element tuple where the second item is a string is always
> treated as `(default, "description")`, **not** as a two-item choice.
> Use three or more elements for a choice: `("fast", "slow", "medium")`.

---

## Path Parameters

```python
from fargv.parameters import FargvExistingFile, FargvFile

p, _ = fargv.parse({
    "model": FargvExistingFile(name="model"),   # must already exist
    "out":   FargvFile(name="out"),             # parent dir must exist
})
```

## Subcommands

```python
p, _ = fargv.parse({
    "cmd": {
        "train": {"lr": 0.01, "epochs": 10},
        "eval":  {"dataset": "val"},
    }
})
# python prog.py train --lr=0.5
# p.cmd == "train", p.lr == 0.5   (flat mode — default)
```

Control the return shape with `subcommand_return_type`:

| Value | `p.cmd` | Sub-params |
|---|---|---|
| `"flat"` (default) | selected name string | merged into top namespace |
| `"nested"` | `SimpleNamespace(name=..., **params)` | inside `p.cmd` |
| `"tuple"` | — | returns `((name, sub_ns, parent_ns), help_str)` |

## Config File

When `auto_define_config=True` (default), fargv automatically supports a JSON
config file.  Defaults < config file < CLI arguments:

```bash
# Dump current values as JSON template
python train.py --auto_configure > ~/.train.config.json

# Override defaults from config
python train.py --config=~/.train.config.json --lr=0.001
```

## Return Types

By default fargv returns a `SimpleNamespace`. Request a `dict` or
`namedtuple` with `return_type`:

```python
p, _ = fargv.parse({"n": 1}, return_type="dict")
p, _ = fargv.parse({"n": 1}, return_type="namedtuple")
```

## Environment Variable Override (Legacy API)

In the legacy API every parameter can be overridden by an environment variable
with the same name:

```bash
lr=0.001 python myscript.py
```

---

## Built-in Parameters

### Legacy API

| Flag | Alias | Description |
|---|---|---|
| `-help` | `-h` | Print help and exit |
| `-bash_autocomplete` | — | Print bash completion script and exit |
| `-v` | — | Verbosity level (integer, default 1) |

### New OO API

| Flag | Alias | Description |
|---|---|---|
| `--help` | `-h` | Print help and exit |
| `--bash_autocomplete` | — | Print bash completion script and exit |
| `--verbosity` | `-v` | Verbosity level (count-switch; `-vvvv` = 4) |
| `--config` | — | Path to a JSON config file |
| `--auto_configure` | — | Print current param values as JSON and exit |

All built-in parameters are stripped from the returned namespace.
