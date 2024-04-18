from abc import ABC, abstractmethod
from pathlib import Path
import sys
import re
from  .fargv_param_registry import FargvName, __registry as __registry

default_registry = __registry


class FargvParamException(Exception):
    pass


class FargvParam(ABC):
    def __init__(self, name_variants, default_value, help_msg="", registry=default_registry) -> None:
        self.__value = default_value
        self.default_value = default_value
        self.type = None
        self.help_msg = help_msg
        self.registry = registry
        self.registry.insert(name_variants, default_value, self)
        self.value_callback = None

    def get_fargvname(self) -> FargvName:
        return self.registry.get_fargvname_of_param(self)

    def get_main_name(self):
        return self.get_fargvname().get_main_name()

    def get_value(self):
        if self.value_callback is not None:
            return self.value_callback()
        else:
            return self.__value

    def update_value(self, value):
        if self.value_allowed(value):
            self.__value = value
        else:
            raise FargvParamException(f"Invalid value '{repr(value)}' for parameter {self.name}")

    def reset_to_default(self):
        self.update_value(self.default_value)

    @abstractmethod
    def value_allowed(self, value):
        pass

    def __eq__(self, other):
        if isinstance(other, FargvParam):
            return self.get_fargvname() == other.get_fargvname() and self.__value == other.__value and self.default_value == other.default_value
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        t_name = repr(type(self)).split(".")[-1]
        return f"Type: {t_name}. {self.help_msg}. Value set: {self.__value}. Default value: {self.default_value}." 

    @staticmethod
    def get_fargv_type(param_definition):
        if isinstance(param_definition, FargvParam):
            return type(param_definition)
        elif isinstance(param_definition, bool):
            return FargvBool
        elif isinstance(param_definition, int):
            return FargvInt
        elif isinstance(param_definition, float):
            return FargvFloat
        elif isinstance(param_definition, str):
            return FargvRefStr  # TODO (anguelos) by default all Strings are reference strings
        else:
            raise FargvParamException(f"Invalid parameter definition '{param_definition}'")

    @staticmethod
    def create_if_needed(param_name_def, param_definition, help_msg="", *args):
        if isinstance(param_definition, FargvParam):
            assert FargvName(param_name_def) == param_definition.get_fargvname()
            assert help_msg == param_definition.help_msg
            return param_definition
        else:
            return FargvParam.get_fargv_type(param_definition)(param_name_def, param_definition, help_msg=help_msg, *args)


class FargvStr(FargvParam):
    def __init__(self, name_variants, default_value, help_msg="") -> None:
        super().__init__(name_variants, default_value, help_msg=help_msg)
        self.type = str

    def value_allowed(self, value):
        if isinstance(value, str):
            return True
        else:
            return False


class FargvRefStr(FargvParam):
    def __init__(self, name_variants, default_value, help_msg="") -> None:
        super().__init__(name_variants, default_value, help_msg=help_msg)
        self.type = str

    def __infer_value(self, visited_param_names):
        my_parent_val = super().get_value()
        str_names = re.findall(r'{(.*?)}', my_parent_val)
        if len(str_names) == 0:
            return self.get_value()
        if not all([name in self.registry.get_main_names() for name in str_names]):
            print(f"{str_names} not in {self.registry.get_main_names()}")
            raise FargvParamException(f"Invalid reference to parameter name in {my_parent_val}, {str_names}")
        my_name = self.get_fargvname().get_main_name()
        infered_names = {}
        for name in str_names:
            param = self.registry.get_param(name)
            if isinstance(param, FargvRefStr):
                if name in visited_param_names:
                    raise FargvParamException(f"Reference cycle detected for parameter {name}")
                else:
                    infered_names[name] = param.__infer_value(visited_param_names + [my_name])
            else:
                infered_names[name] = param.get_value()
        return my_parent_val.format(**infered_names)

    def value_allowed(self, value):
        if isinstance(value, str):
            str_names = re.findall(r'{(.*?)}', value)
            return all([name in self.registry.__main_names for name in str_names])
        else:
            return False
    
    def get_value(self):
        return self.__infer_value(visited_param_names=[])


class FargvBool(FargvParam):
    def __init__(self, name_variants, default_value, help_msg="") -> None:
        super().__init__(name_variants, default_value, help_msg=help_msg)
        self.__value = False
        self.type = bool
        self.default_value = False  # Default value for boolean type to allow switch like behavior

    def value_allowed(self, value):
        if isinstance(value, bool):
            return True
        if isinstance(value, str):
            value = value.lower()
        if value in [True, False, 1, 0, 1.0, 0.0,  "true", "false", "t", "f"]:
            return True
        return False
    
    def update_value(self, value):
        if value in [True, 1, 1.0, "true", "t"]:
            value = True
        elif value in [False, 0, 0.0, "false", "f"]:
            value = False          
        else:
            raise ValueError(f"Invalid value '{value}' for boolean parameter {self.get_main_name()}")
        return super().update_value(value)
        


