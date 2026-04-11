# Defining a Parser

A **parser definition** is the complete set of parameters employed by a
program, expressed as a dict, a dataclass, a function signature, or a
pre-built `ArgumentParser`.  fargv supports four parser definition styles,
each mapping naturally to a different development style and project size.

---

## 1  Plain dict with Python literals

**When to use**: prototypes, notebooks, and scripts where parameter names are
self-documenting and you want the least possible boilerplate.

Pass a `dict` whose values are **plain Python literals** as the parser
definition.  fargv infers the parameter type from the default value's runtime
type.

| Default value | Inferred type | CLI form |
|---|---|---|
| `int` | integer | `--epochs 50` |
| `float` | float | `--lr 0.001` |
| `bool` | boolean switch | `--verbose` / `--verbose false` |
| `str` | string | `--output_dir ./out` |
| `tuple` (≥ 3 items) | choice (first = default) | `--mode train` |
| `list` | variadic list | leftover tokens |

```python
import fargv

# ── Computer Vision: object detection pipeline ───────────────────────────────
p, _ = fargv.parse({
    "data_dir":   "/datasets/coco",
    "output_dir": "{data_dir}/runs",                                # {key} string reference
    "arch":       ("yolov8n", "yolov8s", "yolov8m", "yolov8l"),    # choice (first = default)
    "img_size":   fargv.FargvTuple((int, int), default=(640, 640)), # typed tuple (needs FargvTuple)
    "epochs":     50,
    "lr":         0.01,
    "amp":        False,
    "extras":     [],                                               # variadic: unmatched tokens
    "cmd": {                                                        # subcommand
        "train": {"warmup": 3, "mosaic": True},
        "eval":  {"split": "val", "half": False},
    },
})
print(f"arch={p.arch}  img_size={p.img_size}  out={p.output_dir}")
```

> `FargvTuple` is the one feature that requires an explicit `Fargv*` object even in
> the plain-dict style — there is no Python literal that encodes "fixed-length typed tuple"
> without being mistaken for a choice (3-element tuple) or a list.

```bash
python detect.py --arch=yolov8m --img_size=1280,1280 train --warmup=5
python detect.py --data_dir=/data/coco eval --split=test
```

```python
# ── Data Analytics: run a report pipeline ────────────────────────────────────
p, _ = fargv.parse({
    "db_url":    "postgresql://localhost/analytics",
    "report":    ("parquet", "csv", "json"),
    "date_from": "2024-01-01",
    "date_to":   "{date_from}",     # echoes date_from unless overridden
    "dry_run":   False,
    "tables":    [],
    "cmd": {
        "export": {"compress": True},
        "preview": {"rows": 20},
    },
})
```

**Common mistakes**

```python
# ✗ set() works as variadic in legacy API but is ambiguous — prefer list
"files": set()

# ✓ Use list
"files": []

# ✓ A two-element tuple of strings IS a two-choice enum — consistent with 3+
"mode": ("train", "eval")          # choice: train | eval
"mode": ("train", "eval", "test")  # choice: train | eval | test
```

**When to use**

- Prototypes and research scripts where speed of writing matters most
- Notebooks and one-off data-pipeline scripts
- Teaching / demos where the definition should be self-evident

**When to avoid**

- When `--help` quality matters for end users (no descriptions on params)
- When you need mandatory parameters, file-existence checks, or streams
- When you want IDE autocompletion on the result namespace

| | |
|---|---|
| ✅ Pros | ❌ Cons |
| Minimum boilerplate — a plain dict | No per-parameter `--help` descriptions |
| `{key}` string interpolation | No rich types (streams, paths, tuples) |
| Self-documenting defaults | No mandatory parameters |
| Full auto-params for free | `p.lr` is untyped `SimpleNamespace` |

**How do I…**

*Make a parameter a choice?* — use a tuple with ≥ 3 elements:

```python
{"mode": ("train", "eval", "test")}   # first element is default
```

*Add a description to a single parameter without switching styles?* — use the
2-element `(default, "description")` shorthand:

