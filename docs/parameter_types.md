# Parameter Types

This page maps Python literal types to their fargv equivalents, and lists
fargv parameter types that have no Python literal counterpart.

## Mapping table

| Python literal | Example | `Fargv*` class | Legacy dict default | OO CLI syntax | Notes |
|---|---|---|---|---|---|
| `bool` | `False` | `FargvBool` | `False` | `--verbose` (bare toggles default) | Must be checked before `int` — `bool` subclasses `int` in Python |
| `int` | `42` | `FargvInt` | `42` | `--count=3` or `--count 3` | Set `is_count_switch=True` for `-vvvv` style |
| `float` | `3.14` | `FargvFloat` | `3.14` | `--lr=0.001` | Accepts scientific notation (`1e-3`) |
| `str` | `"hello"` | `FargvStr` | `"hello"` | `--name=Alice` | Supports `{key}` cross-parameter interpolation |
| `tuple` (3+ items) | `("a","b","c")` | `FargvChoice` | `("a","b","c")` | `--mode=b` | First element is the default; 2-item tuple is `(default, description)` |
| `list` | `[]` | `FargvPositional` | `set()` | `file1.txt file2.txt` | Collects unmatched tokens; no `--` prefix on CLI |
| `set` | `set()` | `FargvVariadic` | `set()` | `file1.txt file2.txt` | Same as `list`; legacy API uses `set` for variadics |
| `dict` (all vals dicts) | `{"train":{...}}` | `FargvSubcommand` | — | `prog train --lr=0.1` | Git-style subcommand; flag style `--cmd=train` also works |
| *(none)* | — | `FargvInputStream` | — | `--data=corpus.txt` | Defaults to `sys.stdin`; accepts file paths or `stdin` |
| *(none)* | — | `FargvOutputStream` | — | `--out=results.txt` | Defaults to `sys.stdout`; accepts file paths, `stdout`, or `stderr` |
| *(none)* | — | `FargvStream` | — | `--log=out.txt` | Base class; use `FargvInputStream` / `FargvOutputStream` directly |
| *(none)* | — | `FargvPath` | — | `--model=/weights/best.pt` | Returns `pathlib.Path`; optional existence/non-existence validation |
| *(none)* | — | `FargvExistingFile` | — | `--model=/weights/best.pt` | `FargvPath(must_exist=True)` |
| *(none)* | — | `FargvNonExistingFile` | — | `--out=/tmp/new.pt` | `FargvPath(must_not_exist=True)` |
| *(none)* | — | `FargvFile` | — | `--out=/data/run/pred.txt` | `FargvPath(parent_must_exist=True)` |
| `Tuple[int,int]` annotation | *(function param)* | `FargvTuple` | — | `--size=(640,480)` | Parsed via `ast.literal_eval`; single-element shorthand `"640"` → `(640,)` |
| *(none)* | — | `FargvCountSwitch` | — | `-vvvv` | `FargvInt(is_count_switch=True)`; counts repeated short flags |

## Notes

### Two-element tuple `(default, "description")`

When a tuple has **exactly two elements** and the second is a `str`, fargv
interprets it as `(default_value, "help text")` — not as a choice.  Use
three or more elements for a choice parameter:

```python
# WRONG — treated as (default="fast", description="slow"):
{"mode": ("fast", "slow")}

# CORRECT — three-element choice:
{"mode": ("fast", "slow", "medium")}

# Attaching help text to a non-choice:
{"lr": (0.001, "Learning rate")}
```

### `FargvStr` — cross-parameter interpolation

String parameters support `{key}` references to other string parameters.
Resolution is lazy (evaluated when `.value` is read) and recursive:

```python
from fargv import parse
p, _ = parse({"base": "/tmp/run", "out": "{base}/predictions"})
# --base=/data  →  p.out == "/data/predictions"
```

### `FargvChoice`

The first element of the list / tuple is the default.  All elements must be
strings.  Passing a value not in the list raises `FargvError`.

```python
from fargv.parameters import FargvChoice
FargvChoice(["adam", "sgd", "rmsprop"], name="opt")
# --opt=sgd  →  "sgd"
# --opt=lion  →  FargvError
```

### `FargvPositional`

At most one variadic parameter is supported per parser.  All tokens that
do not start with the long or short prefix are routed to it.

```python
from fargv import parse
p, _ = parse({"files": [], "count": 0})
# prog --count=2 a.txt b.txt  →  p.files == ["a.txt", "b.txt"]
```

### `FargvSubcommand` — nested sub-parsers

Mirrors `git`-style subcommands.  The value is always a dict:
`{"name": "<subcommand>", "result": {<sub-namespace>}}`.

With `subcommand_return_type="flat"` (default), the result is merged into the
top-level namespace and the subcommand key holds the selected name:

```python
from fargv import parse
p, _ = parse(
    {"cmd": {"train": {"lr": 0.01}, "eval": {"dataset": "val"}}},
    given_parameters=["prog", "train", "--lr=0.5"],
)
# p.cmd == "train",  p.lr == 0.5
```

### `FargvStream` — text I/O streams

Accepts a file path, or the keywords `stdin` / `stdout` / `stderr`.
The stream mode (`r` / `w` / `a`) is determined by the default value:
`sys.stdin` → `r`, `sys.stdout`/`sys.stderr` → `w`.

```python
from fargv.parameters import FargvOutputStream
out = FargvOutputStream(name="out")
# --out=results.txt  →  open("results.txt", "w")
# --out=stdout       →  sys.stdout
```

### `FargvPath` hierarchy

```
FargvPath                       (pathlib.Path, no validation)
├── FargvExistingFile           (must_exist=True)
├── FargvNonExistingFile        (must_not_exist=True)
└── FargvFile                   (parent_must_exist=True)
```

### `FargvTuple` — typed fixed-length tuples

Parsed from a single string using `ast.literal_eval`.
Single-element shorthand: `"224"` → `(224,)` for `element_types=(int,)`.
Optional tuples: `"()"` → `None` when `optional=True`.

```python
from fargv.parameters import FargvTuple
p = FargvTuple((int, int), name="size")
p.ingest_value_strings("(640, 480)")
# p.value == (640, 480)
```

Type annotations in function signatures are also supported:

```python
from typing import Tuple, Optional
from fargv import parse

def train(lr: float = 0.01, size: Tuple[int, int] = (224, 224)):
    ...

p, _ = parse(train)
```

### `FargvInt` as a count switch

Set `is_count_switch=True` to count repeated short flags:

```python
from fargv.parameters import FargvInt
v = FargvInt(0, name="verbosity", short_name="v", is_count_switch=True)
# -vvvv          →  4
# --verbosity=3  →  3
```
