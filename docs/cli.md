# CLI 参考

命令入口：

```bash
tiny-stubgen PATH [PATH ...]
```

`PATH` 可以是一个或多个 Python 文件或目录。

## 参数

| 参数 | 说明 |
|------|------|
| `PATH` | 要处理的 Python 文件或目录，支持传入多个路径 |
| `-o, --output-dir OUTPUT_DIR` | 输出目录；未指定时输出到源文件旁边 |
| `--overwrite` | 覆盖已存在的 `.pyi` 文件 |
| `--include-private` | 包含 `_private` 形式的私有名称 |
| `-v, --verbose` | 输出每个生成文件 |
| `-q, --quiet` | 仅输出错误 |
| `--version` | 显示版本号 |
| `-h, --help` | 显示帮助 |

## 示例

生成单个文件：

```bash
tiny-stubgen example.py
```

覆盖已有 stub：

```bash
tiny-stubgen example.py --overwrite
```

生成整个源码目录：

```bash
tiny-stubgen src/ -o stubs/ --overwrite
```

生成多个输入：

```bash
tiny-stubgen src/package_a src/package_b/tools.py -o stubs/ --overwrite
```

包含私有接口：

```bash
tiny-stubgen src/ -o stubs/ --include-private --overwrite
```

CI 中静默运行：

```bash
tiny-stubgen src/ -o stubs/ --overwrite --quiet
```

## 输出路径规则

未指定 `--output-dir` 时，输出文件与源文件同目录：

```text
package/module.py -> package/module.pyi
```

指定 `--output-dir` 时，目录输入会保持相对路径：

```text
tiny-stubgen src/ -o stubs/
src/pkg/mod.py -> stubs/pkg/mod.pyi
```

指定 `--output-dir` 处理单个文件时，输出文件放在该目录下：

```text
tiny-stubgen src/pkg/mod.py -o stubs/
src/pkg/mod.py -> stubs/mod.pyi
```

## 退出码

| 退出码 | 含义 |
|--------|------|
| `0` | 所有处理成功，或没有可处理的 Python 文件 |
| `1` | 至少一个 Python 文件读取、解析或生成失败 |

已存在且未使用 `--overwrite` 的文件会被跳过，不计为错误。

## 错误处理

CLI 会对以下情况给出错误并继续处理其他文件：

- 文件不可读或不是 UTF-8。
- Python 语法错误。
- 源码嵌套过深导致 `RecursionError`。
- 文件超过内部大小限制。

更多排错建议见 [限制与排错](limitations.md)。
