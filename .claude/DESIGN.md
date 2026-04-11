# fargv — Design Notes

Decisions and rationale for planned and in-progress features.
Update this file whenever a design choice is made or revised.

---

## Planned parameter types

### `FargvSubcommand`

**Default Python literal:** `dict`

A dict whose keys are subcommand names and whose values are parameter
definitions (dicts, `ArgumentParser` instances, or callables — anything
accepted by `definition_to_parser`).

#### CLI syntax

Positional-first (git-style) is the default:

```
myscript train --lr=0.1
myscript --subcommand=train --lr=0.1   # flag style, also supported
```

Both styles may be active simultaneously on the same parser.

#### Subcommand selection

- If mandatory (sentinel value or `mandatory=True` kwarg): no subcommand →
  `FargvError` at parse time.
- Otherwise: first key in the dict is the default subcommand.

#### Global parameters

Parent-level parameters are shared across all subcommands.
Defining a `FargvVariadic` at the parent level while subcommands are
active raises a warning on `sys.stderr` (variadic token is ambiguous
— is it a subcommand name or a variadic value?).

#### Nesting

Nested subcommands are supported by design: a subcommand's own definition
may itself contain a `FargvSubcommand` entry.  No artificial depth limit.

#### Return value

`parse()` gains a `subcommand_return_type` parameter:

| Value | Shape |
|-------|-------|
| `"flat"` (default) | `ns.subcommand = "train"`, `ns.lr = 0.001`, global params merged in |
| `"nested"` | `ns.subcommand = "train"`, `ns.train.lr = 0.001` |
| `"tuple"` | `(subcommand_name, subcommand_ns, global_ns)` |

---

### `FargvInputStream` / `FargvOutputStream`

Subclasses of the existing `FargvStream`, hard-coding the mode so it is
visible in the type name and help output.

| Class | Mode | Default |
|-------|------|---------|
| `FargvInputStream` | `"r"` (text read) | `sys.stdin` |
| `FargvOutputStream` | `"w"` (text write) | `sys.stdout` |

`FargvStream` itself remains for cases where mode is inferred from the
default (e.g. an already-open file).

Binary mode and append mode are **TODO**.

---

### `FargvPath` / `FargvExistingFile` / `FargvNonExistingFile` / `FargvFile`

All return `pathlib.Path` as `.value`.

Base class:

```python
FargvPath(
    default,
    must_exist: bool = False,
    must_not_exist: bool = False,
    parent_must_exist: bool = False,
    name=None, short_name=None, description=None,
)
```

Validation runs inside `ingest_value_strings` and raises `FargvError`
immediately if the constraint is violated.

Three named subclasses:

| Class | Constraint | Typical use |
|-------|-----------|-------------|
| `FargvExistingFile` | `must_exist=True` | Input file that must already be on disk |
| `FargvNonExistingFile` | `must_not_exist=True` | Output file that must not overwrite anything |
| `FargvFile` | `parent_must_exist=True` | Output path whose parent directory must exist |

**TODO** — `FargvDir` and its variants (`FargvExistingDir`, `FargvNewDir`)
follow the same pattern but validate directories.

---

### Config-file auto-parameter

#### Motivation

Many scripts need a config file to override defaults before CLI flags are
applied.  fargv injects this automatically so the user never writes the
boilerplate.

#### Priority order

```
coded defaults  →  config file  →  env vars  →  CLI / UI
```

#### Injection

Controlled by `auto_define_config: bool = True` in `fargv.parse()`.
When enabled, two parameters are injected:

| Auto-param | Default | Effect |
|-----------|---------|--------|
| `--config` | `~/.{app_name}.config.json` | Path to JSON config; if the file exists its keys override defaults |
| `--auto_configure` | `False` (flag) | Print the current parameter set as JSON to stdout, then exit |

`app_name` is derived from `guess_program_name()`, dots and path separators
stripped.

#### Validation

A key present in the config file that does not match any defined parameter
raises `FargvError`.  (Avoids silent misconfiguration.)

#### Format

