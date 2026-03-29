# fargv

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

## Usage

Define your parameters as a plain Python dictionary — types are inferred from the default values:

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

Run your script:

```bash
python myscript.py -name=Alice -count=3 -verbose -mode=slow -files a.txt b.txt c.txt
```

## Parameter Types

| Default value | Type | CLI example |
|---|---|---|
| `"hello"` | String (supports `{key}` interpolation) | `-name=Alice` or `-name Alice` |
| `42` | Integer | `-count=3` |
| `3.14` | Float | `-lr=0.001` |
| `False` | Bool flag | `-verbose` or `-verbose=true` |
| `("a", "b", "c")` | Choice (first is default) | `-mode=b` |
| `set()` | Positional list | `-files a.txt b.txt` |

## Help Strings

Attach a description to any parameter with a two-element tuple:

```python
p, _ = fargv.fargv({
    "epochs": (10,    "Number of training epochs"),
    "lr":     (0.001, "Learning rate"),
})
```

Run with `-help` to print the generated help message.

## Built-in Parameters

Every script automatically gets:

| Parameter | Short | Description |
|---|---|---|
| `-help` | `-h` | Print help and exit |
| `-bash_autocomplete` | | Print bash autocomplete script |
| `-v` | | Verbosity level |

## String Interpolation

```python
p, _ = fargv.fargv({
    "base": "/tmp",
    "out":  "{base}/results",   # resolved to /tmp/results
})
```

## Environment Variable Override

```bash
count=42 python myscript.py   # overrides the default for 'count'
```

## License

MIT
