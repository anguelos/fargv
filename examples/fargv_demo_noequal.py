#!/usr/bin/env python3
import fargv

params = {
    "anInt": 1,
    "aFloat": 0.1,
    "aBoolean": False,
    "aString": "Hello",
    "aStringReference": "{aString} World",
    "anIntWithHelp": [2, "This would be the help"],
    "aChoice": [("choice1", "choice2", "choice3", "choice4"), "And this must be the help"]
}

if __name__ == "__main__":
    new_params, help_str = fargv.fargv(params, spaces_are_equals=True)
    for k, v in params.items():
        print(k, repr(v), "->", repr(new_params[k]))
