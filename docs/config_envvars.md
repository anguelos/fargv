# Config Files and Environment Variables

fargv supports two sources of parameter overrides that sit between coded
defaults and the command line: a **config file** (JSON, INI, TOML, or YAML)
and **environment variables**.  Both are injected automatically — no
annotation or registration needed.

---

## Priority order

```
coded default  →  config file  →  env var  →  CLI / UI
```

This can be changed with the `override_order` argument to `parse()`.

---

## Config file

### Auto-injected parameter

fargv injects a `--config` / `-C` parameter automatically:

| Parameter | Alias | Default | Description |
|---|---|---|---|
| `--config` | `-C` | `~/.{appname}.config.json` | Path to a JSON/YAML/TOML/INI config file |

```bash
# Explicitly point to a config file
python train.py --config=/opt/shared/train.json
python train.py -C /opt/shared/train.json   # same, short form

# If the default path exists it is loaded automatically
python train.py   # reads ~/.train_py.config.json if it exists
```

### Key naming convention

Config files use **flat keys**.  Top-level parameters appear as-is.
Subcommand branch parameters are prefixed with the branch name and a dot:

| Parameter | Subcommand branch | Config key |
|---|---|---|
| `lr` (top-level) | — | `lr` |
| `lr` (inside branch `train`) | `train` | `train.lr` |
| `epochs` (inside branch `eval`) | `eval` | `eval.epochs` |

The subcommand field name itself (`cmd`, `command`, etc.) is **not** a valid
config key — only branch names are used as prefixes.

### Config file formats

All four formats use the same flat-key convention.

**JSON** (default):

```json
{
  "fargv_comment.lr": "Learning rate. env var: TRAIN_LR",
  "lr": 0.0005,
  "fargv_comment.train.lr": "Branch train — learning rate",
  "train.lr": 0.001,
  "train.epochs": 50
}
```

Keys that start with `fargv_comment` are silently discarded by the loader.
They act as JSON pseudo-comments and are written automatically by the dump
functions to describe each parameter (full help text + env var name).

**INI** (single `[main]` section, `;` comments):

```ini
[main]

; Learning rate.  type: float  default: 0.01  env var: TRAIN_LR
lr = 0.0005

; --- train ---
; Learning rate inside train branch.  type: float  default: 0.01  env var: TRAIN_TRAIN_LR
train.lr = 0.001

; Epochs inside train branch.  type: int  default: 10  env var: TRAIN_TRAIN_EPOCHS
train.epochs = 50
```

**TOML** (flat, quoted keys for dotted names):

```toml
# Learning rate.  type: float  default: 0.01  env var: TRAIN_LR
lr = 0.0005

# --- train ---
# Learning rate inside train branch.  type: float  default: 0.01  env var: TRAIN_TRAIN_LR
"train.lr" = 0.001

# Epochs inside train branch.  type: int  default: 10  env var: TRAIN_TRAIN_EPOCHS
"train.epochs" = 50
```

Keys containing dots must be quoted in TOML to avoid being interpreted as
nested table syntax.

**YAML** (flat, dot characters are plain in YAML key names):

```yaml
# Learning rate.  type: float  default: 0.01  env var: TRAIN_LR
lr: 0.0005

# --- train ---
# Learning rate inside train branch.  type: float  default: 0.01  env var: TRAIN_TRAIN_LR
train.lr: 0.001

# Epochs inside train branch.  type: int  default: 10  env var: TRAIN_TRAIN_EPOCHS
train.epochs: 50
```

### Generating a config file

Use the `//format` syntax to print a config to stdout and exit.  fargv also
prints the suggested save path to stderr:

```bash
# Dump as JSON (default)
python train.py --config //json
python train.py -C //json

# Dump as INI
python train.py --config //ini

# Dump as TOML
python train.py --config //toml

# Dump as YAML
python train.py --config //yaml
```

```text
$ python train.py --lr=0.001 --config //json
{
  "fargv_comment.lr": "Learning rate.  type: float  default: 0.01  env var: TRAIN_LR",
  "lr": 0.001,
  ...
}
fargv: to persist, redirect to: /home/user/.train_py.config.json
```

Save it and it loads automatically on the next run:

```bash
python train.py --lr=0.001 --config //json > ~/.train_py.config.json
python train.py   # lr=0.001 from config
```

Or use a different format and a different path:

```bash
python train.py --config //ini > myconfig.ini
python train.py --config myconfig.ini
```

### Variadic parameters in config files

`FargvVariadic` parameters (list defaults) are **not written** to config dumps
because persisting a variadic default can cause stale-config bugs when the
coded default is changed later.  In formats that support comments (INI, TOML,
YAML), variadic entries appear as comments so you can see them but they have no
effect.  In JSON they are omitted entirely.

### Unknown keys

By default, if a config file contains any unknown key, fargv prints a warning
to stderr for each bad key and then **ignores the entire config dict**:

```text
fargv: config file 'run.json': unknown key 'ghost.lr' — ignoring config
```

This conservative default prevents a config written for one version of a
script from silently half-applying to a different version.

Change the policy with the `unknown_keys` argument:

| Value | Behaviour |
|---|---|
| `"ignore_dict_and_warn"` (default) | warn per bad key; discard whole dict |
| `"ignore_key_and_warn"` | warn per bad key; apply all valid keys |
| `"raise"` | raise `FargvError` on first bad key |

```python
p, _ = fargv.parse(definition, unknown_keys="ignore_key_and_warn")
```

### Disabling config-file support

```python
p, _ = fargv.parse(definition, auto_define_config=False)
```

---

## Environment variables

Every user-defined parameter automatically accepts an environment variable
override.  The naming follows the same flat convention as config files but uses
underscore (`_`) as the separator and adds the app-name prefix:

```
{APPNAME}_{KEY}   (everything uppercased)
```

| Parameter | App name | Env var |
|---|---|---|
| `lr` (top-level) | `train.py` | `TRAIN_PY_LR` |
| `lr` (branch `train`) | `prog.py` | `PROG_PY_TRAIN_LR` |
| `epochs` (branch `eval`) | `prog.py` | `PROG_PY_EVAL_EPOCHS` |

```bash
export TRAIN_PY_LR=0.0001
python train.py          # lr=0.0001 from env var

TRAIN_PY_LR=0.0001 python train.py --lr=0.001   # lr=0.001 (CLI wins)
```

The subcommand field name itself is not a valid env var target.  Only branch
parameters can be set via env vars, using the `APPNAME_BRANCH_PARAM` pattern.

```bash
# Set parameter 'lr' inside subcommand branch 'train'
export PROG_TRAIN_LR=0.5
python prog.py train     # train.lr=0.5
```

Unknown env vars (no matching parameter) are silently ignored — fargv only
checks env var names that correspond to known parameters.

---

## override_order

The `override_order` list controls which sources are active and which wins.
Rules: must start with `"default"`, must end with `"ui"`, no duplicates.

```python
# Config only, no env vars
p, _ = fargv.parse(definition, override_order=["default", "config", "ui"])

# Env vars only, no config file
p, _ = fargv.parse(definition, override_order=["default", "envvar", "ui"])

# Env vars take priority over config (reversed from default)
p, _ = fargv.parse(definition, override_order=["default", "envvar", "config", "ui"])
```