```python
{"lr": (0.01, "Initial learning rate")}
```

*Collect extra CLI tokens?* — use an empty list:

```python
{"files": []}   # python script.py a.txt b.txt → p.files == ["a.txt", "b.txt"]
```

*Switch to a richer style for just one parameter?* — mix a `Fargv*` object
into the dict alongside plain literals:

```python
{"lr": 0.01, "weights": fargv.FargvStr(fargv.REQUIRED)}
```

---

## 2  Plain dict with `Fargv*` types

**When to use**: production scripts where `--help` quality matters, parameters
that must exist on disk, streams, fixed-length tuples, or verbosity counters.

Replace bare Python literals with explicit `Fargv*` parameter objects.
You can mix both styles freely in one dict.

```python
import sys
import fargv

# ── Computer Vision: object-detection training ───────────────────────────────
p, _ = fargv.parse({
    "images_dir":  fargv.FargvStr("/data/coco/images",
                       description="Root directory of COCO-style images"),
    "output_dir":  fargv.FargvStr("{images_dir}/../runs",          # {key} string reference
                       description="Output dir (inherits images_dir by default)"),
    "annotations": fargv.FargvExistingFile("/data/coco/instances_train.json",
                       description="COCO annotations JSON (must exist)"),
    "arch":        fargv.FargvChoice(["yolov8n", "yolov8s", "yolov8m", "yolov8l"],
                       description="Model architecture"),          # choice
    "img_size":    fargv.FargvTuple((int, int), default=(640, 640),
                       description="Input resolution WxH"),        # fixed tuple
    "log":         fargv.FargvStream(sys.stderr,
                       description="Log destination (file path, stderr, or stdout)"),
    "weights":     fargv.FargvStr(fargv.REQUIRED,
                       description="Pretrained weights path (mandatory)"),
    "verbosity":   fargv.FargvInt(0, short_name="v", is_count_switch=True,
                       description="Verbosity level (-vvv = 3)"),
    "checkpoints": fargv.FargvVariadic(default=[],
                       description="Extra checkpoint files to evaluate"),  # variadic
    "cmd": {                                                               # subcommand
        "train": {"lr": 0.01, "epochs": 100, "amp": False},
        "eval":  {"split": "val", "half": False},
    },
})
print(f"arch={p.arch}  img_size={p.img_size}  out={p.output_dir}")
```

```bash
python detect.py --weights=yolov8n.pt train --epochs=50 --amp
python detect.py --weights=yolov8l.pt --img_size=1280,1280 -vv eval --split=test
python detect.py --weights=yolov8l.pt a.pt b.pt c.pt   # variadic checkpoints
```

```python
# ── NLP: fine-tune a language model ──────────────────────────────────────────
p, _ = fargv.parse({
    "model_name": fargv.FargvStr("bert-base-uncased",
                      description="HuggingFace model identifier"),
    "train_file": fargv.FargvExistingFile(fargv.REQUIRED,
                      description="Training data (jsonl, one example per line)"),
    "task":       fargv.FargvChoice(["classification", "ner", "qa", "summarisation"],
                      description="Fine-tuning task type"),
    "max_length": fargv.FargvInt(512),
    "epochs":     fargv.FargvInt(3),
    "lr":         fargv.FargvFloat(2e-5),
    "fp16":       fargv.FargvBool(False,
                      description="Enable 16-bit mixed precision"),
})
```

**Common mistakes**

```python
import sys

# ✗ FargvStream / FargvOutputStream do NOT accept string keywords as defaults
#   — strings are only valid on the CLI, not at construction time
"log": fargv.FargvOutputStream("stderr")   # raises FargvError

# ✓ Pass the actual sys object
"log": fargv.FargvStream(sys.stderr)       # default = stderr
"out": fargv.FargvOutputStream()           # default = stdout
"inp": fargv.FargvInputStream()            # default = stdin

# ✗ Forgetting REQUIRED is a sentinel, not a string
"weights": fargv.FargvStr("REQUIRED")      # default is the literal string "REQUIRED"

# ✓
"weights": fargv.FargvStr(fargv.REQUIRED)
```

