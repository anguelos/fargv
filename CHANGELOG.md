# Changelog

All notable changes to fargv are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

---

## [1.3.1] — 2026-04-11

### Changed

- **`FargvPositional` renamed to `FargvVariadic`** — fargv's unmatched-token
  collector is not a classical positional argument (position-inferred identity);
  it collects 0-N argv tokens that were not consumed by any named flag.
  "Variadic" is the standard term for this concept (cf. Click's `nargs=-1`,
  POSIX operands). `FargvPositional` and `FargvPostional` are kept as
  backward-compatible aliases but will be removed in a future release.
  Related renames:
  - `FargvParameter.is_positional` → `is_variadic`
  - `ArgumentParser.allow_default_positional` → `allow_default_variadic`
  - `fargv.parse(allow_implied_positionals=...)` → `allow_implied_variadics`


- **Config file and env-var system redesigned** — flat key convention replaces
  the old nested dict format; unified `apply_overrides` core shared by both
  sources; multiple dump formats (JSON, INI, TOML, YAML) with rich comments;
  `//format` dump-and-exit syntax (`--config //ini` etc.) prints to stdout and
  suggests the correct save path on stderr; `-C` added as short alias for
  `--config`; unknown keys now warn to stderr and discard the whole dict by
  default (`unknown_keys="ignore_dict_and_warn"`); `FargvVariadic` params
  excluded from config dumps to prevent stale-override bugs. Key changes:
  - Subcommand branch params use flat dotted keys in config files
    (`train.lr`) and flat underscored env vars (`APPNAME_TRAIN_LR`).
  - `fargv_comment*` keys in JSON are silently dropped by the loader and
    written automatically by dump functions to annotate each param.
  - `unknown_keys` policy: `"ignore_dict_and_warn"` (default),
    `"ignore_key_and_warn"`, or `"raise"`.

- **`{key}` string interpolation available in all definition styles** — was
  previously wired up only for the plain-dict style.  The `_link_string_params`
  helper is now called from `dict_to_parser`, `function_to_parser`, and
  `dataclass_to_parser`, so function signatures and dataclasses support the
  same cross-parameter interpolation.

- **`{key}` interpolation resolves against any parameter type** — previously
  only `FargvStr` siblings were available.  Now any registered parameter can
  be referenced: `{epochs}` in a string default expands to the current value
  of an `int` parameter, `{codec}` to a choice string, etc.

### Added

- **`ArgumentParser._finalize_string_params()`** — new method called at the
  end of every `parse()` invocation (after all sources: config, env vars, CLI).
  Bakes resolved `{key}` values back into `FargvStr._value` so that anything
  reading `_value` directly (config dumps, GUI backends, `FargvNamespace`)
  sees the fully resolved string rather than the original template.

### Fixed

- **Auto-config creation disabled** — `init_config_if_missing` was called on
  every `fargv.parse()` invocation, silently writing a config file on first run
  and persisting parameter defaults across code changes. A stale config from an
  old script version (e.g. `FargvVariadic([])`) would override a later coded
  default (e.g. `FargvVariadic(['b','a'])`) on all subsequent runs, with no
  warning. The symptom appeared as an unrelated parameter (e.g. `FargvChoice`)
  changing the behaviour of `FargvVariadic` — it was merely making the config
  schema match so the stale config got applied. Fix: auto-creation is now
  disabled; config files must be created explicitly. Reported by: nprenet.

---

[Unreleased]: https://github.com/anguelos/fargv/compare/v1.3.1...HEAD
[1.3.1]: https://github.com/anguelos/fargv/compare/v1.3.0...v1.3.1
