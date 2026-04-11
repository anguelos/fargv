# fargv Examples

## `git_like.py` — subcommands (dict API)

A git-style CLI with three subcommands (`commit`, `push`, `log`) and a
shared parent-level `--verbose` flag.  Demonstrates the dict API and
`subcommand_return_type="flat"`.

**Requirements:** only `fargv`

```bash
python examples/git_like.py --help
python examples/git_like.py commit --message="fix bug" --amend
python examples/git_like.py push --remote=upstream --branch=main --force
python examples/git_like.py --verbose log --max_count=5
```

---

## `sklearn_demo.py` — dataclass API with choices, subcommands, and numeric params

Trains and evaluates a scikit-learn classifier on a built-in dataset.
The entire fargv configuration lives in a single `@dataclass`:

- **Choice** — `--dataset` (iris / digits / breast_cancer / wine) and
  `--kernel` (rbf / linear / poly, inside the `svm` subcommand)
- **Subcommands** — the classifier is selected as a subcommand
  (`knn`, `svm`, `rf`, `logistic`), each with its own hyperparameters
- **Float params** — `--test_size`, `--C` (regularisation strength)
- **Int params** — `--random_seed`, `--n_neighbors`, `--n_estimators`,
  `--max_depth`

**Requirements:** `fargv`, `scikit-learn`

```bash
pip install scikit-learn

python examples/sklearn_demo.py knn
python examples/sklearn_demo.py knn --dataset=wine --n_neighbors=7
python examples/sklearn_demo.py svm --C=0.5 --kernel=linear
python examples/sklearn_demo.py rf  --n_estimators=200 --max_depth=3
python examples/sklearn_demo.py logistic --dataset=digits --C=10.0
```

Running without a subcommand prints help.

---

## `jupyter/fargv_jupyter_demo.ipynb` — fargv inside Jupyter notebooks

Five notebook sections covering every Jupyter-specific usage pattern:

1. **Dict shortcut** — pass `given_parameters={"key": val, …}` to bypass
   CLI parsing and fix values directly in a cell (useful for reproducible
   experiments).
2. **`jupyter` GUI mode** — `fargv.parse(…, ui='jupyter')` auto-renders
   an ipywidgets form; execution blocks until the user clicks *Apply*.
3. **Interactive mode** (`render_interactive`) — keeps the widget panel
   live during a long-running cell; *Update* pushes new values mid-run,
   *Kill* sends `SIGTERM`.
4. **Config persistence** — save and reload parameter snapshots to JSON
   with `dump_config` / `load_config`.
5. **Help string display** — `fargv.parse` always returns
   `(namespace, help_str)`; print it in a cell for a quick parameter
   reference.

**Requirements:** `fargv`, `ipywidgets`, JupyterLab or classic Notebook

```bash
pip install fargv ipywidgets
jupyter lab examples/jupyter/fargv_jupyter_demo.ipynb
```

## `scenario/` — demo GIF production

`examples/scenario/` contains the scripts used to record the animated demo
(`docs/_static/demo.gif`) that appears at the top of the README.  The scenario
walks a total newcomer through adding fargv to a plain Python script in six
scenes:

1. Display `word_count.py` — a minimal word-frequency script with no CLI.
2. Run `word_count.py` with its hard-coded defaults.
3. Show the diff between `word_count.py` and `word_count_fargv.py` (the
   fargv-enabled version) using `delta`.
4. Run `python word_count_fargv.py -h` to show the auto-generated help.
5. Run `word_count_fargv.py` with defaults.
6. Run `word_count_fargv.py -v` to show verbosity in action.

### Files

| File | Purpose |
|---|---|
| `word_count.py` | Original script — hard-coded path and min-length |
| `word_count_fargv.py` | Same script after adding `fargv.parse({…})` |
| `example.txt` | Sample text file used by both scripts |
| `scenario.sh` | Shell script that drives all scenes with typed-out commands |
| `agg` | Pre-downloaded `agg` binary (asciinema → GIF converter) |

### Requirements

```bash
pip install asciinema pandas
sudo apt-get install bat git-delta
```

`agg` is included as a pre-built binary in the `scenario/` directory.  To
download a fresh copy:

```bash
wget https://github.com/asciinema/agg/releases/latest/download/agg-x86_64-unknown-linux-gnu -O examples/scenario/agg
chmod 755 examples/scenario/agg
```

### Recording the GIF

Run from the `examples/scenario/` directory:

```bash
cd examples/scenario/
asciinema rec /tmp/demo.cast --overwrite --command="bash ./scenario.sh"
./agg /tmp/demo.cast /tmp/demo.gif
cp /tmp/demo.gif ../../docs/_static/demo.gif
```