JSON for now.  The design should make it easy to add YAML / TOML / INI
later, likely via optional extras (`pip install fargv[yaml]`).  YAML and
TOML are not bundled because fargv has zero required runtime dependencies.

#### Future

Consider a `fargv_config` CLI tool (installed as a console-script entry
point) and/or a `config` built-in subcommand for reading, writing, and
diffing config files.  Deferred to later milestone.

---

### `FargvTuple` — typed tuple via `typing.Tuple`

#### Motivation

Many numerical parameters are naturally pairs or triples:
`--size 224 224`, `--crop 0 0 224 224`.  Python's `typing.Tuple` is a
natural way to express their structure.

#### CLI syntax

The entire tuple is passed as a **single string** (no space splitting):

```
--size=(224,224)
--crop=(0,0,224,224)
--offset=(-10,5)
```

Parsed with `ast.literal_eval`, so standard Python tuple syntax is accepted.

#### Supported element types

All basic Python literal types that `ast.literal_eval` handles:
`int`, `float`, `str`, `bool`, `bytes`.
The annotation `Tuple[T1, T2, ...]` drives type-checking after eval.

#### `Optional[Tuple[...]]`

`'()'` (empty tuple string) evaluates to `None`.
Any other valid tuple string is parsed normally.

#### Integration with `function_to_parser`

```python
from typing import Tuple

def crop(size: Tuple[int, int] = (224, 224)):
    ...

p, _ = fargv.parse(crop)
# CLI: --size=(640,480)
```

`_annotation_to_fargv_cls` is extended to recognise `Tuple[...]`
annotations and return `FargvTuple` with the element types baked in.

---

## TODO list

- `FargvDir`, `FargvExistingDir`, `FargvNewDir` — directory variants of
  the path types (same `FargvPath` base, `is_dir` validation flag).
- `FargvInputStream` / `FargvOutputStream` binary mode variants.
- `FargvStream` append mode.
- Config file: YAML / TOML / INI support as optional extras.
- `fargv_config` CLI tool / `config` built-in subcommand.
- `FargvTuple`: `List[T]` typed list via `typing.List` (same ast path).
- `Optional[Tuple]` full round-trip: serialise `None` back to `'()'` in
  `auto_configure` output.
- Sub-command `"nested"` and `"tuple"` return modes.
- Sub-command flag style (`--subcommand=train`) implementation.
- Sub-command: decide whether to allow a global variadic alongside
  subcommands or hard-error.
- GUI modes: `"tk"`, `"qt"`, `"jupyter"` (currently raise `NotImplementedError`).
- **`itk` interactive GUI mode** — concurrent Tk window with Start/Kill/Update/Reset/Help;
  see full design section below.
- **Type-aware field validation** — `<KeyRelease>` colour feedback (yellow/red) on int/float
  entry fields; `<FocusOut>` revert stays as safety net; see design section below.
- `src/` layout migration (`fargv/` → `src/fargv/`).
- Sphinx docs for OO API.
- **** — filesystem backend exposing a  as a
  -style directory; see full design section below.

---

## Filesystem backend (`FargvFuseBackend`)

### Concept

Expose a `FargvNamespace` as a `/proc`-style directory tree via a
filesystem interface.  Each parameter is a file; reading it returns the
current value as a string; writing to it sets a new value (validated
through the normal `FargvParameter.evaluate()` path).  Subcommand
parameters are represented as subdirectories.

The goal is not to enforce any policy about *which* parameters should
be changeable — that remains entirely the application's concern.  The
backend simply provides the filesystem surface; the `FargvNamespace`
observer chain handles propagation and validation.

### Intended implementation

Two tiers, both behind the same `FargvFuseBackend` API:

1. **FUSE tier** (preferred, requires `refuse` or `fusepy`): a proper
   in-process filesystem mount.  The running process stays alive; the
   mount disappears when the process exits.
2. **Watchdog/inotify fallback** (no FUSE kernel module required):
   write each parameter to a real file in a temp directory; a background
   thread watches for writes and calls `namespace.__setattr__` when a
   file changes.  Slightly less robust (polling interval, stale reads
   between write and reload) but works on restricted HPC nodes and
   macOS without macFUSE.

