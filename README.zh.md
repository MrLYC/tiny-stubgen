# tiny-stubgen

[![PyPI version](https://img.shields.io/pypi/v/tiny-stubgen)](https://pypi.org/project/tiny-stubgen/)
[![CI](https://github.com/MrLYC/tiny-stubgen/actions/workflows/ci.yml/badge.svg)](https://github.com/MrLYC/tiny-stubgen/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

一个零依赖、带增强类型推断能力的 Python `.pyi` stub 文件生成器。

English documentation: [README.md](README.md).

## 快速开始

```bash
pip install tiny-stubgen

# 生成单个文件的 stub
tiny-stubgen example.py

# 生成整个目录的 stub
tiny-stubgen src/ -o stubs/ --overwrite
```

## Python API

```python
from tiny_stubgen import GenerationPolicy, generate_stub

source = open("example.py", encoding="utf-8").read()
stub = generate_stub(source, policy=GenerationPolicy.default())
print(stub)
```

`GenerationPolicy.default()` 保持历史兼容输出；公开生成或处理不可信源码时，可以显式使用 `GenerationPolicy.safe()` 或 `GenerationPolicy.strict()` 降低泄露面。

批量路径 API：

```python
from tiny_stubgen import IOPolicy, generate_stubs_for_path

result = generate_stubs_for_path(
    ["src"],
    output_dir="stubs",
    io_policy=IOPolicy.default().replace(
        existing="overwrite",
        output_scope="any",
    ),
)
assert result.ok
```

## 为什么需要 tiny-stubgen

tiny-stubgen 专注纯静态 AST 分析，不导入也不执行目标模块。相比基础 `stubgen`，它能从字面量、赋值语句、函数默认值和构造函数里的实例属性中推断出更有用的类型。

| 特性 | tiny-stubgen | mypy stubgen |
|------|:---:|:---:|
| 字面量和集合类型推断 | 是 | 否（`Incomplete`） |
| `__init__` 实例属性推断 | 是 | 否（`Incomplete`） |
| 条件块保留 | 是 | 否 |
| overload 实现签名保留 | 是 | 否 |
| TypeVar / ParamSpec 保留 | 是 | 是 |
| Enum 成员处理 | 是 | 是 |
| re-export `as` 别名 | 是 | 是 |
| C 扩展运行时反射 | 否 | 是 |
| 跨模块类型解析 | 否 | 是 |
| 零依赖 | 是 | 否 |

tiny-stubgen 适合纯 Python 项目的快速初始 stub 生成；如果需要运行时反射、C 扩展或类型检查器辅助的跨模块解析，`mypy stubgen` 更合适。

## 功能

- 静态 AST 分析，不执行目标代码。
- 从字面量、集合、构造调用、默认值和 `self.x = ...` 赋值中推断类型。
- 处理 `property`、setter/deleter、classmethod、staticmethod、abstractmethod、overload、dataclass 等装饰器。
- 支持 dataclass、`NamedTuple`、`TypedDict`、Enum、嵌套类、`__slots__`、`TYPE_CHECKING`、`__all__` 和常见平台/版本条件块。
- 通过策略对象控制私有名称、导入、注解、装饰器、类元数据、文件系统边界、symlink、输出碰撞和诊断输出。

## 文档

文档已经拆成英文和中文两套：

| 语言 | 入口 |
|------|------|
| English | [docs/en/README.md](docs/en/README.md) |
| 中文 | [docs/zh/README.md](docs/zh/README.md) |

常用中文文档：

| 文档 | 内容 |
|------|------|
| [使用指南](docs/zh/usage.md) | 安装、常见生成流程和输出策略 |
| [CLI 参考](docs/zh/cli.md) | 命令参数、输出路径和退出码 |
| [Python API](docs/zh/api.md) | `generate_stub`、批量 API 和策略对象 |
| [示例索引](docs/zh/examples.md) | 示例源码和生成结果 |
| [限制与排错](docs/zh/limitations.md) | 适用边界和常见问题 |
| [架构设计](docs/zh/architecture.md) | 内部流水线和数据模型 |
| [稳定性体系](docs/zh/stability.md) | 本地检查、CI 和发布门禁 |

## 开发

```bash
pip install -e ".[dev]"

make lint
make format
make typecheck
make test
make docs-check
make verify
```

参见 [CONTRIBUTING.md](CONTRIBUTING.md) 了解贡献流程。

## 许可证

[MIT License](LICENSE)
