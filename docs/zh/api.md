# Python API

tiny-stubgen 可以作为库在内存中生成 `.pyi` 内容，不需要落盘。

## 稳定 API

### `generate_stub`

```python
from tiny_stubgen import GenerationPolicy, generate_stub

stub = generate_stub(
    "x = 1\n",
    module_name="example",
    include_private=False,
    policy=GenerationPolicy.default(),
)
```

签名：

```python
def generate_stub(
    source: str,
    *,
    module_name: str = "",
    include_private: bool | None = None,
    policy: GenerationPolicy | None = None,
) -> str: ...
```

参数：

| 参数 | 说明 |
|------|------|
| `source` | Python 源码字符串 |
| `module_name` | 模块名，主要用于错误信息和未来扩展 |
| `include_private` | 兼容参数；传入时覆盖 `policy.include_private` |
| `policy` | 生成策略，控制是否输出私有名称、导入、装饰器、类基类等 |

返回值是完整 `.pyi` 文本，并始终以换行结尾。

异常：

| 异常 | 场景 |
|------|------|
| `SyntaxError` | 输入源码不是合法 Python |

### `GenerationPolicy`

`GenerationPolicy` 是库调用方控制安全边界的主要入口：

```python
from tiny_stubgen import GenerationPolicy, generate_stub

policy = GenerationPolicy.strict().replace(
    include_private=False,
    include_docstrings=False,
    emit_class_bases=False,
)

stub = generate_stub(source, policy=policy)
```

预设：

| 预设 | 场景 |
|------|------|
| `GenerationPolicy.default()` | 兼容历史输出，也是 `GenerationPolicy.compat()` 的别名 |
| `GenerationPolicy.safe()` | 较低泄露面，减少不必要导入、装饰器和类关键字 |
| `GenerationPolicy.strict()` | 更低泄露面，适合处理不可信源码或公开自动化 |
| `GenerationPolicy.compat()` | 接近历史版本输出，适合迁移旧快照或工具链 |

常用开关：

| 字段 | 作用 |
|------|------|
| `include_private` | 是否输出 `_private` 名称 |
| `respect_all` | 是否尊重模块 `__all__` |
| `dunder_policy` | 控制自定义 dunder 名称暴露：`magic` / `all` / `none` |
| `include_docstrings` | 是否输出模块文档字符串 |
| `import_mode` | 导入输出模式：`typing-only` / `needed` / `all` |
| `emit_star_imports` | 是否输出 `from x import *` |
| `promote_type_checking_imports` | 是否提升 `TYPE_CHECKING` 内导入 |
| `decorator_mode` | 装饰器输出模式：`none` / `core` / `all-safe` |
| `emit_dataclass_decorators` | 是否输出 `@dataclass` |
| `annotation_mode` | 注解输出模式：`safe` / `any` / `none` |
| `type_alias_mode` | 类型别名输出模式：`safe` / `none` |
| `emit_typing_assignments` | 是否输出 `TypeVar` / `ParamSpec` 等赋值 |
| `emit_class_bases` | 是否输出类基类 |
| `emit_class_keywords` | 是否输出 `metaclass=...`、`total=False` 等类关键字 |
| `emit_conditionals` | 是否输出平台/版本条件块 |
| `include_private_class_constants` | 是否保留私有 `ClassVar` / `Final` 常量 |

### `generate_stubs_for_path`

批量路径 API 会读取文件并写入 `.pyi`，返回结构化结果而不是只打印日志：

```python
from tiny_stubgen import GenerationPolicy, IOPolicy, generate_stubs_for_path

result = generate_stubs_for_path(
    ["src"],
    output_dir="stubs",
    generation_policy=GenerationPolicy.default(),
    io_policy=IOPolicy.default().replace(existing="overwrite"),
)

assert result.ok
```

签名：

```python
def generate_stubs_for_path(
    paths: Iterable[str | Path],
    *,
    output_dir: str | Path | None = None,
    generation_policy: GenerationPolicy | None = None,
    io_policy: IOPolicy | None = None,
    diagnostic_policy: DiagnosticPolicy | None = None,
) -> BatchResult: ...
```

`IOPolicy` 控制文件系统边界，例如输入/遍历/输出 symlink 策略、已存在文件处理、是否允许原地输出、输出范围、输出碰撞策略、隐藏目录、最大文件大小、最大文件数、最大遍历深度和总字节数。默认批量 API 不允许原地输出，且输出范围限制在当前工作目录；如果确实要写到任意目录，需要显式设置 `output_scope="any"`。

`DiagnosticPolicy` 控制日志级别、文本/JSON 格式和诊断路径展示。

## 基础示例

```python
from tiny_stubgen import generate_stub

source = """
class Config:
    def __init__(self, host: str = "localhost"):
        self.host = host
        self.port = 8080
"""

print(generate_stub(source))
```

输出：

```python
class Config:

    host: str
    port: int

    def __init__(self, host: str = ...) -> None: ...
```

## 高级组件

以下组件可用于自定义流水线，但稳定性低于策略化公共 API：

```python
from tiny_stubgen import GenerationPolicy, StubEmitter, StubExtractor, postprocess

policy = GenerationPolicy.default().replace(include_private=True)
extractor = StubExtractor(source, module_name="example", policy=policy)
module = extractor.extract()
module = postprocess(module, policy=policy)
stub = StubEmitter(module, policy=policy).emit()
```

| 组件 | 作用 |
|------|------|
| `StubExtractor` | 将源码解析为 `ModuleStub` 数据模型 |
| `postprocess` | 合并导入，并按 `__all__` 或私有命名过滤导出 |
| `StubEmitter` | 将 `ModuleStub` 渲染为 `.pyi` 文本 |

核心数据模型详见 [架构设计](architecture.md)。

## API 稳定性

- `generate_stub`、`generate_stubs_for_path`、策略对象和 `__version__` 是稳定公共 API。
- `StubExtractor`、`StubEmitter`、`postprocess` 是高级 API，会尽量保持兼容，但内部模型可能随功能演进调整。
- `tiny_stubgen.models` 中的数据结构主要服务内部流水线，适合插件式实验，不建议作为长期外部契约。
