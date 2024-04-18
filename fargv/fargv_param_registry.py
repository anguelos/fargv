from typing import Any
from .util import FargvNameException


class FargvNameException(Exception):
    pass

class FargvDuplicateNameException(Exception):
    pass


class FargvName:
    """
    Class for parameter names."""
    def __init__(self, name_variants):
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
    
    def get_caption(self):
        words = self.__name_variants[0].split("_")
        return " ".join([word.capitalize() for word in words])
    
    def get_cli_help_string(self):
        names = [f"-{n}" for n in self.get_name_variants() if len(n) == 1]
        names = names + [f"--{n}" for n in self.get_name_variants() if len(n) > 1]
        return f"{','.join(names)}"
    
    def __eq__(self, other):
        if isinstance(other, FargvName):
            return self.get_name_variants() == other.get_name_variants()
        else:
            return False


class FargvRegistry:
    """Registry for parameter names and definitions.

    This class handles the registration of parameter names and their definitions.
    Their definitions are not interpreted yet, but only stored in the registry.
    The name_references are handled here as well.
    
    """
    def __init__(self) -> None:
        self.__names_definitions_objects = []
        self.__all_names = {}
        self.__main_names = {}
        self.__short_names = {}
    
    def get_all_names(self):
        return self.__all_names.keys()
    def get_main_names(self):
        return self.__main_names.keys()
    def get_short_names(self):
        return self.__short_names.keys()
    

    def insert(self, name_variants, param_definition, param_object):
        try:
            name = FargvName(name_variants)
        except Exception:
            raise FargvNameException(f"Invalid name variants'{name_variants}'")
        if not all(name_variant not in self.__all_names for name_variant in name.get_name_variants()):
            raise FargvDuplicateNameException(f"Duplicate name variants '{name_variants}'")        
        self.__main_names[name.get_main_name()] = len(self.__names_definitions_objects)
        self.__all_names[name.get_main_name()] = len(self.__names_definitions_objects)
        for short_name in name.get_short_names():
            self.__short_names[short_name] = len(self.__names_definitions_objects)
        self.__names_definitions_objects.append((name, param_definition, param_object))

    def export_as_dict(self):
        return {name: self.main_names[name] for name in self.main_names}
    
    def __getitem__(self, key):
        return self.__names_definitions_objects[self.__all_names[key]][2].get_value()

    def get_param(self, name_str):
        return self.__names_definitions_objects[self.__all_names[name_str]][2]
    
    def __setitem__(self, key, value):
        self.__names_definitions_objects[self.__main_names[key]][2].update_value(value)

    def get_fargvname_of_param(self, obj):
        for name, _, obj_ in self.__names_definitions_objects:
            if obj_ is obj:
                return name
        return None

    def __update_idx(self):
        #raise NotImplementedError() # Ideally we will do without this method
        self.__all_names = {}
        self.__main_names = {}
        self.__short_names = {}
        for n, (name, _, _) in enumerate(self.__names_definitions_objects):
            assert name.get_main_name() not in self.__main_names
            self.__main_names[name.get_main_name()] = n
            for variant in name.get_name_variants():
                assert variant not in self.__all_names
                self.__all_names[variant] = n
            for short_name in name.get_short_names():
                assert short_name not in self.__short_names
                self.__short_names[short_name] = n

    def clear(self):
        self.__names_definitions_objects = []
        self.__all_names = {}
        self.__main_names = {}
        self.__short_names = {}

    def add_guessed_short_names(self):
        for n, (name, _, _) in enumerate(self.__names_definitions_objects):
            if len(name.get_short_names()) == 0:
                short_name = name.get_main_name()[0]
                if short_name not in self.__short_names:
                    name.append_name_variant(short_name)
                    self.__short_names[short_name] = n
                    self.__all_names[short_name] = n


__registry = FargvRegistry()