**When to use**

- Production scripts where `--help` quality and clear error messages matter
- When you need mandatory parameters, file-existence validation, or streams
- When mixing one or two rich parameters into an otherwise plain dict

**When to avoid**

- When you need IDE autocompletion on the result (use dataclass instead)
- For trivial scripts where the extra verbosity slows you down

| | |
|---|---|
| ✅ Pros | ❌ Cons |
| Per-parameter `--help` descriptions | More verbose than bare literals |
| Rich types (path, stream, tuple, count-switch) | `SimpleNamespace` result — no IDE autocompletion |
| Explicit mandatory parameters (`REQUIRED`) | Requires importing `Fargv*` classes |
| Mix freely with plain literals | |

**How do I…**

*Make a parameter mandatory?*

```python
{"weights": fargv.FargvStr(fargv.REQUIRED, description="model weights")}
```

*Add a count-switch verbosity flag?*

```python
{"verbose": fargv.FargvInt(0, short_name="v", is_count_switch=True)}
# -vvv sets verbose=3
```

*Require a file to exist at parse time?*

```python
{"config": fargv.FargvExistingFile(fargv.REQUIRED)}
```

*Accept a stream (file, stdout, stderr)?*

```python
import sys
{"log": fargv.FargvStream(sys.stderr)}
# --log=out.txt  or  --log=stdout
```

---

## 3  Function signature

**When to use**: library functions you want to expose as scripts,
`python -m fargv module.function` ad-hoc invocations, and situations where
the function already documents itself.

Pass any **callable** as the definition.  fargv introspects its signature
using `inspect` and `typing.get_type_hints`, inferring one parameter per
argument.

```python
from typing import Tuple
import fargv

# ── Image processing pipeline ────────────────────────────────────────────────
def process(
    data_dir:   str,                                 # mandatory string param (no default)
    output_dir: str   = "/tmp/out",                  # string param with {key} interpolation
    codec             = ("h264", "h265", "vp9"),     # choice: unannotated tuple → FargvChoice
    img_size:   Tuple[int, int] = (1920, 1080),      # FargvTuple via Tuple annotation
    inputs:     list  = [],                          # FargvVariadic via list annotation
    cmd               = {                            # FargvSubcommand: unannotated dict default
        "encode": {"bitrate": 4000, "crf": 23},
        "decode": {"format": "yuv420"},
    },
) -> None:
    """Process video files with configurable codec and filter pipeline."""
    print(f"codec={codec}  size={img_size}  dest={output_dir}")

p, _ = fargv.parse(process, non_defaults_are_mandatory=True)
process(**vars(p))
```

```bash
python proc.py --data_dir=/media encode --bitrate=8000
python proc.py --data_dir=/media --codec=h265 --img_size=3840,2160 decode
python proc.py --data_dir=/media a.mp4 b.mp4   # variadic inputs
```


```python
# ── NLP: tokeniser benchmark ─────────────────────────────────────────────────
import fargv

def tokenise(
    corpus_path: str,
    tokeniser:   str  = "wordpiece",
    vocab_size:  int  = 30_000,
    lower_case:  bool = True,
    output_dir:  str  = "./tokeniser_out",
) -> None:
    """Tokenise *corpus_path* and save the resulting vocabulary."""
    print(f"tokenising {corpus_path!r}  vocab={vocab_size}  lower={lower_case}")

p, _ = fargv.parse(tokenise, non_defaults_are_mandatory=True)
tokenise(**vars(p))
```

```python
# ── Expose any callable directly ─────────────────────────────────────────────
import fargv
p, _ = fargv.parse(sorted, given_parameters=["prog", "--reverse"])
# Or: python -m fargv numpy.linspace -s 0 -S 6.283 --num 8
```

**Common mistakes**

