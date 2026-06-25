# tiny-stubgen

[![CI](https://github.com/MrLYC/tiny-stubgen/actions/workflows/ci.yml/badge.svg)](https://github.com/MrLYC/tiny-stubgen/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

一个带有增强类型推断能力的 Python stub (.pyi) 文件生成器。

## 为什么需要 tiny-stubgen

Python 的类型提示生态越来越重要，但很多现有代码库缺少类型标注。标准库的 `stubgen` 对没有类型注解的代码生成的 stub 质量较差，大量使用 `Any`。

tiny-stubgen 通过**智能类型推断**，能从默认值、赋值语句、构造函数参数等信息中推断出更精确的类型，生成更有价值的 stub 文件。

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
