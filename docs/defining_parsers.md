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
| `list` | positional list | leftover tokens |

```python
import fargv

# ── Machine Learning: train a classifier ─────────────────────────────────────
p, _ = fargv.parse({
    "data_dir":    "/datasets/imagenet",
    "output_dir":  "{data_dir}/checkpoints",   # {key} interpolation
    "model":       ("resnet50", "vit_b16", "efficientnet_b0"),
    "epochs":      90,
    "lr":          0.1,
    "batch_size":  256,
    "amp":         False,
    "workers":     8,
    "files":       [],        # positional: extra paths, if any
})
print(f"Training {p.model} for {p.epochs} epochs  lr={p.lr}  amp={p.amp}")
```

```bash
python train.py --model=vit_b16 --epochs=30 --amp
python train.py --data_dir=/data/imagenet --lr=0.01 --batch_size=128
```

```python
# ── Data Analytics: run a report pipeline ────────────────────────────────────
p, _ = fargv.parse({
    "db_url":    "postgresql://localhost/analytics",
    "format":    ("parquet", "csv", "json"),
    "date_from": "2024-01-01",
    "date_to":   "2024-12-31",
    "dry_run":   False,
    "tables":    [],
})
```

**Common mistakes**

```python
# ✗ set() works as positional in legacy API but is ambiguous — prefer list
"files": set()

# ✓ Use list
"files": []

# ✓ A two-element tuple of strings IS a two-choice enum — consistent with 3+
"mode": ("train", "eval")          # choice: train | eval
"mode": ("train", "eval", "test")  # choice: train | eval | test
```

**Pros**

- Absolute minimum boilerplate — works in under 60 seconds
- `{key}` string interpolation resolves cross-references automatically
- Auto-generated `--help`, short flags, bash completion, config file, env-var
  override — all for free
- Defaults read as documentation; the dict *is* the spec

**Cons**

- No per-parameter descriptions (appear blank in `--help`)
- No rich types: streams, paths, fixed-length tuples, count-switches
- IDEs cannot autocomplete `p.lr` (returns `SimpleNamespace`)
- No mandatory parameters (every key must have a default)

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
    "annotations": fargv.FargvExistingFile("/data/coco/instances_train.json",
                       description="COCO annotations JSON file (must exist)"),
    "output_dir":  fargv.FargvStr("{images_dir}/../runs",
                       description="Where to write checkpoints and logs"),
    "arch":        fargv.FargvChoice(["yolov8n", "yolov8s", "yolov8m", "yolov8l"],
                       description="Model architecture"),
    "img_size":    fargv.FargvTuple((int, int), default=(640, 640),
                       description="Input resolution (width height)"),
    "epochs":      fargv.FargvInt(100,
                       description="Total training epochs"),
    "lr0":         fargv.FargvFloat(0.01,
                       description="Initial learning rate"),
    "augment":     fargv.FargvBool(True,
                       description="Enable mosaic / colour-jitter augmentation"),
    "log":         fargv.FargvStream(sys.stderr,
                       description="Log destination (file path, stderr, or stdout)"),
    "weights":     fargv.FargvStr(fargv.REQUIRED,
                       description="Path to pretrained weights (mandatory)"),
    "verbosity":   fargv.FargvInt(0, short_name="v", is_count_switch=True,
                       description="Verbosity level (-vvv = 3)"),
    "checkpoints": fargv.FargvPositional(default=[],
                       description="Checkpoint files to evaluate"),
})
print(f"Detecting with {p.arch} at {p.img_size}  weights={p.weights}")
```

```bash
python detect.py --weights=yolov8n.pt --epochs=50 --img_size="(1280, 1280)"
python detect.py --weights=yolov8l.pt --log=train.log --augment false -vv
python detect.py --weights=yolov8l.pt a.pt b.pt c.pt   # positional checkpoints
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

**Pros**

- Per-parameter `--help` descriptions
- Rich types: `FargvExistingFile`, `FargvStream`, `FargvTuple`, `FargvPositional`,
  count-switch (`is_count_switch=True`), …
- Mandatory parameters (`fargv.REQUIRED`) are explicit and self-documenting
- `{key}` string interpolation still works for `FargvStr` values
- Mix with plain literals in one dict — no need to convert everything

**Cons**

- More verbose than bare literals
- Still returns `SimpleNamespace` — no IDE property autocompletion
- Requires importing individual `Fargv*` classes

---

## 3  Function signature

**When to use**: library functions you want to expose as scripts,
`python -m fargv module.function` ad-hoc invocations, and situations where
the function already documents itself.

Pass any **callable** as the definition.  fargv introspects its signature
using `inspect` and `typing.get_type_hints`, inferring one parameter per
argument.

