from .fargv_param_registry import Name, Registry, FargvNameException, FargvDuplicateNameException
from .fargv_param_value import Bool, Int, Float, Str, Choice, Literal, Src, StrRef, create_from_definition_data, type_from_definition_data, ParamDefinition, Sequence


debug=print

class FargvArgparseException(Exception):
    pass


class UnixArgParser:
    def __init__(self, registry, short_separator="-", long_separator="--", allow_nameless_positionales=True) -> None:
        assert len(short_separator) >= len(long_separator)
        self.__allow_nameless_positionals = False # If True, nameless positional arguments are considered params to None param_names
        self.__short_separator = short_separator
        self.__full_separator = "--"
        self.__assignment_separators = ("=",)
        self.__registry = registry

    def parse(self, argv: list[str]):
        """Parse the argv list and return a dictionary of the parsed values."""
        name = argv[0]
        if name.startswith(self.__full_separator) or name.startswith(self.__short_separator):
            raise FargvArgparseException(f"Invalid name '{name}', names shoud not have separators")
        separator_param_values = list(self.split_args(argv))
        separator_param_values = list(self.expand_switches(separator_param_values))
        separator_param_values = list(self.expand_assignmets(separator_param_values))
        key_values = list(self.simplify_separator_param_values(separator_param_values))
        key_values, nameless_positionals = self.get_nameless_positionals(key_values)
        return name, dict(key_values), nameless_positionals

    def get_nameless_positionals(self, key_values):
        """Get the nameless positional arguments."""
        res = [kv for kv in key_values if kv[0] is not None]
        positionals = [values for key, values in key_values if key is None]
        return res, positionals

    def simplify_separator_param_values(self, separator_param_values):
        for separator, param, values in separator_param_values:
            if param in self.__registry.get_short_names() and separator != self.__short_separator:
                raise FargvArgparseException(f"A short param '{param}' requires the short separator '{self.__short_separator}'")
            if len(values) == 0:
                raise FargvArgparseException(f"Parameter '{param}' has no value even after expantion.")
            if len(values) > 1:
                if not isinstance(self.__registry.get_param(param), Sequence) and param is not None:
                    raise FargvArgparseException(f"Parameter '{param}' has multiple values but is not a sequence.")
                if param is None and not self.__allow_nameless_positionals:
                    raise FargvArgparseException(f"Nameless positional arguments are not allowed.")
                yield param, values
            else:
                yield param, values[0]

    def expand_assignmets(self, separator_param_values):
        for separator, param, values in separator_param_values:
            sep_occ = [n for n in param if n in self.__assignment_separators]
            if len(sep_occ) == 1:
                new_param, new_value = param.split(sep_occ[0])  #  This is a tuple
                yield separator, new_param, [new_value]
                if len(values) > 0 and not self.__allow_nameless_positionals:
                    raise FargvArgparseException(f"Multiple values found following parameter '{param}' assignment")
                elif len(values) > 0 and self.__allow_nameless_positionals:
                    yield self.__full_separator, None, values
            elif values[0] in self.__assignment_separators:
                values = values[1:]
                if len(values) == 0:
                    raise FargvArgparseException(f"Parameter '{param}' assignment has not value")
                yield separator, param, values
                if self.__allow_nameless_positionals == True and len(values) > 1:
                    yield self.__full_separator, None, values[1:]
            else:
                yield separator, param, values


    def expand_switches(self, separator_param_values):
        """Expand the short switches to their full names."""
        for separator, param_name, param_values in separator_param_values:
            if separator == self.__short_separator:
                if (param_name not in self.__registry.get_all_names() #  this is not a parameter name
                        and all(n in self.__registry.get_short_names() for n in param_name) #  this is are all plausible parameter short names
                        and all(isinstance(self.__registry.get_param(n), Bool) for n in param_name)): #  all parameters are boolean
                    for n in param_name:
                        yield self.__short_separator, n, "1"
                    if not self.__allow_nameless_positionals and len(param_values) > 0:
                        raise FargvArgparseException(f"Nameless positional arguments are not allowed. They were found following '{param_name}'")
                    else:
                        yield self.__full_separator, None, "1"
                else:
                    raise FargvArgparseException(f"Unknown parameter '{param_name}'")
            yield separator, param_name, param_values

    def split_args(self, argv: list[str]):
        """Split the argv list into positional and keyword arguments."""
        param_border_positions = []
        for n, arg in enumerate(argv):
            if arg.startswith(self.__full_separator) or arg.startswith(self.__short_separator):
                param_border_positions.append(n)
        param_border_positions.append(len(argv))
        if len(param_border_positions) > 1 and param_border_positions[0] != 1 and not self.__allow_nameless_positionals:
            debug("DBG param_border_positions:", param_border_positions)
            debug("DBG argv:", argv)
            raise FargvArgparseException("Nameless positional arguments are not allowed.")
        elif param_border_positions[0] != 1 and self.__allow_nameless_positionals:
            yield self.__full_separator, None, argv[1:param_border_positions[0]]
        for n in range(len(param_border_positions) - 1):
            start = param_border_positions[n]
            end = param_border_positions[n + 1]
            param_name = argv[start]
            param_values = argv[start + 1:end]
            if param_name.startswith(self.__full_separator):
                param_name = param_name[len(self.__full_separator):]
                separator = self.__full_separator
            elif param_name.startswith(self.__short_separator):
                param_name = param_name[len(self.__short_separator):]
                separator = self.__short_separator
            else:
                raise ValueError(f"Invalid parameter name '{param_name}'")
            yield separator, param_name, param_values
