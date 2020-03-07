# fargv: The laziest command-line argument parser  

## Installation

```bash
pip3 pip install --user --upgrade git+https://github.com/anguelos/fargv
```

## Usage in 3 Simple Steps!

Fast argument parser

* Immport
```python
from fargv import fargv 
```
* Define a dictionary with default parameters
```python
params = {
    "anInt": 1,
    "aFloat": 0.1,
    "aBoolean": False,
    "anotherBoolean": True,
    "aString": "Hello",
    "aStringReference": "{aString} World",
    "anIntWithHelp": [2,"This would be the help"],
    "aChoice": [("choice1","choice2","choice3","choice4"),"And this must be the help"]
}
```

* Parse user provided argv to override defaults
```python
new_params, help_str = fargv(params)
```

* In shell:
```bash
my_program -anInt 34 -aFloat=2.3 -aBoolean -anotherBoolean=False
```

## Features:
* Type checking
* Automatic help generation
* Params usable as dictionary or struct
* Can read environmental variables as well
* macro-parameters
* fast autocomplete generation

### Autocomplete

Static autocomplete for any program using fargv can be enabled with a single command.

The following command enables autocomplete for fargv_demo.py in the current shell where it is run.
```bash
source <(./examples/fargv_demo.py -bash_autocomplete)
```
fargv_demo.py should be an executable file employing the shebang (#!/usr/bin/env python3) or something equivalent.
For a temporary solution, the autocomplete bash code can go in a script in /etc/bash_completion.d or in .bashrc.