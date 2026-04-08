# API Reference

## Parameter class hierarchy

```{eval-rst}
.. inheritance-diagram::
   fargv.parameters.FargvInt
   fargv.parameters.FargvFloat
   fargv.parameters.FargvBool
   fargv.parameters.FargvStr
   fargv.parameters.FargvChoice
   fargv.parameters.FargvPositional
   fargv.parameters.FargvTuple
   fargv.parameters.FargvStream
   fargv.parameters.FargvInputStream
   fargv.parameters.FargvOutputStream
   fargv.parameters.FargvPath
   fargv.parameters.FargvExistingFile
   fargv.parameters.FargvNonExistingFile
   fargv.parameters.FargvFile
   fargv.parameters.FargvSubcommand
   :top-classes: fargv.parameters.FargvParameter
   :parts: 1
```

---

## Main entry points

```{eval-rst}
.. autofunction:: fargv.parse
```

```{eval-rst}
.. autofunction:: fargv.parse_and_launch
```

```{eval-rst}
.. autofunction:: fargv.parse_here
```

---

## Parameter classes

All parameter classes are exported directly from the `fargv` package.

```{eval-rst}
.. autoclass:: fargv.FargvInt
   :members:
```

```{eval-rst}
.. autoclass:: fargv.FargvFloat
   :members:
```

```{eval-rst}
.. autoclass:: fargv.FargvBool
   :members:
```

```{eval-rst}
.. autoclass:: fargv.FargvStr
   :members:
```

```{eval-rst}
.. autoclass:: fargv.FargvChoice
   :members:
```

```{eval-rst}
.. autoclass:: fargv.FargvPositional
   :members:
```

```{eval-rst}
.. autoclass:: fargv.FargvTuple
   :members:
```

```{eval-rst}
.. autoclass:: fargv.FargvStream
   :members:
```

```{eval-rst}
.. autoclass:: fargv.FargvInputStream
   :members:
```

```{eval-rst}
.. autoclass:: fargv.FargvOutputStream
   :members:
```

```{eval-rst}
.. autoclass:: fargv.FargvPath
   :members:
```

```{eval-rst}
.. autoclass:: fargv.FargvExistingFile
   :members:
```

```{eval-rst}
.. autoclass:: fargv.FargvNonExistingFile
   :members:
```

```{eval-rst}
.. autoclass:: fargv.FargvFile
   :members:
```

```{eval-rst}
.. autoclass:: fargv.FargvSubcommand
   :members:
```

---

## Sentinel

```{eval-rst}
.. autodata:: fargv.REQUIRED
```

---

## Low-level parser

```{eval-rst}
.. autoclass:: fargv.parser.ArgumentParser
   :members: _add_parameter, infer_short_names, parse, generate_help_message
```

---

## Type detection utilities

```{eval-rst}
.. autofunction:: fargv.type_detection.definition_to_parser
```

```{eval-rst}
.. autofunction:: fargv.type_detection.dict_to_parser
```

```{eval-rst}
.. autofunction:: fargv.type_detection.function_to_parser
```

```{eval-rst}
.. autofunction:: fargv.type_detection.dataclass_to_parser
```
