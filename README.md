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