class FargvInt(FargvParam):
    def __init__(self, name_variants, default_value, help_msg="", min_max=(None, None)) -> None:
        super().__init__(name_variants, default_value, help_msg=help_msg)
        self.type = int
        self.min_val, self.max_val = min_max

    def value_allowed(self, value):
        try:
            v = int(value)
            if self.min_val is not None and v < self.min_val:
                return False
            if self.max_val is not None and v > self.max_val:
                return False
            return True
        except ValueError:
            return False


class FargvFloat(FargvParam):
    def __init__(self, name_variants, default_value, help_msg="", min_max=(None, None)) -> None:
        super().__init__(name_variants, default_value, help_msg=help_msg)
        self.type = float
        self.min_val, self.max_val = min_max

    def value_allowed(self, value):
        try:
            v = float(value)
            if self.min_val is not None and v < self.min_val:
                return False
            if self.max_val is not None and v > self.max_val:
                return False
            return True
        except ValueError:
            return False


class FargvFname(FargvParam):
    def __init__(self, name_variants, default_value, help_msg="") -> None:
        super().__init__(name_variants, default_value, help_msg=help_msg)
        self.type = Path

    def value_allowed(self, value):
        try:
            _ = Path(value)
        except Exception:
            return False
        return True


class FargvExistingFname(FargvFname):
    def __init__(self, name_variants, default_value, help_msg="") -> None:
        super().__init__(name_variants, default_value, help_msg=help_msg)
        self.type = Path

    def value_allowed(self, value):
        if Path(value).exists():
            return True
        return False

    def get_value(self):
        return Path(self.get_value())


class FargvMissingFname(FargvFname):
    def __init__(self, name_variants, default_value, help_msg="") -> None:
        super().__init__(name_variants, default_value, help_msg=help_msg)
        self.type = Path

    def value_allowed(self, value):
        path = Path(value)
        if path.exists():
            return False
        return True


class FargvFd(FargvParam):
    preopened_values = {"stdin": sys.stdin, "stdout": sys.stdout, "stderr": sys.stderr}

    def __init__(self, name_variants, default_value, help_msg="", mode="", force_exist=False, force_no_exist=True) -> None:
        super().__init__(name_variants, default_value, help_msg=help_msg)
        self.type = Path
        self.fd = None
        self.mode = mode
        assert not (force_exist and force_no_exist)
        self.force_exist = force_exist
        self.force_no_exist = force_no_exist
        assert mode in ("r", "w", "a", "rb", "wb", "ab")
        assert not (mode in ("r", "rb") and force_no_exist)

    def value_allowed(self, value):
        if self.force_exist:
            if not Path(value).exists():
                return False
        if self.force_no_exist:
            if Path(value).exists():
                return False
        if value in ("stdin", sys.stdin) and self.mode in ("r", "a"):
            return True
        if value in ("stdout", sys.stdout) and self.mode in ("w", "a"):
            return True
        if value in ("stderr", sys.stderr) and self.mode in ("w", "a"):
            return True
        path = Path(value)
        if self.mode in ("r", "rb"):
            if not path.exists():
                return False
        return True

    def set_value(self, value):
        if self.fd is not None and value != self.__value and value not in FargvFd.preopened_values:
            self.fd = None  # TODO (anguelos) Must I close the file descriptor? What if I don't own it?
        if value in self.preopened_values:  #  Checking for stdin, stdout, stderr
            self.fd = self.preopened_values[value]
        self.__value = value

    def get_value(self):
        self.__value = FargvParam.get_value(self)  # Triggering any possible callbacks
        if self.fd is not None:
            return self.fd
        else:
            if self.__value == "stdin":
                self.fd = open(0, "r")
            else:
                self.fd = open(self.__value, "r")
            return self.fd


class FargvFdReadBin(FargvParam):
    def __init__(self, name_variants, default_value, help_msg="") -> None:
        super().__init__(name_variants, default_value, help_msg=help_msg, mode="rb")
        self.type = Path
        self.fd = None


class FargvFdWrite(FargvParam):
    def __init__(self, name_variants, default_value, help_msg="") -> None:
        super().__init__(name_variants, default_value, help_msg=help_msg, mode="w")
        self.type = Path
        self.fd = None


class FargvFdWriteBin(FargvParam):
    def __init__(self, name_variants, default_value, help_msg="") -> None:
        super().__init__(name_variants, default_value, help_msg=help_msg, mode="wb")
        self.type = Path
        self.fd = None


class FargvChoice(FargvParam):
    def __init__(self, name_variants, choices, help_msg="") -> None:
        super().__init__(name_variants, default_value=choices, help_msg=help_msg)
        self.type = tuple

    def value_allowed(self, value):
        if value in self.default_value:
            return True
