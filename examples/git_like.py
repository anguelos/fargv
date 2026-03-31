"""Simple subcommand example — a git-like tool.

Usage
-----
::

    # list available subcommands
    python examples/git_like.py --help

    # commit subcommand
    python examples/git_like.py commit --message="fix bug" --amend

    # push subcommand
    python examples/git_like.py push --remote=upstream --branch=main --force

    # log subcommand (with parent-level --verbose)
    python examples/git_like.py --verbose log --max_count=5
"""
import fargv

p, _ = fargv.parse(
    {
        "verbose": False,          # parent-level flag shared by all subcommands
        "cmd": {                   # nested dict → inferred as FargvSubcommand
            "commit": {
                "message": ("", "Commit message"),
                "amend":   False,
                "all":     False,
            },
            "push": {
                "remote": "origin",
                "branch": "HEAD",
                "force":  False,
            },
            "log": {
                "max_count": 10,
                "oneline":   False,
                "author":    "",
            },
        },
    },
    subcommand_return_type="flat",
)

if p.cmd == "commit":
    action = "amend last commit" if p.amend else "create commit"
    stage  = " (all tracked files)" if p.all else ""
    print(f"[commit] {action}{stage}: {p.message!r}")

elif p.cmd == "push":
    flag = " --force" if p.force else ""
    print(f"[push] {p.remote} {p.branch}{flag}")

elif p.cmd == "log":
    filters = []
    if p.author:
        filters.append(f"author={p.author!r}")
    if p.oneline:
        filters.append("oneline")
    extra = f"  filters: {', '.join(filters)}" if filters else ""
    print(f"[log] last {p.max_count} commits{extra}")

if p.verbose:
    print("(verbose mode on)")
