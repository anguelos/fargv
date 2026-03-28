import os
import os
import sys
from typing import Dict, Optional, Tuple, Literal, List, Union, Any
from abc import ABC, abstractmethod
import re
from pathlib import Path
import io


class FargvError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class FargvParameter(ABC):
    def __init__(self, default: Any = None, name: Optional[str]=None, short_name: Optional[str] = None, description: Optional[str]=None) -> None:
        super().__init__()
        self._name = name
        self._short_name = short_name
        self._description = description
        self._default = default
        self._value = default
    
    def set_name(self, name: str):
        self._name = name

    def set_short_name(self, short_name: str):
        self._short_name = short_name

    @property
    def is_positional(self) -> bool:
        return False

    @property
    def is_bool(self) -> bool:
        return False

    @property
    def exit_if_true(self) -> bool:
        return False


    @property
    def is_string(self) -> bool:
        return False
    
    @property
    def has_value(self) -> bool:
        return self._value is not None

    @classmethod
    def _get_class_type(cls) -> type:
        raise NotImplementedError("Subclasses of FargvParameter must implement the _get_class_type method.")

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def prety_name(self) -> str:
        words = self._name.split("_")
        return " ".join(word.capitalize() for word in words)

    @property
    def short_name(self) -> str:
        return self._short_name 


    @property
    def description(self) -> str:
        return self._description

    @property
    def default(self) -> Any:
        return self._default

    @property
    def value(self) -> Any:
        return self._value
    
    @property
    def value_str(self) -> str:
        return str(self._value)
    
    @property
    def docstring(self) -> str:
        name_str = f"--{self._name}"
        shortname_str = f"-{self._shortname}" if self._shortname is not None else ""
        type_str = f"Type: {repr(self._get_class_type())}"
        description_str = self._description if self._description is not None else ""
        default_str = f" Default: {repr(self._default)}"
        return f"{name_str} {shortname_str} {type_str} {description_str}{default_str}"

    def validate_value_strings(self, *values: List[str]) -> bool:
        try:
            for value in values:
                self._get_class_type()(value)
            return True
        except ValueError:
            return False

    def ingest_value_strings(self, *values: List[str]) -> List[str]:
        if len(values) < 1:
            raise FargvError(f"Parameter '{self._name}' accepts a single value")
        self._value = self._get_class_type()(values[0])
        return values[1:]



class FargvInt(FargvParameter):
    def __init__(self, default: int = 0, name: Optional[str]=None, short_name: Optional[str]=None, description: Optional[str]=None) -> None:
        super().__init__(default, name, short_name, description)

    @classmethod
    def _get_class_type(cls) -> type:
        return int


class FargvFloat(FargvParameter):
    def __init__(self, default: float = 0.0, name: Optional[str]=None, short_name: Optional[str]=None, description: Optional[str]=None) -> None:
        super().__init__(default, name, short_name, description)

    @classmethod
    def _get_class_type(cls) -> type:
        return float

    
class FargvBool(FargvParameter):
    def __init__(self, default: bool = False, name: Optional[str]=None, short_name: Optional[str]=None, description: Optional[str]=None) -> None:
        super().__init__(default, name, short_name, description)

    @classmethod
    def _get_class_type(cls) -> type:
        return bool
    
    def is_bool(self) -> bool:
        return True
    
    def ingest_value_strings(self, *values: List[str]):
        if self._default == False and len(values) == 0:
            self._value = True
        elif values[0].lower() in ["1", "0", "t", "f", "true", "false"]:
            self._value = values[0].lower() in ["1", "t", "true"]
            return values[1:]
        else:
            raise FargvError(f"Boolean parameter '{self._name}' accepts a single value which can be one of '0', '1', 't', 'f', 'true', or 'false' (case insensitive), or no value at all to set it to True.")


class FargvBoolHelp(FargvBool):
    def __init__(self, param_parser):
            super().__init__(default=False, name="help", short_name="h", description="Show this help message and exit")
            self._param_parser = param_parser

    @property
    def exit_if_true(self) -> bool:
        return True

    def ingest_value_strings(self, *values: List[str]):
        if (self._default == False and len(values) == 0) or values[0].lower() in ["1", "t","true"]:
            self._value = True
        elif values[0].lower() in ["1", "0", "t", "f", "true", "false"]:
            print(self._param_parser.generate_help_message(), file=sys.stdout)
            sys.exit(0)
        else:
            raise FargvError(f"Boolean parameter '{self._name}' accepts a single value which can be one of '0', '1', 't', 'f', 'true', or 'false' (case insensitive), or no value at all to set it to True.")




