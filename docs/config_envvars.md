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

### Auto-injected parameter

fargv injects a `--config` parameter automatically:

| Parameter | Default | Description |
|---|---|---|
| `--config` | `~/.{appname}.config.json` | Path to a JSON/YAML/TOML/INI config file |

```bash
# Explicitly point to a config file
python train.py --config=/opt/shared/train.json

# Next run picks up the default path automatically (if it exists)
python train.py   # reads ~/.train_py.config.json
```

### Config file format

A JSON object whose keys match parameter names:

```json
{
  "lr": 0.0005,
  "epochs": 50,
  "data_dir": "/datasets/imagenet",
  "mode": "train"
}
```

Unknown parameter names raise a `FargvError` at parse time — config files
are validated against the parser's known parameters.  Config values are
overridden by CLI arguments parsed afterwards.

### Generating a config from current values

Pass an empty string to `--config` to print **all current parameter values**
as JSON to stdout and exit.  Pipe the output to bootstrap a config file:

```bash
python train.py --lr=5e-4 --config=
# prints JSON to stdout, then exits

python train.py --lr=5e-4 --config= > ~/.train_py.config.json
# save it; next runs pick it up automatically
```

### Config files with subcommands

When a parser has subcommands, `--config=` includes **all branches** in the
dump so the same file covers every subcommand:

```bash
$ python prog.py train --config=
{
  "verbose": false,
  "cmd": {
    "train": {"lr": 0.01, "epochs": 10},
    "eval":  {"dataset": "val"}
  }
}
```

Config files **may set per-branch parameter values** using this nested format.
When loaded, fargv applies each branch's values to the matching sub-parser
regardless of which subcommand is selected at runtime:

```json
{
  "verbose": true,
  "cmd": {
    "train": {"lr": 0.001, "epochs": 50},
    "eval":  {"dataset": "test"}
  }
}
```

Config files **may not select which subcommand to run** — that is
only possible via the CLI.  Placing a string value for a subcommand
key raises `FargvError` at parse time:

```json
{ "cmd": "train" }
```

```text
FargvError: subcommand 'cmd' cannot be selected via a config file (got 'train').
Config may only set per-branch parameter values using the nested dict format:
{<subcommand>: {<branch>: {param: value}}}
```

> **Note**: subcommand param values in the dump always reflect definition
> defaults (not CLI overrides for the selected branch), because `--config=`
> fires before subcommand parsing completes.  Top-level params do capture
> their CLI values.  Edit the generated file to customise per-branch defaults.

### Disabling config-file support

```python
p, _ = fargv.parse(definition, auto_define_config=False)
```

### Manual config parameter

To hard-code a non-default config path:

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
{SCRIPTNAME}_{PARAMNAME}   (both uppercased, dots/hyphens → underscores)
```

For `train.py` with parameter `lr`:

```bash
export TRAIN_PY_LR=0.0001
python train.py   # lr=0.0001
```

The env var is overridden by an explicit CLI argument:

```bash
TRAIN_PY_LR=0.0001 python train.py --lr=0.001   # lr=0.001
```

### Env vars and subcommands

Environment variables **may not select which subcommand to run**.
If an env var matches a subcommand parameter name, fargv raises `FargvError`
at parse time:

```bash
export PROG_CMD=eval
python prog.py   # FargvError: env var 'PROG_CMD' attempts to select subcommand ...
```

Only the CLI can select a subcommand:

```bash
python prog.py eval   # OK
python prog.py --cmd=eval   # OK (flag form)
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

# Env vars take priority over config (reversed from default)
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
