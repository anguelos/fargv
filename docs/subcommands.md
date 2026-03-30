# Subcommands

Subcommands let a single script expose multiple distinct operations — similar
to `git commit`, `git push`, `git log`.  fargv implements them via a nested
dict whose values are themselves definitions.

---

## Defining subcommands

Pass a dict whose **values are all dicts** (or callables / `ArgumentParser`
instances).  fargv detects this pattern and creates a `FargvSubcommand`
parameter automatically.

```python
import fargv

p, _ = fargv.parse({
    "verbose": False,
    "command": {
        "commit": {
            "message": ("", "Commit message"),
            "all":     (False, "Stage all tracked files"),
        },
        "push": {
            "remote": ("origin", "Remote name"),
            "force":  (False,    "Force push"),
        },
        "log": {
            "n":      (10,    "Number of commits to show"),
            "oneline": (False, "Compact one-line format"),
        },
    },
})

print(p.command)   # selected subcommand name, e.g. "commit"
print(p.message)   # subcommand parameter (flat mode, default)
print(p.verbose)   # parent parameter
```

```bash
python git_like.py commit --message="fix typo" --all
python git_like.py push --remote=upstream --force
python git_like.py log --n=20 --oneline
```

---

## Per-subcommand help

Every subcommand automatically gets its own `--help` / `-h` flag:

```bash
python git_like.py commit --help
python git_like.py push -h
```

---

## Return shapes

The `subcommand_return_type` argument controls how the selected subcommand's
parameters appear in the result.

### `"flat"` (default)

The subcommand key holds the **selected name** as a string.  All subcommand
parameters are merged into the top-level namespace.

```python
p, _ = fargv.parse(definition, subcommand_return_type="flat")
print(p.command)  # "commit"
print(p.message)  # "fix typo"
print(p.all)      # True
```

**Best for**: simple scripts where parameter names don't conflict across
subcommands.

### `"nested"`

The subcommand key holds a `SimpleNamespace(name=..., **params)`.

```python
p, _ = fargv.parse(definition, subcommand_return_type="nested")
print(p.command.name)    # "commit"
print(p.command.message) # "fix typo"
print(p.verbose)         # parent param still at top level
```

**Best for**: scripts where subcommands have overlapping parameter names.

### `"tuple"`

Returns a three-element tuple `(name, sub_ns, parent_ns)` instead of the
usual `(result, help_str)` pair.

```python
(name, sub_ns, parent_ns), help_str = fargv.parse(
    definition, subcommand_return_type="tuple"
)
print(name)           # "commit"
print(sub_ns.message) # "fix typo"
print(parent_ns.verbose)
```

**Best for**: dispatch tables — `handlers[name](sub_ns, parent_ns)`.

---

## Dispatch pattern

```python
def do_commit(sub, parent):
    print(f"Committing: {sub.message!r}  all={sub.all}  verbose={parent.verbose}")

def do_push(sub, parent):
    print(f"Pushing to {sub.remote}  force={sub.force}")

def do_log(sub, parent):
    print(f"Showing {sub.n} commits  oneline={sub.oneline}")

handlers = {"commit": do_commit, "push": do_push, "log": do_log}

(name, sub_ns, parent_ns), _ = fargv.parse(
    definition, subcommand_return_type="tuple"
)
handlers[name](sub_ns, parent_ns)
```

---

## Subcommands defined by callables

Any definition that is a callable (function, class) can be used as a
subcommand value.  fargv will introspect the signature:

```python
def commit(message: str = "", all: bool = False):
    ...

def push(remote: str = "origin", force: bool = False):
    ...

p, _ = fargv.parse({
    "verbose": False,
    "command": {"commit": commit, "push": push},
})
```

---

## Notes

- Only **one** subcommand parameter is supported per parser.
- The subcommand name is always a positional token — the first bare word on the
  command line that matches a known subcommand name.
- Unknown subcommand names raise a `FargvError`.
