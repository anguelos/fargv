# Command Line Reference

Every script using `fargv.fargv` automatically inherits the following
built-in parameters.

## -help / -h

Prints a help message listing all parameters with their types, descriptions,
defaults, and current values, then exits.

```bash
python myscript.py -help
```

Example output:

```text
myscript.py Syntax:

    -name=<class 'str'>  Default 'world' . Passed 'world'
    -count=<class 'int'>  Default 1 . Passed 1
    -verbose=<class 'bool'>  Default False . Passed False
```

## -bash_autocomplete

Prints a bash script that enables tab-completion for the current program.
Source it in your shell or drop it in `/etc/bash_completion.d`:

```bash
source <(python myscript.py -bash_autocomplete)
```

## -v

Sets the verbosity level (integer, default 1). Used internally by
`fargv.util.warn` — higher values produce more output.

```bash
python myscript.py -v=2
```