```python
# ✗ *args / **kwargs cause an error unless you opt in
def bad(x: int, *args, **kwargs): ...
p, _ = fargv.parse(bad)                             # raises FargvError

# ✓ Opt in explicitly
p, _ = fargv.parse(bad, fn_def_tolerate_wildcards=True)

# ✗ Unannotated parameter with None default is silently skipped
def ambiguous(x: int, device=None): ...  # 'device' has no annotation + None default
p, _ = fargv.parse(ambiguous)            # 'device' does not appear in help or result

# ✓ Add an annotation
def clear(x: int, device: str = "cpu"): ...

# ✗ Rich fargv types cannot be expressed as function defaults — they appear as
#   their plain Python value on the CLI (no description, no special behaviour)
def model(paths=fargv.FargvVariadic([])):  # fargv sees a FargvVariadic object,
    ...                                       # not recognised; treated as FargvStr
```

**When to use**

- Library functions you want to expose as CLI tools with no wrapper
- Ad-hoc invocation via `python -m fargv module.callable`
- When the function already documents itself via docstring and annotations

**When to avoid**

- When you need IDE autocompletion on the parsed result (use dataclass)
- When parameters need rich types like streams or path validation
- When the function has unannotated `None` defaults you depend on

| | |
|---|---|
| ✅ Pros | ❌ Cons |
| Zero duplication — signature *is* the definition | Type annotations required for accurate coercion |
| Works on any callable (stdlib, third-party) | `*args`/`**kwargs` need `fn_def_tolerate_wildcards=True` |
| Docstring appears in `--help` | `None` defaults without annotations are silently skipped |
| Natural fit for `python -m fargv` | Rich `Fargv*` types not usable as function defaults |

**How do I…**

*Make parameters without defaults mandatory?*

```python
def run(host: str, port: int = 8080): ...
p, _ = fargv.parse(run, non_defaults_are_mandatory=True)
# python run.py --host=localhost
```

*Parse and call in one step?*

```python
fargv.parse_and_launch(train)
```

*Call from inside the function itself?*

```python
def train(lr: float = 0.01, epochs: int = 10):
    p, _ = fargv.parse_here()   # resolves own signature
    print(p.lr, p.epochs)
```

*Handle `*args` or `**kwargs`?*

```python
p, _ = fargv.parse(fn, fn_def_tolerate_wildcards=True)
```

---

## 4  Dataclass

**When to use**: any project where IDE autocompletion, type safety, and
re-using the config object across modules matter.  The return value is an
instance of your class — `cfg.lr`, `cfg.arch` autocomplete in every IDE.

Decorate a class with `@dataclass` and pass the **class** (not an instance)
to `fargv.parse`.

### 4a  Plain field defaults

For parameters expressible as plain Python literals, annotate the field and
set the default directly.  fargv infers the `Fargv*` type from the annotation
and the default value.

```python
from dataclasses import dataclass, field
from typing import Tuple
import fargv

# ── Image processing pipeline ────────────────────────────────────────────────
@dataclass
class ProcessConfig:
    data_dir:   str   = "/data/raw"
    output_dir: str   = "{data_dir}/processed"    # {key} string reference — resolved after parsing
    codec:      tuple = ("h264", "h265", "vp9")   # choice: tuple annotation → FargvChoice
    img_size:   Tuple[int, int] = (1920, 1080)    # FargvTuple via Tuple[int,int] annotation
    inputs:     list  = field(default_factory=list)  # variadic: list annotation → FargvVariadic
    cmd:        dict  = field(default_factory=lambda: {  # subcommand: dict of dicts
        "encode": {"bitrate": 4000, "crf": 23},
        "decode": {"format": "yuv420"},
    })

cfg, _ = fargv.parse(ProcessConfig)
# cfg is ProcessConfig — IDE autocompletes cfg.codec, cfg.img_size, etc.
print(f"codec={cfg.codec}  size={cfg.img_size}")
```

```bash
python proc.py --codec=h265 --img_size=3840,2160 encode --crf=18
python proc.py decode --format=rgb24
python proc.py a.mp4 b.mp4   # variadic inputs
```