Both tiers are optional — `from fargv.fs_backend import available`
follows the same pattern as `fargv.gui_tk.available`.

### API sketch

```python
from fargv import FargvFuseBackend

p, _ = fargv.parse({"lr": 0.001, "epochs": 10}, return_type="namespace")
p.link(FargvFuseBackend())                        # auto path: /tmp/fargv-{appname}-{pid}/
p.link(FargvFuseBackend("/shared/nfs/job42/"))    # explicit path (multi-node sharing)

# From any shell with access to the path:
# cat /tmp/fargv-train-12345/lr          ->  0.001
# echo 5e-4 > /tmp/fargv-train-12345/lr
# cat /tmp/fargv-train-12345/lr          ->  0.0005
```

Chains naturally with other backends:

```python
p.link(FargvConfigBackend("~/.train.json")).link(FargvFuseBackend())
# A filesystem write also triggers the config-file backend.
```

### File format conventions

- Scalar params: plain string representation (`str(value)`) followed by
  a newline — compatible with `cat` and `echo`.
- List / variadic params: one element per line.
- Choice params: current value on line 1; available choices on subsequent
  lines (read-only lines 2+), so `cat` shows the menu.
- A write that fails validation leaves the file content unchanged and
  the error is available in a companion `{param}.error` file (empty when
  last write succeeded).

### Mount point and lifecycle

- Default path: `/tmp/fargv-{appname}-{pid}/`
- Unmounted automatically via `atexit` and `SIGTERM` handler registered
  at `attach()` time.
- If the process is killed with `SIGKILL` the mount point is left behind;
  cleanup is `fusermount -u <path>` (FUSE) or plain `rm -r` (watchdog).

### Use cases

- **HPC live tuning** — tweak a parameter of a queued job without
  killing it and re-queuing.  Primary motivation for this feature.
- **Long-running ML training** — adjust learning rate, log verbosity,
  early stopping threshold while the job is running.
- **Shell tooling for free** — `watch`, `diff`, `grep`, `cp -r` all
  work on the param directory without any custom code.
- **Orchestration tools** — Ansible/Chef/Puppet can read and write the
  files; the running process becomes a managed resource.
- **Checkpoint/reproducibility** — `cp -r /tmp/fargv-job42/ ./run_003/`
  snapshots the parameter state at any point mid-run.
- **Multi-process sharing** — workers on a shared filesystem all read
  from the same directory; one controller writes.
- **Auto-tuning loops** — a hyperparameter search script writes
  candidate values to the param files; the running job picks them up on
  the next iteration.
- **Cross-language interoperability** — C++, Julia, or bash processes
  can read/write parameters with no Python dependency.
- **Kubernetes ConfigMap hot-reload** — if the mount path is a
  ConfigMap volume, updating the ConfigMap propagates to the running
  pod's parameters automatically.
- **Fault injection / chaos testing** — a test harness writes bad values
  and verifies the process handles `evaluate()` errors gracefully.

---

## Interactive Tk GUI (`itk` mode / `FargvItkBackend`)

### Concept

A non-blocking Tk window that runs **concurrently** with the program's main
loop, allowing a user to inspect and modify `FargvNamespace` parameters while
the program is running.  Designed for long-running jobs (ML training, HPC
simulations, daemons) where restarting to change a parameter is undesirable.

Activated via `--user_interface=itk` or by calling
`p.link(FargvItkBackend())` directly.

### Buttons

| Button | Behaviour |
|---|---|
| **Start** | Apply current GUI values to the namespace (same as **Run** in modal `tk`), then return control to the main program — the window stays open. |
| **Kill** | Send `signal.raise_signal(signal.SIGTERM)` to the process.  Triggers `atexit` handlers (FUSE unmount, config flush, etc.) before exit. |
| **Update** | Push all pending GUI field values into the namespace.  Disabled when GUI is in sync with the namespace. |
| **Reset** | Revert all pending GUI field values to the current namespace values.  Disabled when GUI is in sync with the namespace. |
| **Help** | Same as modal `tk` — scrollable help text window. |

