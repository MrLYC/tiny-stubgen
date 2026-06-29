# 示例索引

`examples/` 目录中的每个 `.py` 文件都有对应 `.pyi` 输出，用于展示 tiny-stubgen 的生成能力。修改生成逻辑后应运行：

```bash
make examples
make check-examples
```

## 示例列表

| 示例 | 输入 | 输出 | 演示内容 |
|------|------|------|----------|
| 基础类型 | [01_basic_types.py](../../examples/01_basic_types.py) | [01_basic_types.pyi](../../examples/01_basic_types.pyi) | 字面量、集合、字典、元组、构造调用、f-string、复数 |
| 函数签名 | [02_functions.py](../../examples/02_functions.py) | [02_functions.pyi](../../examples/02_functions.pyi) | 默认值、async、位置参数、关键字参数、可变参数 |
| 类定义 | [03_classes.py](../../examples/03_classes.py) | [03_classes.pyi](../../examples/03_classes.pyi) | 继承、实例属性、类变量、嵌套类、`__slots__` |
| 装饰器 | [04_decorators.py](../../examples/04_decorators.py) | [04_decorators.pyi](../../examples/04_decorators.pyi) | `@property`、setter、abstractmethod、staticmethod、classmethod、overload |
| 数据类 | [05_dataclasses.py](../../examples/05_dataclasses.py) | [05_dataclasses.pyi](../../examples/05_dataclasses.pyi) | dataclass、NamedTuple、TypedDict |
| 导入与导出 | [06_imports_and_exports.py](../../examples/06_imports_and_exports.py) | [06_imports_and_exports.pyi](../../examples/06_imports_and_exports.pyi) | import 处理、`TYPE_CHECKING`、`__all__` |
| 条件块 | [07_conditionals.py](../../examples/07_conditionals.py) | [07_conditionals.pyi](../../examples/07_conditionals.pyi) | `sys.platform`、`sys.version_info`、`os.name` 条件分支 |
| 泛型 | [08_generics.py](../../examples/08_generics.py) | [08_generics.pyi](../../examples/08_generics.pyi) | TypeVar、ParamSpec、Generic、Protocol、Callable |
| 枚举 | [09_enums.py](../../examples/09_enums.py) | [09_enums.pyi](../../examples/09_enums.pyi) | Enum、IntEnum、auto、自定义枚举方法 |

## 如何阅读示例

1. 先看 `.py` 文件，确认源码里哪些位置有显式注解，哪些没有。
2. 再看 `.pyi` 文件，观察 tiny-stubgen 如何推断未注解内容。
3. 对照 [限制与排错](limitations.md)，判断输出是设计行为还是需要改进的缺口。

## 添加新示例

新增示例时保持命名连续：

```text
examples/10_new_feature.py
examples/10_new_feature.pyi
```

添加步骤：

1. 编写 `.py` 输入文件，覆盖一个明确主题。
2. 运行 `make examples` 生成 `.pyi`。
3. 检查输出是否能清楚展示预期行为。
4. 更新本页表格。
5. 运行 `make check-examples` 和 `make docs-check`。
