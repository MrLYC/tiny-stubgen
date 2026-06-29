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
| `--existing {skip,fail,overwrite}` | 已存在输出文件的处理方式 |
| `--input-symlinks {reject,skip,follow}` | 显式输入路径含 symlink 时的处理方式 |
| `--traversal-symlinks {reject,skip,follow}` | 目录遍历过程中遇到 symlink 时的处理方式 |
| `--output-symlinks {reject,allow}` | 输出路径为 symlink 时的处理方式 |
| `--output-scope {cwd,source-root,any}` | 限制输出路径所在范围 |
| `--collision-policy {fail,skip,overwrite}` | 多输入映射到同一输出路径时的处理方式 |
| `--no-recursive` | 目录输入只处理当前层 |
| `--include-hidden` | 遍历隐藏文件和隐藏目录 |
| `--include-private` | 包含 `_private` 形式的私有名称 |
| `--ignore-all` | 忽略 `__all__`，改用普通 public/private 过滤 |
| `--import-mode {typing-only,needed,all}` | 控制普通导入输出范围 |
| `--decorator-mode {none,core,all-safe}` | 控制装饰器输出范围 |
| `--type-alias-mode {none,safe}` | 控制类型别名输出 |
| `--emit-typing-assignments` | 输出安全的 `TypeVar` / `ParamSpec` 等赋值 |
| `--emit-class-keywords` | 输出安全的类关键字，例如 `metaclass=...` |
| `--no-class-bases` | 不输出类基类 |
| `--no-conditionals` | 不输出平台/版本条件块 |
| `--max-file-size N` | 单个源码文件最大字节数 |
| `--max-files N` | 目录处理时最多处理的 Python 文件数 |
| `--max-depth N` | 目录遍历最大深度 |
| `--log-format {text,json}` | 诊断输出格式 |
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

更低泄露面的公开生成：

```bash
tiny-stubgen src/ -o stubs/ --import-mode typing-only --no-class-bases --no-conditionals
```

迁移旧输出快照时保留更多历史行为：

```bash
tiny-stubgen src/ -o stubs/ --import-mode all --emit-typing-assignments --emit-class-keywords
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
- 文件超过 `--max-file-size` 限制。
- 目录处理超过 `--max-files` 或 `--max-depth` 限制。

更多排错建议见 [限制与排错](limitations.md)。
