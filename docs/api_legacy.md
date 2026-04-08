# Legacy API Reference

## Backwards compatibility

`fargv.fargv` is the original fargv parser, present since the first release.
It is exposed at the package top level so that existing scripts continue to
work unchanged:

```python
from fargv import fargv          # legacy entry point
p, help_str = fargv({"lr": 0.01, "epochs": 10, "verbose": False})
```

The legacy API uses **single-dash** (`-name=value`) syntax and is **frozen**
— it receives no new features, only bug fixes.  New scripts should use
`fargv.parse` instead, which offers four definition styles, richer types,
env-var overrides, config files, and standard double-dash (`--name=value`)
syntax.

| | `fargv.fargv` (legacy) | `fargv.parse` (current) |
|---|---|---|
| CLI syntax | `-name=value` | `--name=value` |
| Short aliases | auto | auto |
| Config file | ❌ | ✅ JSON / YAML / TOML / INI |
| Env-var overrides | ✅ (bare `PARAMNAME`) | ✅ (`APPNAME_PARAMNAME`) |
| Rich types | ❌ | ✅ `Fargv*` classes |
| Mandatory params | ❌ | ✅ `fargv.REQUIRED` |
| GUI backends | ❌ | ✅ `--user_interface=tk/qt` |
| New features | ❌ frozen | ✅ actively developed |

---

## Main function

```{eval-rst}
.. autofunction:: fargv.fargv_legacy.fargv
```

---

## Helper functions

```{eval-rst}
.. autofunction:: fargv.fargv_legacy.fargv2dict
```

```{eval-rst}
.. autofunction:: fargv.fargv_legacy.can_override
```

```{eval-rst}
.. autofunction:: fargv.fargv_legacy.override
```

```{eval-rst}
.. autofunction:: fargv.fargv_legacy.generate_bash_autocomplete
```
