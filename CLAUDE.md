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
pytest                    # 运行测试
ruff check src/ tests/    # Lint 检查
ruff format src/ tests/   # 格式化
```

## 代码约定

- Python >= 3.11，使用 `from __future__ import annotations`
- src-layout 布局
- 测试文件在 `tests/`，fixtures 在 `tests/fixtures/`
- fixtures 中的 unused imports 是故意的，ruff 已排除 F401
