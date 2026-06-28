# 使用指南

tiny-stubgen 从 Python 源码生成 `.pyi` stub 文件。它只做静态 AST 分析，不导入目标模块，因此适合纯 Python 项目、生成速度快，也避免执行用户代码。

## 安装

```bash
pip install tiny-stubgen
```

从源码开发：

```bash
git clone https://github.com/MrLYC/tiny-stubgen.git
cd tiny-stubgen
pip install -e ".[dev]"
```

## 单文件生成

```bash
tiny-stubgen path/to/module.py
```

默认会在源文件旁边生成 `path/to/module.pyi`。如果目标 `.pyi` 已存在，命令会跳过该文件，避免覆盖手工维护的 stub。

需要覆盖时使用：

```bash
tiny-stubgen path/to/module.py --overwrite
```

## 目录生成

```bash
tiny-stubgen src/ -o stubs/ --overwrite
```

目录模式会递归处理 `.py` 文件，并保持相对路径：

```text
src/package/core.py  ->  stubs/package/core.pyi
src/package/api.py   ->  stubs/package/api.pyi
```

## 私有名称

默认输出遵循 Python stub 的常见习惯：

- 保留公开名称。
- 保留双下划线魔术方法，例如 `__init__`、`__repr__`。
- 排除 `_private` 形式的私有变量、函数、类和类成员。
- 如果模块定义了 `__all__`，只输出 `__all__` 中列出的名称。

如果需要完整内部接口：

```bash
tiny-stubgen src/ -o stubs/ --include-private --overwrite
```

## 推荐工作流

对应用项目：

```bash
tiny-stubgen src/ -o stubs/ --overwrite
python -m mypy src/
```

对库项目：

```bash
tiny-stubgen src/ -o src/ --overwrite
git diff -- '*.pyi'
```

对本仓库示例：

```bash
make examples
make check-examples
```

## 输出策略

tiny-stubgen 会尽量保留源码结构，同时让生成的 `.pyi` 更适合类型检查器使用：

- 默认值输出为 `...`，例如 `timeout: float = ...`。
- 未注解变量会从字面量、集合和简单构造调用中推断类型。
- `TYPE_CHECKING` 守卫内的导入会提升为 stub 中可见的普通导入。
- `typing` 相关导入会自动合并，并补齐推断注解需要的名称。
- `sys.platform`、`sys.version_info`、`os.name` 等条件块会保留为条件结构。

## 下一步

- 命令行参数见 [CLI 参考](cli.md)。
- 作为库调用见 [Python API](api.md)。
- 生成效果见 [示例索引](examples.md)。
- 已知边界见 [限制与排错](limitations.md)。
