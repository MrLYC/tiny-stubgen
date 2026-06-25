# tiny-stubgen

[![CI](https://github.com/MrLYC/tiny-stubgen/actions/workflows/ci.yml/badge.svg)](https://github.com/MrLYC/tiny-stubgen/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

一个带有增强类型推断能力的 Python stub (.pyi) 文件生成器。

## 为什么需要 tiny-stubgen

Python 的类型提示生态越来越重要，但很多现有代码库缺少类型标注。标准库的 `stubgen` 对没有类型注解的代码生成的 stub 质量较差，大量使用 `Any`。

tiny-stubgen 通过**智能类型推断**，能从默认值、赋值语句、构造函数参数等信息中推断出更精确的类型，生成更有价值的 stub 文件。

## 与 mypy stubgen 对比

tiny-stubgen 专注纯静态 AST 分析 + 增强类型推断，零外部依赖；mypy stubgen 依托 mypy 类型检查生态，支持运行时反射和跨模块解析。

以下是同一段源码经两个工具生成的 stub 对比（基于实际运行结果）：

### 类型推断

```python
# 源码
class Config:
    def __init__(self, host: str = "localhost"):
        self.host = host
        self.port = 8080
        self.debug = False
```

| tiny-stubgen | mypy stubgen |
|:--|:--|
| `host: str` | `host: Incomplete` |
| `port: int` | `port: Incomplete` |
| `debug: bool` | `debug: Incomplete` |

### 集合推断

```python
# 源码
TAGS = {"python", "typing"}
ERROR_CODES = {404: "Not Found", 500: "Server Error"}
```

| tiny-stubgen | mypy stubgen |
|:--|:--|
| `TAGS: set[str]` | `TAGS: Incomplete` |
| `ERROR_CODES: dict[int, str]` | `ERROR_CODES: Incomplete` |

### 条件块保留

```python
# 源码
if sys.platform == "win32":
    def get_size() -> tuple[int, int]: ...
else:
    def get_size() -> tuple[int, int]: ...
```

| tiny-stubgen | mypy stubgen |
|:--|:--|
| 保留 `if/else` 分支结构 | 展平为当前运行环境的单个定义 |

### 特性矩阵

| 特性 | tiny-stubgen | mypy stubgen |
|------|:---:|:---:|
| 字面量 / 集合类型推断 | :white_check_mark: | :x: (`Incomplete`) |
| `__init__` 实例属性推断 | :white_check_mark: | :x: (`Incomplete`) |
| 条件块保留 (`sys.platform` 等) | :white_check_mark: | :x: (展平) |
| overload 实现签名保留 | :white_check_mark: | :x: |
| TypeVar / ParamSpec 保留 | :white_check_mark: | :white_check_mark: |
| Enum 成员处理 | :white_check_mark: | :white_check_mark: |
| re-export `as` 别名 | :white_check_mark: | :white_check_mark: |
| 运行时反射 (C 扩展) | :x: | :white_check_mark: |
| 跨模块类型解析 | :x: | :white_check_mark: |
| 零依赖 | :white_check_mark: | :x: (需要 mypy) |

**总结**：tiny-stubgen 适合纯 Python 项目的快速高质量 stub 生成，在类型推断精度和条件块保留上有明显优势；mypy stubgen 在需要运行时反射（C 扩展模块）或跨模块类型解析时更合适。两者定位互补。

## 特性

- **智能类型推断** — 从字面量、默认值、集合构造等推断类型
- **装饰器识别** — 正确处理 `@property`、`@classmethod`、`@staticmethod`、`@abstractmethod`、`@overload` 等
- **Dataclass 支持** — 识别 `@dataclass`、`NamedTuple`、`TypedDict`
- **实例属性提取** — 从 `__init__` 方法中提取实例属性并推断类型
- **条件块保留** — 保留 `sys.platform`、`sys.version_info` 等条件判断结构
- **导入管理** — 自动去重、合并 typing 导入、处理 `TYPE_CHECKING` 守卫
- **导出控制** — 尊重 `__all__`，可选包含私有名称
- **嵌套类支持** — 正确处理嵌套的类定义

## 安装

### 从源码安装

```bash
git clone https://github.com/MrLYC/tiny-stubgen.git
cd tiny-stubgen
pip install -e .
```

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

## 快速开始

### 处理单个文件

```bash
tiny-stubgen example.py
```

这会在同目录下生成 `example.pyi`。

### 处理整个目录

```bash
tiny-stubgen src/ -o stubs/ --overwrite
```

### 示例

输入 `example.py`：

```python
import os

class Config:
    DEFAULT_PORT = 8080

    def __init__(self, host: str = "localhost"):
        self.host = host
        self.port = 8080
        self.debug = False

def greet(name, greeting="Hello"):
    return f"{greeting}, {name}!"
```

生成 `example.pyi`：

```python
import os

class Config:
    DEFAULT_PORT: int
    host: str
    port: int
    debug: bool
    def __init__(self, host: str = ...) -> None: ...

def greet(name: Any, greeting: str = ...) -> str: ...
```

## CLI 参数

| 参数 | 说明 |
|------|------|
| `PATH` | 要处理的 Python 文件或目录（支持多个） |
| `-o, --output-dir` | 输出目录（默认：与源文件同目录） |
| `--overwrite` | 覆盖已存在的 .pyi 文件 |
| `--include-private` | 包含以 `_` 开头的私有名称 |
| `-v, --verbose` | 详细输出 |
| `-q, --quiet` | 静默模式，仅显示错误 |
| `--version` | 显示版本号 |

## 转换效果展示

[`examples/`](examples/) 目录包含 9 个精心设计的示例，每个 `.py` 文件都有对应的 `.pyi` 文件，直观展示转换效果：

| 示例 | 演示内容 |
|------|----------|
| [`01_basic_types`](examples/01_basic_types.py) | 字面量、集合、元组、字典的类型推断 |
| [`02_functions`](examples/02_functions.py) | 函数签名、默认值、async、位置/关键字参数 |
| [`03_classes`](examples/03_classes.py) | 继承、实例属性提取、嵌套类、`__slots__` |
| [`04_decorators`](examples/04_decorators.py) | property、abstractmethod、overload 等装饰器 |
| [`05_dataclasses`](examples/05_dataclasses.py) | dataclass、NamedTuple、TypedDict |
| [`06_imports_and_exports`](examples/06_imports_and_exports.py) | 导入处理、`__all__` 导出控制、TYPE_CHECKING |
| [`07_conditionals`](examples/07_conditionals.py) | sys.platform / sys.version_info 条件块 |
| [`08_generics`](examples/08_generics.py) | TypeVar、ParamSpec、Generic、Protocol |
| [`09_enums`](examples/09_enums.py) | Enum、IntEnum、auto() 枚举类型 |

可随时重新生成所有示例的 stub 文件：

```bash
make examples
```

## 架构概览

tiny-stubgen 的主流程是 `cli.process_file()` 串起 `StubExtractor`、`postprocess()` 和 `StubEmitter`：先解析 Python 源码为 `ModuleStub`，再做导入去重与导出过滤，最后渲染为 `.pyi` 文本。

![tiny-stubgen architecture](docs/architecture-imagegen.png)

更详细的模块职责见 [架构设计](docs/architecture.md)。

## 项目结构

```
tiny-stubgen/
├── src/tiny_stubgen/
│   ├── cli.py          # 命令行接口
│   ├── extractor.py    # AST 解析，提取 stub 信息
│   ├── inferrer.py     # 类型推断引擎
│   ├── emitter.py      # .pyi 文件内容生成
│   ├── resolver.py     # 导入去重与导出过滤
│   ├── models.py       # 核心数据模型
│   └── utils.py        # 工具函数
├── examples/           # 转换效果展示（.py + .pyi）
├── tests/              # 测试套件
├── docs/               # 架构文档
├── Makefile            # 常用开发命令
├── pyproject.toml
└── .github/workflows/  # CI 配置
```

## 开发

常用命令（通过 Makefile）：

```bash
make help            # 查看所有可用命令
make lint            # 运行 lint 检查
make format          # 格式化代码
make test            # 运行测试
make examples        # 重新生成示例 stub
make check-examples  # 检查示例是否同步
```

参见 [贡献指南](CONTRIBUTING.md) 了解如何参与开发。

## 许可证

[MIT License](LICENSE)
