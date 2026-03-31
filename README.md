# fargv

[![Tests](https://github.com/anguelos/fargv/actions/workflows/tests.yml/badge.svg)](https://github.com/anguelos/fargv/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/anguelos/fargv/badges/badges/coverage.json)](https://github.com/anguelos/fargv/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/fargv)](https://pypi.org/project/fargv/)
[![Downloads](https://img.shields.io/pypi/dm/fargv)](https://pypi.org/project/fargv/)
[![Documentation Status](https://readthedocs.org/projects/fargv/badge/?version=latest)](https://fargv.readthedocs.io/en/latest/)
[![Python Versions](https://img.shields.io/pypi/pyversions/fargv)](https://pypi.org/project/fargv/)
[![GitHub repo size](https://img.shields.io/github/repo-size/anguelos/fargv)](https://github.com/anguelos/fargv)

A very easy to use argument parser for Python scripts.

## Installation

```bash
pip install fargv
```

## Lazy usage

Pass a plain dict — types, short names, config file, and env-var overrides are
all inferred automatically.

```python
import fargv

p, _ = fargv.parse({
    "data_dir":   "/data",                   # str — base path, referenced below
    "output_dir": "{data_dir}/results",      # str — resolved via {data_dir}
    "mode":       ("train", "eval", "test"), # choice — first element is default
    "verbose":    False,                     # bool switch
    "files":      [],                        # positional — collects leftover args
})

print(f"Reading from {p.data_dir}, writing to {p.output_dir}")
print(f"Mode: {p.mode}  verbose: {p.verbose}  files: {p.files}")
```

```bash
python myscript.py --data_dir=/datasets/cifar --mode=eval --verbose model_a.pt model_b.pt
# data_dir=/datasets/cifar  output_dir=/datasets/cifar/results
# mode=eval  verbose=True  files=['model_a.pt', 'model_b.pt']
```

Every parameter automatically gets a short flag inferred from its name
(`-d`, `-o`, `-m`, `-V`, …), `--help` output, bash tab-completion, a config
file at `~/.myscript.config.json`, and env-var overrides (`MYSCRIPT_MODE=eval`).

## Precise usage

Use explicit `FargvParameter` types for full control — descriptions, validation,
and stream / path / tuple parameters.

```python
import fargv

p, _ = fargv.parse({
    "data_dir":   fargv.FargvStr("/data",
                      description="Root input directory"),
    "output_dir": fargv.FargvStr("{data_dir}/results",
                      description="Where outputs are written ({data_dir} resolved at parse time)"),
    "mode":       fargv.FargvChoice(["train", "eval", "test"],
                      description="Run mode"),
    "verbose":    fargv.FargvBool(False,
                      description="Enable verbose logging"),
    "files":      fargv.FargvPositional([],
                      description="Input files (positional)"),
})
```

The CLI behaviour is identical to the lazy version; the explicit form adds
per-parameter descriptions in `--help` and makes the intent clearer for
larger scripts.

## Using fargv from bash

`python -m fargv` calls any Python callable directly from the shell —
types and defaults are inferred from the function's signature automatically,
with no wrapper code required.

```bash
python -m fargv numpy.linspace --help
python -m fargv numpy.linspace -s 0 -S 6.283 --num 8 --endpoint false
```

![fargv bash demo](docs/_static/fargv_bash.png)

The same call with `-ui tk` opens a Tk window instead:

```bash
python -m fargv numpy.linspace -s 0 -S 6.283 --num 8 --endpoint false -ui tk
```

![fargv Tk GUI demo](docs/_static/fargv_linspace_tk.png)

## Comparison with other argument parsers

| Feature | [fargv](https://github.com/anguelos/fargv) | [argparse](https://docs.python.org/3/library/argparse.html) | [click](https://click.palletsprojects.com/) | [typer](https://typer.tiangolo.com/) | [fire](https://github.com/google/python-fire) | [docopt](http://docopt.org/) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Zero boilerplate | ✅ | ❌ | 🟡 | 🟡 | ✅ | 🟡 |
| Type inference from defaults | ✅ | ❌ | ❌ | ❌ | 🟡 | ❌ |
| Type inference from annotations | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| Auto-generated help | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Auto short-name inference | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Config file (built-in) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| String interpolation | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Subcommands | ✅ | ✅ | ✅ | ✅ | ✅ | 🟡 |
| `python -m pkg.func` invocation | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Bash tab completion | 🟡 | 🟡 | ✅ | ✅ | 🟡 | ❌ |
| No runtime dependencies | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Environment variable override | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| GUI / widget interface | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| zsh / fish completion | ❌ | 🟡 | ✅ | ✅ | 🟡 | ❌ |
| Mutually exclusive parameters | ❌ | ✅ | ✅ | ✅ | ❌ | 🟡 |
| Parameter validation / constraints | 🟡 | 🟡 | ✅ | ✅ | ❌ | ❌ |
| Async command support | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Interactive prompts / password input | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Decorator-based API | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Type-safe return value | 🟡 | ❌ | 🟡 | ✅ | ❌ | ❌ |

✅ built-in  · 🟡 available with extra work or plugins  · ❌ not supported

**fargv notes:**
Bash tab completion generates a script via `--bash_autocomplete` that must be sourced manually.
Parameter validation covers path constraints (`FargvExistingFile`, `FargvNonExistingFile`, `FargvFile`) but not numeric ranges or regex patterns.
Type-safe return requires passing a dataclass as the definition; the default `SimpleNamespace` is untyped.

## License

MIT

---

## Legacy usage (v < 0.1.9)

The original API uses single-dash flags and a plain dict.  It is still fully
supported but new scripts should prefer `fargv.parse` above.

```python
import fargv

p, _ = fargv.fargv({
    "name":    "world",            # str
    "count":   1,                  # int
    "verbose": False,              # bool flag
    "mode":    ("fast", "slow"),   # choice, first is default
    "files":   set(),              # positional list
})

print(f"Hello, {p.name}! count={p.count}")
```

Both assignment and space-separated forms are accepted:

```bash
python myscript.py -name=Alice -count=3 -verbose -mode=slow -files a.txt b.txt c.txt
python myscript.py -name Alice -count 3 -verbose -mode slow -files a.txt b.txt c.txt
```

Attach a description with a two-element tuple:

```python
p, _ = fargv.fargv({
    "epochs": (10,    "Number of training epochs"),
    "lr":     (0.001, "Learning rate"),
})
```

Built-in legacy parameters:

| Parameter | Short | Description |
|---|---|---|
| `-help` | `-h` | Print help and exit |
| `-bash_autocomplete` | | Print bash autocomplete script |
| `-v` | | Verbosity level |

String interpolation and env-var override work the same way as in the new API.