class FargvStr(FargvParameter):
    def __init__(self, default: str = "", name: Optional[str]=None, short_name: Optional[str]=None, description: Optional[str]=None) -> None:
        super().__init__(default, name, short_name, description)
        self.other_string_params: Dict[str, FargvStr] = {}
    
    @property
    def value(self) -> str:
        def resolve(key: str, visiting: set[str]) -> str:
            if key not in self.other_string_params:
                return f"{{{key}}}"  # Leave unknown references as-is

            if key in visiting:
                raise ValueError(f"Circular reference detected involving key: '{key}'")

            visiting.add(key)

            def replace_ref(match):
                ref_key = match.group(1)
                return resolve(ref_key, visiting)

            result = re.sub(r"\{(\w+)\}", replace_ref, self.other_string_params[key].value)
            visiting.remove(key)  # Remove after resolving so siblings can reuse it
            return result
        return resolve(self._name, set())

    @classmethod
    def _get_class_type(cls) -> type:
        return str


class FargvChoice(FargvParameter):
    def __init__(self, choices: List[str], default: Optional[str] = None, name: Optional[str]=None, short_name: Optional[str]=None, description: Optional[str]=None) -> None:
        if default is None:
            default = choices[0]
        super().__init__(default, name, short_name, description)
        self._choices = choices

    @classmethod
    def _get_class_type(cls) -> type:
        return tuple

    def validate_value_strings(self, *values: List[str]) -> bool:
        assert len(values) == 1
        return values[0] in self._choices


class FargvPostional(FargvParameter):
    def __init__(self, default: Optional[List[str]] = None, name: Optional[str]=None, short_name: Optional[str]=None, description: Optional[str]=None) -> None:
        super().__init__(default, name, short_name, description)

    @property
    def is_positional(self) -> bool:
        return True

    @classmethod
    def _get_class_type(cls) -> type:
        return list
    
    def ingest_value_strings(self, *values: List[str]) -> List[str]:
        self._value = values


class FargvStream(FargvParameter):
    def __init__(self, name: str, default: Union[io.TextIOBase, Literal["stderr", "stdout", "stdin"]], short_name: Optional[str]=None, description: Optional[str]=None) -> None:
        super().__init__(name, default, short_name, description)
        self.mode = default.mode
        
        if default is sys.stderr:
            self.original_path = "stderr"
        elif default is sys.stdout:
            self.original_path = "stdout"
        elif default is sys.stdin:
            self.original_path = "stdin"
        else:
            self.original_path = "N/A"
    
    @classmethod
    def _get_class_type(cls) -> type:
        return io.TextIOBase
    
    def validate_value_strings(self, value: str) -> bool:
        def can_mkdir_p(path: Path) -> bool:
            path = Path(path).resolve()
            parent = next((p for p in [path, *path.parents] if p.exists()), None)
            return parent is not None and os.access(parent, os.W_OK | os.X_OK)
        if self.mode == "r":
            try:
                with open(value, self.mode) as f:
                    return True
            except Exception:
                return False
        elif self.mode == "w":
            path = Path(value)
            if path.exists():
                return False # we want to forbid overwriting
            else:
                return can_mkdir_p(path)
    
    def set_value_str(self, *values: List[str]) -> List[str]:
        if len(values) < 1:
            raise FargvError(f"Paramenter {self.name} requires one value")
        if values[0] == "stdout":
            assert self.mode in ("w", "a"), "stdout stream parameter must be opened in write or append mode"
            self._value = os.sys.stdout
            self.original_path = "stdout"

        elif values[0] == "stderr":
            assert self.mode in ("w", "a"), "stderr stream parameter must be opened in write or append mode"
            self._value = os.sys.stderr
            self.original_path = "stderr"

        elif values[0] == "stdin":
            assert self.mode == "r", "stdin stream parameter must be opened in read mode"
            self._value = os.sys.stdin
            self.original_path = "stdin"

        else:
            path = Path(values[0])
            self.original_path = values[0]
            if self.mode == "w":
                assert not path.exists(), f"File '{values[0]}' already exists, refusing to overwrite."
                if not path.parent.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                self._value = open(values[0], self.mode)
            elif self.mode == "r":
                assert path.exists(), f"File '{values[0]}' does not exist, cannot open for reading."
                self._value = open(values[0], self.mode)
            elif self.mode == "a":
                if not path.parent.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                self._value = open(values[0], self.mode)
            else:
                raise ValueError(f"Unsupported mode '{self.mode}' for stream parameter '{self._name}'")
        return values[1:]

    @property
    def value_str(self) -> str:
        if self._value is sys.stdout:
            return "sys.stdout"
        elif self._value is sys.stdin:
            return "sys.stdin"
        elif self._value is sys.stderr:
            return "sys.stderr"
        else:
            return f"open('{self.original_path}', '{self.mode}')"

    def __del__(self):
        if isinstance(self._value, io.TextIOBase) and self._value not in (sys.stdout, sys.stderr, sys.stdin):
            self._value.close()


