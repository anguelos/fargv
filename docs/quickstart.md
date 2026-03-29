# Quickstart

## Installation

```bash
pip install fargv
```

## Basic Usage

Define your parameters as a plain Python dictionary — types are inferred from
the default values:

```python
import fargv

p, _ = fargv.fargv({
    "name":    "world",           # str
    "count":   1,                 # int
    "verbose": False,             # bool flag
    "mode":    ("fast", "slow"),  # choice, first is default
    "files":   set(),             # positional list
})

print(f"Hello, {p.name}! count={p.count}")
```

Run your script:

```bash
python myscript.py -name=Alice -count=3 -verbose -mode=slow -files a.txt b.txt
```

## Parameter Types

| Default value | Type | CLI example |
|---|---|---|
| `"hello"` | String | `-name=Alice` or `-name Alice` |
| `42` | Integer | `-count=3` |
| `3.14` | Float | `-lr=0.001` |
| `False` | Bool flag | `-verbose` or `-verbose=true` |
| `("a", "b", "c")` | Choice | `-mode=b` |
| `set()` | Positional list | `-files a.txt b.txt` |

## String Interpolation

String parameters support `{key}` references to other parameters:

```python
p, _ = fargv.fargv({
    "base": "/tmp",
    "out":  "{base}/results",   # becomes /tmp/results
})
```

## Help Strings

Attach a description to any parameter using a two-element tuple:

```python
p, _ = fargv.fargv({
    "epochs": (10,    "Number of training epochs"),
    "lr":     (0.001, "Learning rate"),
})
```

Run with `-help` to print the generated help message.

## Return Types

By default fargv returns a `SimpleNamespace`. You can request a `dict` or
`namedtuple` instead:

```python
p, _ = fargv.fargv({"n": 1}, return_type="dict")
p, _ = fargv.fargv({"n": 1}, return_type="namedtuple")
```

## Environment Variable Override

Every parameter can be overridden by an environment variable with the same
name before calling your script:

```bash
n=42 python myscript.py
```

## Built-in Parameters

Every script automatically gets:

| Parameter | Short | Description |
|---|---|---|
| `-help` | `-h` | Print help and exit |
| `-bash_autocomplete` | | Print bash autocomplete script and exit |
| `-v` | | Verbosity level (integer) |
