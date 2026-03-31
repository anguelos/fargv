# Return Types

fargv's `parse()` function always returns a `(result, help_str)` tuple.  The
*result* object can take several forms — choose the one that best fits your
workflow.

---

## Overview

| `return_type` | Type returned | IDE autocompletion | Mutable after parse |
|---|---|---|---|
| `"SimpleNamespace"` (default) | `types.SimpleNamespace` | limited | yes |
| `"dict"` | `dict` | no | yes |
| `"namedtuple"` | `collections.namedtuple` | no | no (immutable) |
| `"namespace"` | `FargvNamespace` | no | yes + notifications |
| dataclass (pass class as definition) | your dataclass | **full** | yes |

---

## SimpleNamespace (default)

```python
import fargv

p, _ = fargv.parse({"lr": 0.001, "epochs": 10})
print(p.lr, p.epochs)   # attribute access
```

Simple and convenient.  Most editors offer limited autocompletion because the
attributes are not declared statically.

**Best for**: quick scripts where autocompletion is not critical.

---

## dict

```python
p, _ = fargv.parse({"lr": 0.001, "epochs": 10}, return_type="dict")
print(p["lr"], p["epochs"])
```

Useful when you need to serialise the result, pass it to `**kwargs`, or merge
it with another mapping.

**Best for**: frameworks that accept `**kwargs`, JSON serialisation.

---

## namedtuple

```python
p, _ = fargv.parse({"lr": 0.001, "epochs": 10}, return_type="namedtuple")
print(p.lr, p.epochs)   # attribute access, immutable
```

Immutable — safe to pass between threads.  Field names show up in `repr()`.

**Best for**: read-only configuration, thread-safe sharing.

---

## Dataclass — full IDE autocompletion

Define your parameters as a dataclass and pass the **class** (not an instance)
as the definition.  fargv reads the field types and defaults, builds a parser,
and returns a populated instance of your class.

```python
from dataclasses import dataclass, field
import fargv

@dataclass
class TrainConfig:
    data_dir:   str   = "/data"
    output_dir: str   = "{data_dir}/checkpoints"
    lr:         float = 1e-3
    epochs:     int   = 20
    batch_size: int   = 32
    tags:       list  = field(default_factory=list)

cfg, _ = fargv.parse(TrainConfig)
# cfg is a TrainConfig instance — full IDE autocompletion on cfg.lr, cfg.epochs, ...
print(cfg.lr, cfg.epochs)
```

```bash
python train.py --lr=5e-4 --epochs=50 --data_dir=/datasets/imagenet
```

### Pros
- Full static type information — IDE can autocomplete and type-check.
- The dataclass doubles as a documented configuration schema.
- `field(default_factory=list)` works as expected.
- Mandatory fields (no default) become required CLI arguments.

### Cons
- Slightly more boilerplate than a plain dict.
- Dataclass instances are not linked to a live parser — re-parsing requires
  calling `fargv.parse` again.

**Best for**: medium-to-large projects, ML experiments, anything where type
safety matters.

---

## FargvNamespace — live, observable namespace

`FargvNamespace` is a dynamic container that keeps a reference to the
underlying `FargvParameter` objects.  Attribute assignment re-validates the
value through the parameter's type converter and notifies registered backends.

```python
import fargv
from fargv import FargvNamespace, FargvConfigBackend

p, _ = fargv.parse(
    {"lr": 0.001, "epochs": 10},
    return_type="namespace",
)
# p is a FargvNamespace
p.link(FargvConfigBackend("~/.myapp.config.json"))

p.lr = 5e-4        # validated, saved to config file automatically
print(p.lr)        # 0.0005
print(p.as_dict()) # {"lr": 0.0005, "epochs": 10}
```

### Backends

| Backend | Effect of `on_param_changed` |
|---|---|
| `FargvConfigBackend(path)` | Writes full namespace as JSON to *path* |
| `FargvTkBackend(title)` | Opens Tk dialog; closes cleanly on Run |

Backends are chainable:

```python
p.link(FargvConfigBackend("~/.cfg.json")).link(FargvTkBackend("My App"))
```

### Pros
- Values are live — change `p.lr` and the config file updates automatically.
- Multiple backends can be attached (config + GUI).
- Parameters retain type validation after parse.

### Cons
- No static type declarations — IDE autocompletion not available.
- Slightly heavier than a plain namespace for read-only use.

**Best for**: interactive applications, Jupyter notebooks, long-running
services where configuration can change at runtime.

---

## Subcommand return types

When a subcommand parameter is present, the `subcommand_return_type` argument
controls how the result is shaped.  See the [Subcommands](subcommands.md) guide
for details.