```python
# ── Machine Learning: distributed training ───────────────────────────────────
@dataclass
class TrainConfig:
    data_root:    str   = "/datasets/imagenet"
    arch:         str   = "resnet50"
    epochs:       int   = 90
    lr:           float = 0.1
    amp:          bool  = False

cfg, _ = fargv.parse(TrainConfig)
print(f"Training {cfg.arch} for {cfg.epochs} epochs  lr={cfg.lr}")
```

```bash
python train.py --arch=vit_b16 --epochs=30 --amp
```

```python
# ── CV: mandatory fields (no default) ────────────────────────────────────────
@dataclass
class InferConfig:
    checkpoint:  str           # mandatory — no default
    images_dir:  str  = "/data/val"
    threshold:   float = 0.5
    half:        bool  = False

cfg, _ = fargv.parse(InferConfig, non_defaults_are_mandatory=True)
```

### 4b  `Fargv*` parameter instances as defaults

When you need a rich type that has no plain Python literal equivalent
(`FargvVariadic`, `FargvStream`, `FargvTuple`, `FargvInt(is_count_switch=True)`, …),
assign a `Fargv*` instance as the field default.  fargv detects it and uses
it directly, ignoring the annotation (which exists only to satisfy the type
checker and `@dataclass`).

```python
import sys
from dataclasses import dataclass
import fargv

# ── ML checkpoint tool ────────────────────────────────────────────────────────
@dataclass
class CheckpointConfig:
    # Plain defaults — inferred from annotation + value
    output_dir:  str   = "./runs"
    dry_run:     bool  = False

    # Rich types — FargvParameter instance IS the parameter definition
    checkpoints: list  = fargv.FargvVariadic(default=[],
                             description="Checkpoint .pt files to inspect")
    verbosity:   int   = fargv.FargvInt(0, short_name="v", is_count_switch=True,
                             description="Verbosity level (-vvv = 3)")
    log:         object = fargv.FargvStream(sys.stderr,
                             description="Log stream (path, stderr, or stdout)")

cfg, _ = fargv.parse(CheckpointConfig)
# cfg.checkpoints is a list, cfg.verbosity is an int, cfg.log is a file-like
```

```bash
python tool.py a.pt b.pt --output_dir=./out -vv --log=run.log
```

### 4c  Field docstrings

Per-field descriptions appear in `--help` output and can be attached directly
in the parser definition as **attribute docstrings** — a bare string literal
immediately after the field.  Two placement styles are recognised:

| Style | Syntax | Recognised by |
|---|---|---|
| Next-line | string on the following line | fargv, Sphinx, PyCharm, Pylance |
| Same-line | string after `;` on the same line | fargv only |

```python
from dataclasses import dataclass
import fargv

@dataclass
class TrainConfig:
    # ── No description ────────────────────────────────────────────────────────
    output_dir: str = "./runs"

    # ── Same-line (compact; recognised by fargv, not by Sphinx/IDEs) ─────────
    epochs: int = 90; "Total number of training epochs."

    # ── Next-line (conventional; recognised by fargv, Sphinx, and IDEs) ──────
    lr: float = 0.1
    "Initial learning rate."

    arch: str = "resnet50"
    """
    Model architecture identifier.
    Any torchvision-compatible name is accepted.
    """

cfg, _ = fargv.parse(TrainConfig)
```

Field docstrings are a fallback: if the field default is a `Fargv*` instance
with an explicit `description=`, that takes precedence and the docstring is
ignored.

```python
@dataclass
class MixedConfig:
    # description= wins over the docstring
    lr: float = fargv.FargvFloat(0.1, description="Learning rate (explicit wins)")
    "This docstring is ignored."

    # no description= → docstring is used
    epochs: int = fargv.FargvInt(90, short_name="e")
    "Total training epochs."
```

**Common mistakes**