### Dirty tracking (Update / Reset enable state)

Each parameter field tracks whether its current GUI value differs from the
live namespace value.  A field is *dirty* when `var.get() != str(p.{name})`.

- Any dirty field → **Update** and **Reset** both enabled.
- All fields clean → both disabled.
- After **Update**: all fields applied to namespace, all become clean.
- After **Reset**: all fields reverted to namespace values, all become clean.

### Threading model

`FargvItkBackend.attach()` starts the Tk event loop in a **background daemon
thread**, then blocks on a `threading.Event` (`_started`) until the user
clicks Start.  Once Start is clicked:

1. `_started` is set → `attach()` returns → the user's main loop begins.
2. The Tk event loop continues running in its daemon thread.
3. When the main loop finishes (or `_stop` is set), the window closes.

This requires **no restructuring** of user code — `p.link(FargvItkBackend())`
is placed immediately before the main loop, same as any other backend.

```python
p, _ = fargv.parse({"lr": 0.001, "epochs": 100}, return_type="namespace")
p.link(FargvItkBackend())   # window opens; blocks here until Start is clicked

for epoch in range(p.epochs):   # main loop starts after Start
    train(lr=p.lr)              # reads live namespace value each iteration
```

### Platform threading constraints

| Platform | Tk (itk) | Qt (iqt) | GTK (igtk) |
|---|---|---|---|
| Linux / Windows | background thread | background thread | background thread |
| macOS (OS X 10+) | background thread (works in practice) | **subprocess + IPC** | **subprocess + IPC** |

Qt and GTK use Cocoa on macOS, which hard-requires the main thread for all UI
operations.  The subprocess + IPC approach routes parameter changes through the
`FargvFuseBackend` filesystem path — no custom protocol needed.

### Two-way binding (nice-to-have)

When another backend (e.g. config file, FUSE) changes a namespace value
programmatically, the `on_param_changed` callback should update the
corresponding GUI field.  This requires posting a call to the Tk thread via
`root.after(0, lambda: var.set(str(new_value)))` — safe because `root.after`
is thread-safe in Tk.  Implement after the core itk loop is stable.

### Window lifetime

The window closes when:
- The main program's loop finishes (normal exit): the backend's `close()`
  method is called, which calls `root.after(0, root.destroy)`.
- **Kill** is pressed: `signal.SIGTERM` sent; `atexit` closes the window.
- The user closes the window via the OS (WM_DELETE_WINDOW): treated as Kill.


---

## Type-aware field validation in Tk GUI

### Current behaviour

`_make_validator` binds `<FocusOut>` on text entry widgets.  On focus loss,
if the raw string cannot be converted by the parameter's type, the field
reverts to the parameter's default value.  No feedback is given while the
user is typing.

### Improved behaviour

Two-event model:

1. **`<KeyRelease>`** — fires after every keystroke.  Updates the field's
   background colour as a non-disruptive signal:
   - **Normal**: field matches current parameter value (clean).
   - **`#fff3cd`** (pale yellow): field has been modified but is parseable
     (pending, not yet applied).
   - **`#f8d7da`** (pale red): current text cannot be parsed by the parameter
     type (invalid mid-type).

2. **`<FocusOut>`** (existing) — reverts to default when the text is
   unparseable, resets background to normal.

The colour signal applies only to `FargvInt` and `FargvFloat` fields, where
partial input (`-`, `0.`, `1e`) is common.  `FargvStr` fields are always
parseable.  Booleans and choices never use text entry.

### Implementation note

`_make_validator` gains a second binding via `_make_key_release_validator`,
or the two are merged into a single helper that registers both events.
The `<KeyRelease>` callback should **not** call `evaluate()` — it only tests
parseability (try/except around `type_fn(raw)`) and sets the background.
`evaluate()` is called only at `<FocusOut>` (revert) or explicit Apply/Update.

