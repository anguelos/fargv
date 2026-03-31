# Config Files and Environment Variables

fargv supports two sources of parameter overrides that sit between coded
defaults and the command line: a **JSON config file** and **environment
variables**.  Both are injected automatically — no annotation or registration
needed.

---

## Priority order

By default, each source overrides the previous one:

```
coded default  →  config file  →  env var  →  CLI / UI
```

This can be changed with the `override_order` argument to `parse()`.

---

## Config file

### Auto-injected parameters

When the script has a recognisable name (not `__main__`, `-c`, etc.), fargv
injects two parameters:

| Parameter | Default | Description |
|---|---|---|
| `--config` | `~/.{appname}.config.json` | Path to the JSON config file |
| `--auto_configure` | `False` | Print current config as JSON and exit |

```bash
# Save the current effective configuration
python train.py --lr=5e-4 --auto_configure > ~/.train.config.json

# Next run picks it up automatically
python train.py   # lr=5e-4 from config file

# Override the config path
python train.py --config=/opt/shared/train.json
```

### Config file format

A flat JSON object — keys match parameter names:

```json
{
  "lr": 0.0005,
  "epochs": 50,
  "data_dir": "/datasets/imagenet",
  "mode": "train"
}
```

Unknown keys are silently ignored.  Config values are overridden by CLI
arguments parsed afterwards.

### Passing an empty string to --config

```bash
python train.py --config=''
```

This is a shorthand for `--auto_configure`: the current parameter values are
printed as JSON to stdout and the process exits.  Useful in shell pipelines.

### Disabling config-file support

```python
p, _ = fargv.parse(definition, auto_define_config=False)
```

### Manual config parameter

To use a non-default config path *in code*:

```python
from fargv import parse, FargvConfig

p, _ = parse({
    "lr": 0.001,
    "config": FargvConfig("/opt/myapp/config.json"),
})
```

---

## Environment variables

Every user-defined parameter automatically accepts an environment variable
override.  The name is derived as:

```
{SCRIPTNAME}_{PARAMNAME}   (both uppercased)
```

For `train.py` with parameter `lr`:

```bash
export TRAIN_LR=0.0001
python train.py   # lr=0.0001
```

The env var is overridden by an explicit CLI argument:

```bash
TRAIN_LR=0.0001 python train.py --lr=0.001   # lr=0.001
```

### Disabling env-var support

```python
p, _ = fargv.parse(definition, override_order=["default", "config", "ui"])
```

---

## override_order

The `override_order` list controls which source wins.  Rules:

- Must start with `"default"`.
- Must end with `"ui"`.
- No duplicates.

```python
# Config only, no env vars
p, _ = fargv.parse(definition, override_order=["default", "config", "ui"])

# Env vars only, no config file
p, _ = fargv.parse(definition, override_order=["default", "envvar", "ui"])

# Env vars override config (reversed from default)
p, _ = fargv.parse(definition, override_order=["default", "config", "envvar", "ui"])
# Wait — that IS the default.  To make config override env vars:
p, _ = fargv.parse(definition, override_order=["default", "envvar", "config", "ui"])
```

---

## FargvNamespace + FargvConfigBackend

When using `return_type="namespace"`, attach `FargvConfigBackend` to
automatically save changes back to the config file whenever a parameter is
updated at runtime:

```python
import fargv
from fargv import FargvConfigBackend

p, _ = fargv.parse({"lr": 0.001, "epochs": 10}, return_type="namespace")
p.link(FargvConfigBackend("~/.myapp.config.json"))

# Later in the script:
p.lr = 5e-4   # immediately written to ~/.myapp.config.json
```

See [Return Types](return_types.md) and [GUI and Backends](gui_backends.md)
for more on `FargvNamespace`.
