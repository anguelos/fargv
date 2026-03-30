# Defining a Parser

fargv supports four ways to define a parser.  Each maps naturally to a
different development style and project size.  This guide walks through all
four, with pros/cons and real-world examples drawn from machine learning,
computer vision, NLP, and data analytics.

---

## 1  Plain dict with Python types

Pass a `dict` whose values are **plain Python literals**.  fargv infers the
parameter type from the default value's runtime type.

| Default value | Inferred type | CLI flag |
|---|---|---|
| `int` | integer | `--epochs 50` |
| `float` | float | `--lr 0.001` |
| `bool` | boolean switch | `--verbose` |
| `str` | string | `--output_dir ./out` |
| `tuple` (≥ 3 items) | choice | `--mode train` |
| `list` / `set` | positional list | leftover tokens |

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
    "amp":         False,     # automatic mixed precision
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
    "db_url":      "postgresql://localhost/analytics",
    "output":      "{db_url}/report",
    "format":      ("parquet", "csv", "json"),
    "date_from":   "2024-01-01",
    "date_to":     "2024-12-31",
    "dry_run":     False,
    "tables":      [],        # positional: which tables to include
})
```

**Pros**

- Absolute minimum boilerplate — works in under 60 seconds
- No imports beyond `fargv`
- Defaults read as documentation; the dict *is* the spec
- `{key}` string interpolation resolves cross-references automatically
- Auto-generated `--help`, short flags, bash completion, config file, env-var
  override — all for free

**Cons**

- No per-parameter descriptions (appear as blank in `--help`)
- Type inference can surprise: a two-element tuple is treated as
  `(default, description)`, not a choice — use three or more elements for
  choices
- No validation beyond type coercion
- IDEs cannot autocomplete `p.lr` (returns `SimpleNamespace`)

**Best for**

Quick scripts, notebooks, prototypes, and any situation where the
parameter names are self-documenting.

---

## 2  Plain dict with `FargvParam` types

Replace bare Python literals with explicit
`Fargv*` parameter objects for fine-grained control: descriptions,
mandatory parameters, stream/path types, and fixed-length tuples.

```python
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
    "log":         fargv.FargvOutputStream("stderr",
                       description="Log destination (file path or stderr/stdout)"),
    "weights":     fargv.FargvStr(fargv.REQUIRED,
                       description="Path to pretrained weights (mandatory)"),
})
print(f"Detecting with {p.arch} at {p.img_size}  weights={p.weights}")
```

```bash
python detect.py --weights=yolov8n.pt --epochs=50 --img_size="(1280, 1280)"
python detect.py --weights=yolov8l.pt --log=train.log --augment false
```

```python
# ── NLP: fine-tune a language model ──────────────────────────────────────────
p, _ = fargv.parse({
    "model_name":  fargv.FargvStr("bert-base-uncased",
                       description="HuggingFace model identifier"),
    "train_file":  fargv.FargvExistingFile(fargv.REQUIRED,
                       description="Training data (jsonl, one example per line)"),
    "output_dir":  fargv.FargvStr("./finetuned",
                       description="Directory to save the fine-tuned model"),
    "task":        fargv.FargvChoice(["classification", "ner", "qa", "summarisation"],
                       description="Fine-tuning task type"),
    "max_length":  fargv.FargvInt(512,
                       description="Maximum token sequence length"),
    "epochs":      fargv.FargvInt(3),
    "lr":          fargv.FargvFloat(2e-5),
    "fp16":        fargv.FargvBool(False,
                       description="Enable 16-bit mixed precision"),
})
```

**Pros**

- Per-parameter `--help` descriptions
- Rich types: `FargvExistingFile`, `FargvOutputStream`, `FargvTuple`, …
- Mandatory parameters (`fargv.REQUIRED`) are explicit and self-documenting
- Still fully compatible with the lazy dict approach — mix both in one dict

**Cons**

- More verbose than bare literals
- Still returns `SimpleNamespace` by default — no IDE property autocompletion
- Requires importing individual `Fargv*` classes

**Best for**

Production scripts where `--help` quality matters, parameters that must
exist on disk, or when the type system (streams, paths, tuples) adds real
value.

---

## 3  Function signature

Pass any **callable** as the definition.  fargv introspects its signature
using `inspect` and `typing.get_type_hints`, inferring one parameter per
argument.  Arguments without defaults become mandatory CLI flags.

```python
import fargv

# ── NLP: callable-based tokeniser benchmark ──────────────────────────────────
def tokenise(
    corpus_path: str,
    tokeniser:   str  = "wordpiece",
    vocab_size:  int  = 30_000,
    lower_case:  bool = True,
    output_dir:  str  = "./tokeniser_out",
) -> None:
    """Tokenise *corpus_path* and save the resulting vocabulary."""
    print(f"tokenising {corpus_path!r}  vocab={vocab_size}  lower={lower_case}")
    # ... real implementation ...

p, _ = fargv.parse(tokenise)
tokenise(**vars(p))
```

```bash
python tok.py --corpus_path=/data/wiki.txt --vocab_size=50000
python tok.py --corpus_path=/data/cc.txt --tokeniser=bpe --lower_case false
```

```python
# ── Data Analytics: callable wraps a pandas pipeline ────────────────────────
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
    result = df.groupby(group_by)[metric].sum().reset_index()
    result.to_csv(output_csv, index=False)

