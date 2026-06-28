# tiny-stubgen

Python stub (.pyi) 文件生成器，带有增强类型推断。

## 架构

处理流水线：`源码 → StubExtractor（AST 解析）→ postprocess（去重/过滤）→ StubEmitter（输出生成）→ .pyi 文件`

核心模块（均在 `src/tiny_stubgen/` 下）：

- `models.py` — 数据模型：ModuleStub、ClassInfo、FunctionInfo、ImportInfo 等
- `extractor.py` — AST 访问器，从源码提取 stub 信息
- `inferrer.py` — 类型推断引擎（字面量、默认值、集合等）
- `resolver.py` — 导入去重 + `__all__` 导出过滤
- `emitter.py` — 从 ModuleStub 生成 .pyi 内容
- `cli.py` — 命令行入口
- `utils.py` — 工具函数

## 常用命令

```bash
pip install -e ".[dev]"   # 安装开发依赖
make test                 # 运行测试
make lint                 # Lint 检查
make typecheck            # strict mypy 类型检查
make verify               # 完整稳定性检查
make format               # 格式化
make examples             # 重新生成示例 stub
make check-examples       # 检查示例是否同步
make docs-check           # 检查文档链接
```

## 代码约定

- Python >= 3.11，使用 `from __future__ import annotations`
- src-layout 布局
- 测试文件在 `tests/`，fixtures 在 `tests/fixtures/`
- fixtures 和 examples 中的 unused imports 是故意的，ruff 已排除 F401
- examples/*.pyi 是生成文件，排除在 ruff 格式化之外
- 修改生成逻辑后运行 `make examples` 更新示例 stub
