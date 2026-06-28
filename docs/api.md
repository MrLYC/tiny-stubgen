# Python API

tiny-stubgen 可以作为库在内存中生成 `.pyi` 内容，不需要落盘。

## 稳定 API

### `generate_stub`

```python
from tiny_stubgen import generate_stub

stub = generate_stub(
    "x = 1\n",
    module_name="example",
    include_private=False,
)
```

签名：

```python
def generate_stub(
    source: str,
    *,
    module_name: str = "",
    include_private: bool = False,
) -> str: ...
```

参数：

| 参数 | 说明 |
|------|------|
| `source` | Python 源码字符串 |
| `module_name` | 模块名，主要用于错误信息和未来扩展 |
| `include_private` | 是否输出 `_private` 形式的私有名称 |

返回值是完整 `.pyi` 文本，并始终以换行结尾。

异常：

| 异常 | 场景 |
|------|------|
| `SyntaxError` | 输入源码不是合法 Python |

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

以下组件可用于自定义流水线，但稳定性低于 `generate_stub`：

```python
from tiny_stubgen import StubEmitter, StubExtractor, postprocess

extractor = StubExtractor(source, module_name="example")
module = extractor.extract()
module = postprocess(module, include_private=True)
stub = StubEmitter(module, include_private=True).emit()
```

| 组件 | 作用 |
|------|------|
| `StubExtractor` | 将源码解析为 `ModuleStub` 数据模型 |
| `postprocess` | 合并导入，并按 `__all__` 或私有命名过滤导出 |
| `StubEmitter` | 将 `ModuleStub` 渲染为 `.pyi` 文本 |

核心数据模型详见 [架构设计](architecture.md)。

## API 稳定性

- `generate_stub` 和 `__version__` 是稳定公共 API。
- `StubExtractor`、`StubEmitter`、`postprocess` 是高级 API，会尽量保持兼容，但内部模型可能随功能演进调整。
- `tiny_stubgen.models` 中的数据结构主要服务内部流水线，适合插件式实验，不建议作为长期外部契约。