```python
import fargv

# ── NLP: tokeniser benchmark ─────────────────────────────────────────────────
def tokenise(
    corpus_path: str,
    tokeniser:   str  = "wordpiece",
    vocab_size:  int  = 30_000,
    lower_case:  bool = True,
    output_dir:  str  = "./tokeniser_out",
) -> None:
    """Tokenise *corpus_path* and save the resulting vocabulary."""
    print(f"tokenising {corpus_path!r}  vocab={vocab_size}  lower={lower_case}")

p, _ = fargv.parse(tokenise)
tokenise(**vars(p))
```

```bash
python tok.py --corpus_path=/data/wiki.txt --vocab_size=50000
python tok.py --corpus_path=/data/cc.txt --tokeniser=bpe --lower_case false
```

```python
# ── Data Analytics: pandas pipeline ─────────────────────────────────────────
import pandas as pd

def aggregate(
    input_csv:  str,
    group_by:   str  = "region",
    metric:     str  = "revenue",
    output_csv: str  = "aggregated.csv",
    dropna:     bool = True,
) -> None:
    df = pd.read_csv(input_csv)
    if dropna:
        df = df.dropna(subset=[metric])
    df.groupby(group_by)[metric].sum().reset_index().to_csv(output_csv, index=False)

p, _ = fargv.parse(aggregate, non_defaults_are_mandatory=True)
aggregate(**vars(p))
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
def model(paths=fargv.FargvPositional([])):  # fargv sees a FargvPositional object,
    ...                                       # not recognised; treated as FargvStr
```

**Pros**

- Zero duplication: the function's own signature *is* the parser definition
- Works on any callable — your own functions, stdlib, or third-party
- Docstring is available for `--help` display
- Natural fit for `python -m fargv module.function` workflows

**Cons**

- Requires type annotations on every parameter for accurate coercion;
  unannotated parameters default to `FargvStr`
- `*args` / `**kwargs` require `fn_def_tolerate_wildcards=True`
- Parameters whose default is `None` and have no annotation are skipped
- Rich fargv types (`FargvPositional`, `FargvStream`, …) are not usable as
  function defaults
- No `{key}` string interpolation

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
import fargv

# ── Machine Learning: distributed training ───────────────────────────────────
@dataclass
class TrainConfig:
    data_root:    str   = "/datasets/imagenet"
    num_workers:  int   = 8
    arch:         str   = "resnet50"
    pretrained:   bool  = True
    epochs:       int   = 90
    lr:           float = 0.1
    weight_decay: float = 1e-4
    amp:          bool  = False
    gpus:         int   = 1
    output_dir:   str   = "./runs"

cfg, _ = fargv.parse(TrainConfig)
# cfg is TrainConfig — IDE autocompletes cfg.lr, cfg.arch, etc.
print(f"Training {cfg.arch} for {cfg.epochs} epochs on {cfg.gpus} GPU(s)")
```

```bash
python train.py --arch=vit_b16 --epochs=30 --amp --gpus=4
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
(`FargvPositional`, `FargvStream`, `FargvInt(is_count_switch=True)`, …),
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
    checkpoints: list  = fargv.FargvPositional(default=[],
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
    paths = fargv.FargvPositional(default=[])  # NOT a dataclass field; ignored

# ✓ Add a type annotation
@dataclass
class Good:
    paths: list = fargv.FargvPositional(default=[])

# ✗ Trailing comma — makes the value a one-element tuple, not a FargvParameter
@dataclass
class Bad2:
    paths: list = fargv.FargvPositional(default=[]),   # <- comma!
    # paths is now (FargvPositional(...),) — fargv sees a tuple, infers FargvChoice

# ✓ No trailing comma
@dataclass
class Good2:
    paths: list = fargv.FargvPositional(default=[])

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

**Pros**

- **Full IDE autocompletion**: the return type is your class — pyright, mypy,
  and PyCharm all know every attribute and its type
- **`isinstance` checks work**: `assert isinstance(cfg, TrainConfig)`
- **Reusable as a typed config** throughout the codebase
- **Rich types** (`FargvPositional`, `FargvStream`, count-switches) expressible
  via `Fargv*` instance defaults (approach 4b)
- **Mandatory fields** expressed naturally: omit the default value entirely
- Integrates cleanly with `dataclasses.asdict`, `json.dumps`, etc.

**Cons**

- Slightly more boilerplate than a plain dict for trivial scripts
- Type annotations are required for accurate CLI coercion (and for
  `@dataclass` to register the field at all)
- `{key}` string interpolation is not supported across fields
- `Fargv*` instance defaults (approach 4b) share the same object across all
  class instances — this is harmless for fargv's use but may surprise you
  if you construct `TrainConfig()` directly elsewhere

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
| `{key}` interpolation | ✅ | ✅ | ❌ | ❌ |
| Works with existing callables | ❌ | ❌ | ✅ | ❌ |

† the function itself is the definition; no wrapper needed.

In practice many scripts start with a plain dict and graduate to a dataclass
as the project grows — the migration is a mechanical rename-and-annotate.