class ArgumentParser:
    def __init__(self, progname:str=None, parameters: Union[List[FargvParameter], Dict[str, FargvParameter]] = [], 
        allow_default_positional: bool = True,
        auto_help: bool = True,
        auto_bash_autocomplete: bool = True):
        self._name2parameters : Dict[str, FargvParameter] = {}
        self._shortname2parameters : Dict[str, FargvParameter] = {}
        self.allow_default_positional = allow_default_positional
        if isinstance(parameters, list):
            for param in parameters:
                self.__add_parameter(param)
        elif isinstance(parameters, dict):
            for param_name, param in parameters.items():
                if param.name is None:
                    param.set_name(param_name)
                self.__add_parameter(param)
        else:
            raise TypeError("parameters must be a list or a dict")
    
    def __has_default_positional(self) -> bool:
        return len([p for p in self._name2parameters.values() if p.is_positional]) == 1  #  We must have only one position for it 

    def __get_default_positional(self) -> Optional[FargvPostional]:
        res = [p for p in self._name2parameters.values() if p.is_positional]
        if len(res) == 1 and self.allow_default_positional:
            return res[0]
        else:
            return None

    def __add_parameter(self, parameter:FargvParameter):
        assert parameter.name is not None
        assert parameter.name not in self._name2parameters, f"Duplicate parameter name '{parameter.name}'"
        self._name2parameters[parameter.name] = parameter
        if parameter.short_name is not None:
            if parameter.short_name is not None and parameter.short_name in self._shortname2parameters:
                raise ValueError(f"Duplicate parameter short name '{parameter.short_name}'")
            self._shortname2parameters[parameter.short_name] = parameter
    
    def __parse_arguments(self, argv: List[str], first_is_name: bool = True):
        if first_is_name and len(argv) > 0:
            self.name = argv[0]
            argv = argv[1:]
        expanded_argv = []
        for arg in argv:
            if arg.startswith("-") and not arg.startswith("--") and len(arg):
                if len(arg) > 2:
                    assert all(c in self._shortname2parameters and self._shortname2parameters[c]._default is False for c in arg[1:]), f"{repr(arg)}: Only boolean by default False short parameters can be merged'{arg}'"
                for c in arg[1:]:
                    expanded_argv.append(f"--{self._shortname2parameters[c].name}")
            else:
                expanded_argv.append(arg)
        param_pos = [n for n, arg in enumerate(expanded_argv) if arg.startswith("--") and not arg.startswith("---")]
        param_pos.append(len(expanded_argv))
        analysed_argument_names: List[str] = []
        unaccounted_positionals: List[List[str]] = []
        for n in range(len(param_pos)-1):
            param_start, param_end = param_pos[n], param_pos[n+1]
            param_name = expanded_argv[param_start].lstrip("-")
            if param_name not in self._name2parameters:
                raise FargvError(f"unknown parameter --{param_name}")
            if param_name in analysed_argument_names:
                raise FargvError(f"parameter --{param_name} specified multiple times previous value: {self._name2parameters[param_name].value}")
            unpocessed_positionals = self._name2parameters[param_name].append_value_strings(*expanded_argv[param_start+1:param_end])
            unaccounted_positionals.append(unpocessed_positionals)
            analysed_argument_names.append(param_name)

        if len(unaccounted_positionals) > 0:
            default_positional = self.__get_default_positional()
            if default_positional is not None:
                flattened_positionals = []
                for positionals in unaccounted_positionals:
                    flattened_positionals+= positionals
                default_positional.append_value_strings(*flattened_positionals)
            else:
                raise FargvError(f"Nameless positional arguments were found, but no default positional parameter is defined: {unaccounted_positionals}")


    def __generate_bash_autocomplete(self):
        """Creates bash code for autocomplete

        :param default_switches: a dictionary with the switches definitions
        :param full_filename: The filename of the current program. If None, sys.argv[0] is used.
        :return: A string with bash commands that enable autocomplete
        """
        commands = " ".join([f"--{k}" for k in self._name2parameters.keys()])
        fname = self.name if hasattr(self, "name") else os.path.basename(sys.argv[0])
        full_filename = fname.split("/")[-1]
        name = fname.split(".")[0]
        autocomplete_script = f"""# Static autocomplete generator.
    #
    # Enable in current shell:
    # source <({full_filename} -bash_autocomplete)
    #
    # Or add the following code in a file in /etc/bash_completion.d
    _myscript_tab_complete_{name} () {{
        local cur prev opts
        COMPREPLY=()
        cur="${{COMP_WORDS[COMP_CWORD]}}"
        prev="${{COMP_WORDS[COMP_CWORD-1]}}"
        words="{commands}"

        COMPREPLY=( $(compgen -W "${{words}}" -- ${{cur}}) )
        return 0
    }}
    complete -F _myscript_tab_complete_{name} {fname}
    """
        return autocomplete_script

    def generate_help_message(self) -> str:
        lines = [f"Usage: {self.name if hasattr(self, 'name') else os.path.basename(sys.argv[0])} [OPTIONS]"]
        for param in self._name2parameters.values():
            lines.append(f"  --{param.name}" + (f", -{param.short_name}" if param.short_name is not None else "") + f": {param.description} (Type: {repr(param._get_class_type())}, Default: {repr(param.default)})")
        return "\n".join(lines)