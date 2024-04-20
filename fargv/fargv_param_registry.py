import sys
from .fargv_param_value import ParamDefinition, create_from_definition_data

class FargvNameException(Exception):
    pass


class FargvDuplicateNameException(Exception):
    pass


class Name:
    """
    Class for parameter names."""
    def __init__(self, name_variants):
        print(f"3NameConstr({repr(name_variants)})")
        if isinstance(name_variants, Name):
            self.__name_variants = tuple([n for n in name_variants.__name_variants])
        else:
            if isinstance(name_variants, str):
                name_variants = tuple([name_variants])
            try:
                assert isinstance(name_variants, tuple)
                assert len(name_variants) > 0
                assert all(isinstance(name, str) for name in name_variants)
                assert all(name.isidentifier() for name in name_variants)
                assert all(len(name) for name in name_variants)
                assert all([all(ord(c) < 128 for c in name) for name in name_variants])
                assert len(set(name_variants)) == len(name_variants)
            except AssertionError:
                print(f"NV {repr(name_variants)}, {type(name_variants)}")
                exc_type, exc_obj, exc_tb = sys.exc_info()
                raise FargvNameException(f"Invalid name variants'{name_variants}'")
            self.__name_variants = tuple([name_variants[0]]) + tuple(sorted(name_variants[1:]))

    def get_main_name(self):
        return self.__name_variants[0]

    def get_short_names(self):
        return tuple([name for name in self.__name_variants if len(name) == 1 and name.isalpha()])

    def get_name_variants(self):
        return self.__name_variants

    def append_name_variant(self, name_variant):
        assert isinstance(name_variant, str)
        assert name_variant.isidentifier()
        assert len(name_variant) == 1 and name_variant.isalpha() or len(name_variant) > 1
        self.__name_variants += (name_variant,)

    def __str__(self):
        return f"{self.__name_variants[0]}"

    def __repr__(self):
        return f"{self.get_name_variants()}"
    
    def __hash__(self) -> int:
        return hash(self.__name_variants)

    def get_caption(self):
        words = self.__name_variants[0].split("_")
        return " ".join([word.capitalize() for word in words])

    def get_cli_help_string(self, separator="-"):
        names = [f"{separator}{n}" for n in self.get_name_variants() if len(n) == 1]
        names = names + [f"{separator}{separator}{n}" for n in self.get_name_variants() if len(n) > 1]
        return f"{','.join(names)}"

    def __eq__(self, other):
        if isinstance(other, Name):
            return self.get_name_variants() == other.get_name_variants()
        else:
            return False


class Registry:
    """Registry for parameter names and definitions.

    This class handles the registration of parameter names and their definitions.
    Their definitions are not interpreted yet, but only stored in the registry.
    The name_references are handled here as well.
    
    """
    def __init__(self, data=None) -> None:
        self.__names_definitions = []  # Renamed from __names_definitions_objects
        self.__all_names = {}
        self.__main_names = {}
        self.__short_names = {}
        if data is None:
            pass
        elif isinstance(data, dict):
            self.define_from_dict(data)
        else:
            raise ValueError(f"Registry(data) Invalid data type '{type(data)}'")
    
    def insert(self, name, param):
        name = Name(name)
        if any(n in self.__all_names for n in name.get_name_variants()):
            raise FargvDuplicateNameException
        print(f"4Insert({name}, {param})")
        param = create_from_definition_data(param)
        param.register_param(self)
        self.__names_definitions.append((name, param))  # Renamed from __names_definitions_objects
        self.__update_idx()
    
    def get_all_names(self):
        return self.__all_names.keys()

    def get_main_names(self):
        return self.__main_names.keys()

    def get_short_names(self):
        return self.__short_names.keys()

    def export_as_dict(self):
        """Export the registry definition as a dictionary."""
        return dict(iter(self.__names_definitions))

    def get_param(self, name_str):
        return self.__names_definitions[self.__all_names[name_str]][1]

    def __getitem__(self, key):
        return self.__names_definitions[self.__all_names[key]][1].get_value()

    def __setitem__(self, key, value):
        self.__names_definitions[self.__main_names[key]][1].update_value(value)
    
    def __len__(self):
        return len(self.__names_definitions)
    
    def __delitem__(self, key):
        raise NotImplementedError()
    
    def __iter__(self):
        """Iterate over the main_names and value."""
        name_values = [(n.get_main_name(), p.get_value()) for n, p in self.__names_definitions]
        return iter(name_values)

    def get_name_of_param(self, obj):
        for name, obj_ in self.__names_definitions:
            if obj_ is obj:
                return name
        return None

    def __update_idx(self):
        #raise NotImplementedError() # Ideally we will do without this method
        self.__all_names = {}
        self.__main_names = {}
        self.__short_names = {}
        for n, (name, _) in enumerate(self.__names_definitions):
            assert name.get_main_name() not in self.__main_names
            self.__main_names[name.get_main_name()] = n
            for variant in name.get_name_variants():
                assert variant not in self.__all_names
                self.__all_names[variant] = n
            for short_name in name.get_short_names():
                assert short_name not in self.__short_names
                self.__short_names[short_name] = n

    def clear(self):
        self.__names_definitions = []  # Renamed from __names_definitions_objects
        self.__all_names = {}
        self.__main_names = {}
        self.__short_names = {}

    def add_guessed_short_names(self):
        for n, (name, _, _) in enumerate(self.__names_definitions):
            if len(name.get_short_names()) == 0:
                short_name = name.get_main_name()[0]
                if short_name not in self.__short_names:
                    name.append_name_variant(short_name)
                    self.__short_names[short_name] = n
                    self.__all_names[short_name] = n

    def values_allowed(self, name2value):
        for name, value in name2value.items():
            if not self.__names_definitions[self.__all_names[name]][2].value_allowed(value):
                return False
        return True

    def update_values(self, name2value):
        if self.values_allowed(name2value):
            for name, value in name2value.items():
                self.__names_definitions[self.__all_names[name]][2].update_value(value)
        else:
            raise ValueError("Invalid value")

    def copy(self):
        res = Registry()
        for name, param in self.__names_definitions:
            res.insert(name.get_name_variants(), param.copy().register_param(self))
        return res

    def define_from_dict(self, args_dict):
        print("args_dict", args_dict)
        for name, definition_data in args_dict.items():
            if isinstance(definition_data, dict):
                raise NotImplementedError  # This is in order to do sub modules
                definition_data = create_from_definition_data(definition_data)
            elif isinstance(definition_data, tuple):
                definition_data = create_from_definition_data(definition_data)
            elif isinstance(definition_data, ParamDefinition):
                raise ValueError("Invalid definition data type")
            else:
                definition_data = create_from_definition_data(definition_data)
            if isinstance(name, str) or isinstance(name, tuple) or isinstance(name, list):
                name = Name(name)
            elif isinstance(name, Name):
                pass
            else:
                raise ValueError("Invalid name type")
            print("2DefineFromDict ", name, definition_data)
            self.insert(name, definition_data)


# ALERT: The following code seems to be obsolete
#__registry = Registry()