```python
# ✗ Missing type annotation — @dataclass ignores class attributes without one,
#   so fargv never sees this field
@dataclass
class Bad:
    paths = fargv.FargvVariadic(default=[])  # NOT a dataclass field; ignored

# ✓ Add a type annotation
@dataclass
class Good:
    paths: list = fargv.FargvVariadic(default=[])

# ✗ Trailing comma — makes the value a one-element tuple, not a FargvParameter
@dataclass
class Bad2:
    paths: list = fargv.FargvVariadic(default=[]),   # <- comma!
    # paths is now (FargvVariadic(...),) — fargv sees a tuple, infers FargvChoice

# ✓ No trailing comma
@dataclass
class Good2:
    paths: list = fargv.FargvVariadic(default=[])

# ✗ FargvStream default must be a sys object, not a string keyword
@dataclass
class Bad3:
    log: object = fargv.FargvStream("stderr")   # raises FargvError at import time

# ✓
import sys
@dataclass
class Good3:
    log: object = fargv.FargvStream(sys.stderr)

# ✗ Passing a dataclass instance instead of the class itself
cfg = TrainConfig()
p, _ = fargv.parse(cfg)   # raises TypeError — pass the class, not an instance

# ✓
p, _ = fargv.parse(TrainConfig)
```

**When to use**

- Any project where IDE autocompletion, mypy/pyright, or `isinstance` checks matter
- When the config object is passed around multiple modules
- When you want mandatory fields expressed as plain missing defaults

**When to avoid**

- For throwaway scripts (a plain dict is faster to write)

| | |
|---|---|
| ✅ Pros | ❌ Cons |
| Full IDE autocompletion on result | More boilerplate than a plain dict for tiny scripts |
| `isinstance(cfg, MyConfig)` works | Type annotations required on every field |
| Reusable typed config across modules | |
| Rich types via `Fargv*` instance defaults | `Fargv*` defaults share one object per class |
| Mandatory fields: just omit the default | |
| Works with `dataclasses.asdict`, `json.dumps` | |

**How do I…**

*Make a field mandatory?* — omit the default:

```python
@dataclass
class Config:
    checkpoint: str        # no default → required on CLI
    threshold: float = 0.5
```

*Add a description to a field?* — bare string literal immediately after:

```python
@dataclass
class Config:
    lr: float = 0.1
    "Initial learning rate."   # shown in --help
```

*Add a rich type (stream, count-switch, variadic)?*

```python
import sys
from dataclasses import dataclass
from typing import Tuple
import fargv

@dataclass
class Config:
    verbose:  int          = fargv.FargvInt(0, short_name="v", is_count_switch=True)
    log:      object       = fargv.FargvStream(sys.stderr)
    files:    list         = fargv.FargvVariadic(default=[])
    img_size: Tuple[int, int] = (640, 640)   # plain default, Tuple annotation → FargvTuple
```

*Use subcommands in a dataclass?*

```python
from dataclasses import dataclass, field
import fargv

@dataclass
class Config:
    cmd: dict = field(default_factory=lambda: {
        "train": {"lr": 0.01},
        "eval":  {"dataset": "val"},
    })

cfg, _ = fargv.parse(Config, subcommand_return_type="nested")
```

---

## Choosing the right approach

| | Dict (literals) | Dict (`Fargv*`) | Function | Dataclass |
|---|:---:|:---:|:---:|:---:|
| Boilerplate | minimal | low | none† | low |
| IDE autocomplete on result | ❌ | ❌ | ❌ | ✅ |
| Per-param descriptions | ❌ | ✅ | via docstring | field docstrings or `Fargv*` defaults |
| Rich types (stream, path, tuple, count-switch) | ❌ | ✅ | ❌ | ✅ (4b) |
| Mandatory params | ❌ | ✅ | ✅ | ✅ |
| Reusable typed config object | ❌ | ❌ | ❌ | ✅ |
| `{key}` interpolation | ✅ | ✅ | ✅ | ✅ |
| Works with existing callables | ❌ | ❌ | ✅ | ❌ |

† the function itself is the definition; no wrapper needed.

In practice many scripts start with a plain dict and graduate to a dataclass
as the project grows — the migration is a mechanical rename-and-annotate.