p, _ = fargv.parse(aggregate, non_defaults_are_mandatory=True)
aggregate(**vars(p))
```

```python
# ── ML: expose any callable from the standard library or third party ─────────
# No wrapper code required — fargv reads the signature directly.
import fargv
p, _ = fargv.parse(sorted, given_parameters=["prog", "--reverse"])
# Works with python -m fargv too:
#   python -m fargv numpy.linspace -s 0 -S 6.283 --num 8
```

**Pros**

- Zero duplication: the function's own signature *is* the parser definition
- Works on any callable — your own functions, stdlib, or third-party
- Docstring is available for documentation generators
- Natural fit for `python -m fargv module.function` workflows
- Type annotations drive both the CLI and the function call

**Cons**

- Requires type annotations on every parameter for accurate type coercion;
  unannotated parameters default to `FargvStr`
- `*args` / `**kwargs` raise an error unless
  `fn_def_tolerate_wildcards=True`
- Parameters whose default is `None` and have no annotation are skipped
  (type is uninferable)
- No per-parameter descriptions unless docstring parsing is used

**Best for**

Library functions you want to expose as scripts, `python -m fargv` ad-hoc
invocations, and "fire-and-forget" one-liners where the function already
documents itself.

---

## 4  Dataclass

Decorate a class with `@dataclass` and pass the **class** (not an instance)
to `fargv.parse`.  The field names, annotations, and defaults define the
parser; the return value is a properly-typed instance of that class.

```python
from dataclasses import dataclass, field
import fargv

# ── Machine Learning: distributed training config ────────────────────────────
@dataclass
class TrainConfig:
    # Data
    data_root:    str   = "/datasets/imagenet"
    num_workers:  int   = 8

    # Model
    arch:         str   = "resnet50"
    pretrained:   bool  = True

    # Optimisation
    epochs:       int   = 90
    lr:           float = 0.1
    weight_decay: float = 1e-4
    amp:          bool  = False

    # Infrastructure
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
# ── CV: image segmentation inference ────────────────────────────────────────
@dataclass
class InferConfig:
    checkpoint:   str          # mandatory — no default
    images_dir:   str  = "/data/val"
    output_dir:   str  = "./predictions"
    threshold:    float = 0.5
    half:         bool  = False
    batch_size:   int   = 1

cfg, _ = fargv.parse(InferConfig, non_defaults_are_mandatory=True)
# cfg.checkpoint is guaranteed to be set — no if/else needed
```

```python
# ── NLP: evaluation harness ──────────────────────────────────────────────────
@dataclass
class EvalConfig:
    model_dir:    str          # mandatory
    test_file:    str          # mandatory
    task:         str  = "classification"
    batch_size:   int  = 32
    max_length:   int  = 512
    output_json:  str  = "results.json"
    verbose:      bool = False

cfg, _ = fargv.parse(EvalConfig, non_defaults_are_mandatory=True)
```

```python
# ── Data Analytics: ETL pipeline ─────────────────────────────────────────────
from dataclasses import dataclass, field
from typing import List

@dataclass
class ETLConfig:
    source_db:    str        = "postgresql://localhost/raw"
    target_db:    str        = "postgresql://localhost/warehouse"
    tables:       List[str]  = field(default_factory=list)
    batch_rows:   int        = 10_000
    dry_run:      bool       = False
    parallelism:  int        = 4

cfg, _ = fargv.parse(ETLConfig)
```

**Pros**

- **Full IDE autocompletion**: the return type is `TrainConfig` (or whatever
  class you defined) — pyright, mypy, and PyCharm all know every attribute
  and its type without any manual annotation
- **`isinstance` checks work**: `assert isinstance(cfg, TrainConfig)`
- **Reusable as a config object** throughout the codebase: pass `cfg` to any
  function that accepts `TrainConfig`
- **`field(default_factory=…)` supported** for mutable defaults (lists, dicts)
- **Mandatory fields** expressed naturally: omit the default value entirely
- Integrates cleanly with `dataclasses.asdict`, `json.dumps`, `pydantic`, etc.

**Cons**

- Slightly more boilerplate than a plain dict for trivial scripts
- Type annotations are required for accurate CLI coercion
- Rich fargv types (`FargvExistingFile`, `FargvTuple`, `FargvOutputStream`)
  are not directly expressible as dataclass field types — use
  [approach 2](#2-plain-dict-with-fargvparam-types) when you need them
- `{key}` string interpolation is not supported (no cross-references between
  fields)

**Best for**

Any project where IDE support, type safety, and re-using the config object
across modules matter.  This is the recommended approach for production ML
training scripts, research codebases, and larger applications.

---

## Choosing the right approach

| | Dict (plain) | Dict (FargvParam) | Function | Dataclass |
|---|:---:|:---:|:---:|:---:|
| Boilerplate | minimal | low | none* | low |
| IDE autocomplete | ❌ | ❌ | ❌ | ✅ |
| Per-param descriptions | ❌ | ✅ | via docstring | ❌ |
| Rich types (path, stream, tuple) | ❌ | ✅ | partial | ❌ |
| Mandatory params | ❌ | ✅ | ✅ | ✅ |
| Reusable typed config object | ❌ | ❌ | ❌ | ✅ |
| `{key}` interpolation | ✅ | ✅ | ❌ | ❌ |
| Works with existing callables | ❌ | ❌ | ✅ | ❌ |

\* the function itself is the definition; no wrapper needed.

In practice many scripts start with a plain dict and graduate to a
dataclass as the project grows — the migration is a mechanical
rename-and-annotate.
