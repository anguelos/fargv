from abc import ABC, ABCMeta, abstractmethod
import re
import ast
from pathlib import Path

class FargvValueNotAllowedError(Exception):
    pass


def type_from_definition_data(definition_data):
    if isinstance(definition_data, bool):
        return Bool
    elif isinstance(definition_data, int):
        return Int
    elif isinstance(definition_data, float):
        return Float
    elif isinstance(definition_data, str):
        return StrRef if re.search(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}", definition_data) else Str
    elif isinstance(definition_data, set):
        return Sequence
    elif isinstance(definition_data, tuple):
        return Choice
    elif isinstance(definition_data, list):
        if len(definition_data) == 2:
            return ParamDefinition.type_from_definition_data(definition_data[0])
    elif isinstance(definition_data, ParamDefinition):
        return type(definition_data)
    else:
        raise ValueError("Invalid definition data type")


def create_from_definition_data(definition_data, description=None):
    if isinstance(definition_data, bool):
        return Bool(definition_data)
    elif isinstance(definition_data, int):
        return Int(definition_data)
    elif isinstance(definition_data, float):
        return Float(definition_data)
    elif isinstance(definition_data, str):
        if re.search(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}", definition_data):
            return StrRef(definition_data)
        else:
            return Str(definition_data)
    elif isinstance(definition_data, set):
        return Sequence(definition_data)
    elif isinstance(definition_data, tuple):
        return Choice(definition_data)
    elif isinstance(definition_data, list):
        if len(definition_data) == 2:
            return create_from_definition_data(definition_data[0], description=definition_data[1])
    elif isinstance(definition_data, ParamDefinition):
        return definition_data.copy()
    else:
        raise ValueError("Invalid definition data type")


class ParamDefinition(ABC):
    def __init__(self, *args):
        super().__init__()
        assert not isinstance(args[0], ParamDefinition)  # This is to prevent nesting of ParamDefinitions
        self._registry = None  # Registry is set by the registry when the parameter is registered
        self.__params = args
        self._definition_data = args[0]
        self._description = args[1]
        self._value = args[0]

    def create_callback(self):
        return lambda: self.get_value()

    def get_value(self):
        return self._value
    
    @abstractmethod
    def value_allowed(self, value):
        passattribute

    def update_value(self, value):
        if not self.value_allowed(value):
            raise FargvValueNotAllowedError(f"Invalid value '{value}' for parameter")
        self._value = value

    def __str__(self):
        return f"{type(self).__name__}\n\tDefinition Data: {self._definition_data}\n\tCached Value: {self._value}\n\tDescription: {self._description}"

    def __repr__(self):
        return f"{type(self).__name__}({self.__params})"

    def copy(self, registry=None):
        res = type(self)(*self.__params)
        res.register_param(registry)
        return res

    def register_param(self, registry):
        self._registry = registry
        return self


class Bool(ParamDefinition):
    def __init__(self, definition_data=False, description=" A boolean parameter"):
        super().__init__(definition_data, description)
        self._value = definition_data

    def value_allowed(self, value):
        return isinstance(value, bool) or value in [1, 0, 1.0, 0.0, "True", "False", "true", "false", "t", "f"]


class Int(ParamDefinition):
    def __init__(self, definition_data=0, description="An Integer parameter", val_range=None):
        super().__init__(definition_data, description, val_range)
        self.val_range = val_range
        if self.value_allowed(definition_data):
            self._value = definition_data
        else:
            raise FargvValueNotAllowedError(f"Invalid definition '{definition_data}' during construction")

    def value_allowed(self, value):
        try:
            value = int(value)
        except ValueError:
            return False
        if self.val_range is not None:
            return self.val_range[0] <= value <= self.val_range[1]
        else:
            return True


class Float(ParamDefinition):
    def __init__(self, definition_data=0.0, description="A float parameter", val_range=None):
        super().__init__(definition_data, description, val_range)
        self.val_range = val_range
        if self.value_allowed(definition_data):
            self._value = definition_data
        else:
            raise FargvValueNotAllowedError(f"Invalid definition '{definition_data}' during construction")

    def value_allowed(self, value):
        try:
            value = float(value)
        except ValueError:
            return False
        if self.val_range is not None:
            return self.val_range[0] <= value <= self.val_range[1]
        else:
            return True


