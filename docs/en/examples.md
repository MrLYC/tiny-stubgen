# Examples

Every `.py` file in `examples/` has a matching `.pyi` output that demonstrates tiny-stubgen behavior. After changing generation logic, run:

```bash
make examples
make check-examples
```

## Example List

| Example | Input | Output | Demonstrates |
|---------|-------|--------|--------------|
| Basic types | [01_basic_types.py](../../examples/01_basic_types.py) | [01_basic_types.pyi](../../examples/01_basic_types.pyi) | literals, collections, dictionaries, tuples, constructor calls, f-strings, complex numbers |
| Function signatures | [02_functions.py](../../examples/02_functions.py) | [02_functions.pyi](../../examples/02_functions.pyi) | defaults, async, positional-only args, keyword-only args, varargs |
| Classes | [03_classes.py](../../examples/03_classes.py) | [03_classes.pyi](../../examples/03_classes.pyi) | inheritance, instance attributes, class variables, nested classes, `__slots__` |
| Decorators | [04_decorators.py](../../examples/04_decorators.py) | [04_decorators.pyi](../../examples/04_decorators.pyi) | `@property`, setters, abstract methods, static/class methods, overloads |
| Dataclasses | [05_dataclasses.py](../../examples/05_dataclasses.py) | [05_dataclasses.pyi](../../examples/05_dataclasses.pyi) | dataclasses, `NamedTuple`, `TypedDict` |
| Imports and exports | [06_imports_and_exports.py](../../examples/06_imports_and_exports.py) | [06_imports_and_exports.pyi](../../examples/06_imports_and_exports.pyi) | imports, `TYPE_CHECKING`, `__all__` |
| Conditionals | [07_conditionals.py](../../examples/07_conditionals.py) | [07_conditionals.pyi](../../examples/07_conditionals.pyi) | `sys.platform`, `sys.version_info`, `os.name` branches |
| Generics | [08_generics.py](../../examples/08_generics.py) | [08_generics.pyi](../../examples/08_generics.pyi) | TypeVar, ParamSpec, Generic, Protocol, Callable |
| Enums | [09_enums.py](../../examples/09_enums.py) | [09_enums.pyi](../../examples/09_enums.pyi) | Enum, IntEnum, `auto()`, enum methods |

## How to Read Examples

1. Read the `.py` source and note explicit annotations versus inferred locations.
2. Read the `.pyi` output and compare inferred types.
3. Check [Limitations](limitations.md) to distinguish intended behavior from gaps.

## Adding an Example

Keep example numbering sequential:

```text
examples/10_new_feature.py
examples/10_new_feature.pyi
```

Then run:

```bash
make examples
make check-examples
```

