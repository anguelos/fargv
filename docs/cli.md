# Command Line Reference

## Legacy API (single-dash)

Scripts using `fargv.fargv` automatically get these parameters:

### `-help` / `-h`

Print a help message listing all parameters with types, defaults, and current
values, then exit.

```bash
python myscript.py -help
```

### `-bash_autocomplete`

Print a bash completion script for the current program.  Source it in your
shell or drop it in `/etc/bash_completion.d`:

```bash
source <(python myscript.py -bash_autocomplete)
```

### `-v`

Set the global verbosity level (integer, default `1`).  Used by
`fargv.util.warn` — messages with `verbose <= v` are printed.

```bash
python myscript.py -v=2
```

---

## New OO API (double-dash)

Scripts using `fargv.parse` get these parameters (all configurable via
`auto_define_*` keyword arguments):

### `--help` / `-h`

Print a formatted help message and exit.

```bash
python myscript.py --help
```

### `--bash_autocomplete`

Print a bash completion script and exit.

```bash
source <(python myscript.py --bash_autocomplete)
```

### `--verbosity` / `-v`  *(count switch)*

Set the verbosity level.  Can be specified as a count switch (`-vvv` = 3)
or explicitly (`--verbosity=2`).

```bash
python myscript.py -vvv        # verbosity = 3
python myscript.py --verbosity=2
```

### `--config`

Path to a JSON config file.  Values in the file override coded defaults
but are themselves overridden by any CLI flags that follow.

```bash
python myscript.py --config=~/.myapp.config.json
```

The default config path is `~/.{appname}.config.json` (derived from the
program name automatically).

### `--auto_configure`

Print the current parameter values (after applying config file and CLI
flags) as pretty-printed JSON, then exit.  Useful for generating a config
file template:

```bash
python myscript.py --auto_configure > ~/.myapp.config.json
```

---

## Disabling built-in parameters

Pass `False` for any `auto_define_*` argument to `fargv.parse`:

```python
p, _ = fargv.parse(
    {"n": 1},
    auto_define_help=False,
    auto_define_bash_autocomplete=False,
    auto_define_verbosity=False,
    auto_define_config=False,
)
```