class Str(ParamDefinition):
    def __init__(self, definition_data="", description="A string parameter"):
        super().__init__(definition_data, description)
        self._value = definition_data

    def value_allowed(self, value):
        return isinstance(value, str)


class StrRef(Str):
    """A string parameter that references other parameters in the Registry.
    
    The value of this parameter is a string that can contain references to other parameters in the registry.
    The references are in the form of {parameter_name}.
    This is the liberal version of the StrRef parameter, which will not evaluate unregistered names in brackets and preserve them.
    """
    def __init__(self, definition_data="", description="A referenced string parameter"):
        super().__init__(definition_data, description)
        self._value = definition_data

    def value_allowed(self, value):
        if not isinstance(value, str):
            return False
        references = [s[1:-1] for s in re.findall(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}", value)]
        if self.registry is None:
            return False
        if not all(ref in self._registry for ref in references):
            return False
        else:
            return True

    def __infer(self, seen_names, registry):
        my_name = registry.get_name_of_param(self)
        references = [s[1:-1] for s in re.findall(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}", self._value)]
        if my_name in seen_names:
            raise FargvValueNotAllowedError(f"Circular reference detected for parameter '{my_name}'")        
        ref_dict = {}
        for ref in references:
            try:
                ref_param = registry.get_param(ref)
                if isinstance(ref_param, StrRef):
                    ref_dict[ref] = ref_param.__infer(seen_names=seen_names + [my_name], registry=registry)
                else:
                    ref_dict[ref] = ref_param.get_value()
            except KeyError:
                ref_dict[ref] = "{" + ref + "}"
        result = self._value.format(**ref_dict)
        return result

    def get_value(self):
        if self._registry is None:
            return self._value
        else:
            return self.__infer([], self._registry)


class Choice(Str):
    def __init__(self, definition_data=tuple([""]), description="A choice parameter"):
        super().__init__(definition_data, description)
        assert len(definition_data) > 0
        self._choices = definition_data
        self._value = self._choices[0]

    def value_allowed(self, value):
        return value in self._choices


class Literal(Str):
    def __init__(self, definition_data="0", description="A python literal parameter"):
        super().__init__(definition_data, description)
        if self.value_allowed(definition_data):
            self._value = definition_data
        else:
            raise FargvValueNotAllowedError(f"Invalid definition '{definition_data}' during construction")

    def value_allowed(self, value):
        try:
            _ = ast.literal_eval(value)
            return True
        except ValueError:
            return False

    def get_value(self):
        return ast.literal_eval(self._value)


class Src(Str):
    def __init__(self, definition_data="0 + 0", description="A python source parameter"):
        super().__init__(definition_data, description)
        if self.value_allowed(definition_data):
            self._value = definition_data
        else:
            raise FargvValueNotAllowedError(f"Invalid definition '{definition_data}' during construction")

    def value_allowed(self, value):
        try:
            _ = eval(value, {}, {})
            return True
        except Exception:
            return False

    def get_value(self):
        try:
            res = eval(self._value, {}, {})
            return res
        except Exception:
            raise FargvValueNotAllowedError(f"Invalid python source '{self._value}' for parameter")


class Sequence(ParamDefinition):
    def __init__(self, definition_data=set([]), description="A sequence parameter", element_type=Str, min_len=0):
        super().__init__(definition_data, description, element_type)
        self._element_type = element_type
        self._element_type_instance = element_type()
        self._min_len = min_len
        if self.value_allowed(definition_data):
            self._value = definition_data
        else:
            raise FargvValueNotAllowedError(f"Invalid definition '{definition_data}' during construction")

    def value_allowed(self, value):
        if type(value) not in (list, tuple, set, Sequence):
            return False
        if len(value) < self._min_len:
            return False
        if any(not self._element_type_instance.value_allowed(v) for v in value):
            return False
        return True
