# 架构设计

## 总体架构

tiny-stubgen 采用管道式架构，将 Python 源码转换为 .pyi stub 文件：

```
Python 源码
    │
    ▼
┌──────────────┐
│  Extractor   │  AST 解析，提取结构化信息
│ (extractor.py)│
└──────┬───────┘
       │ ModuleStub
       ▼
┌──────────────┐
│  Resolver    │  导入去重，导出过滤
│ (resolver.py) │
└──────┬───────┘
       │ ModuleStub (处理后)
       ▼
┌──────────────┐
│   Emitter    │  生成 .pyi 文件内容
│ (emitter.py)  │
└──────┬───────┘
       │ str
       ▼
   .pyi 文件
```

## 核心数据模型

所有模块之间通过 `models.py` 中定义的数据结构通信。`ModuleStub` 是核心容器：

```
ModuleStub
├── imports: list[ImportInfo]           # 导入语句
├── variables: list[VariableInfo]       # 模块级变量
├── functions: list[FunctionInfo]       # 顶层函数
├── classes: list[ClassInfo]            # 类定义
├── conditional_blocks: list[ConditionalBlock]  # 条件块
├── all_names: list[str] | None        # __all__ 内容
└── docstring: str | None              # 模块文档字符串
```

### 关键模型

| 模型 | 用途 |
|------|------|
| `ImportInfo` | 表示一条 import 语句，含模块路径、名称列表、别名、层级（相对导入）、TYPE_CHECKING 标记 |
| `FunctionInfo` | 函数签名：参数列表、返回类型、装饰器、async 标记、overload 支持 |
| `ParameterInfo` | 函数参数：名称、注解、默认值、参数类型（位置/关键字/可变等） |
| `ClassInfo` | 类定义：基类、方法、属性、装饰器、内部类 |
| `AttributeInfo` | 类/实例属性：注解、ClassVar/Final 标记 |
| `VariableInfo` | 模块级变量：注解、TypeAlias 检测 |
| `ConditionalBlock` | 条件块（如 `if sys.platform == "win32"`）：含条件内的导入和定义 |

### 装饰器分类

`DecoratorKind` 枚举将装饰器分为以下类别：

- `PROPERTY` / `SETTER` / `DELETER` — property 相关
- `CLASSMETHOD` / `STATICMETHOD` — 方法类型
- `ABSTRACTMETHOD` — 抽象方法
- `OVERLOAD` — 函数重载
- `DATACLASS` — dataclass 装饰器
- `OTHER` — 其他装饰器（原样保留）

## 模块详解

### Extractor（提取器）

`StubExtractor` 是一个 `ast.NodeVisitor` 子类，遍历 AST 提取 stub 信息。

**核心职责：**

- **导入提取** — 普通导入、from 导入、星号导入、相对导入、TYPE_CHECKING 守卫内的导入
- **函数提取** — 完整的参数签名（位置参数、关键字参数、`*args`、`**kwargs`、默认值）
- **类提取** — 继承关系、方法、属性、装饰器、内部类
- **实例属性提取** — 从 `__init__` 方法中提取 `self.x = ...` 形式的赋值
- **特殊类处理** — `@dataclass`、`NamedTuple`、`TypedDict` 的专门处理
- **`__slots__` 解析** — 从 `__slots__` 声明中提取属性名
- **条件块处理** — 识别 `sys.version_info`、`sys.platform`、`os.name` 条件判断
- **`__all__` 提取** — 包括动态的 `.extend()` / `.append()` 调用
- **Overload 合并** — 将多个 `@overload` 签名和实现合并

### Inferrer（类型推断器）

提供三个核心函数：

**`infer_type_from_value(node)`** — 从 AST 表达式推断类型：

- 字面量：`42` → `int`，`"hello"` → `str`，`True` → `bool`
- 集合：`[1, 2]` → `list[int]`，`{"a": 1}` → `dict[str, int]`
- 构造函数调用：`dict()` → `dict[str, Any]`
- 联合类型：`X | Y` → `X | Y`
- f-string → `str`

**`infer_type_from_default(node)`** — 从函数默认值推断（更保守，避免误报）

**`classify_decorator(node)`** — 识别装饰器类型，返回 `(DecoratorKind, raw_text)`

### Resolver（解析器）

两步后处理：

1. **`deduplicate_imports()`** — 合并来自同一模块的多条导入语句
2. **`resolve_exports()`** — 根据 `__all__` 过滤，或排除私有名称

### Emitter（生成器）

`StubEmitter` 将 `ModuleStub` 转换为 `.pyi` 文本：

- **导入分组** — `__future__` → 标准导入 → typing 导入
- **自动补充 typing 导入** — 扫描所有注解，自动添加需要的 `typing` 名称（如 `Any`、`Optional` 等）
- **函数输出** — 参数格式化，默认值统一替换为 `...`，处理位置参数分隔符 `/` 和关键字参数分隔符 `*`
- **类输出** — 属性声明 + 方法签名，空类体用 `...` 表示
- **overload 输出** — `@overload` 签名在实现签名之前输出

## 类型推断策略

tiny-stubgen 的推断遵循**宁可保守也不误报**原则：

1. 对模块级变量的赋值值进行完整推断（`infer_type_from_value`）
2. 对函数默认值仅做保守推断（`infer_type_from_default`），避免类型注解与实际行为矛盾
3. 实例属性先看参数注解，再看赋值值推断
4. 无法推断时使用 `Any`

## 扩展点

如需扩展 tiny-stubgen 的能力，以下是关键入口：

- **支持新的类型推断模式** — 在 `inferrer.py` 的 `infer_type_from_value()` 中添加新的 AST 节点处理分支
- **支持新的装饰器** — 在 `inferrer.py` 的 `classify_decorator()` 和 `models.py` 的 `DecoratorKind` 中扩展
- **自定义输出格式** — 修改 `emitter.py` 中的 `_emit_*` 方法
- **支持新的特殊类** — 在 `extractor.py` 的 `_extract_class()` 中添加识别逻辑
