# 贡献指南

感谢你对 tiny-stubgen 的关注！以下是参与开发的指引。

## 开发环境搭建

```bash
# 克隆仓库
git clone https://github.com/MrLYC/tiny-stubgen.git
cd tiny-stubgen

# 安装开发依赖
pip install -e ".[dev]"

# 验证环境
make verify

# 可选：安装本地 Git hooks
pre-commit install --hook-type pre-commit --hook-type pre-push
```

## 代码规范

项目使用 [ruff](https://docs.astral.sh/ruff/) 进行代码检查和格式化。

```bash
# 检查
make lint

# 格式化
make format

# 完整格式检查
make format-check
```

CI 会自动运行 lint、格式、类型、测试、示例同步、文档链接和包构建检查，请确保提交前通过 `make verify`。修改生成逻辑后，还应运行 `make check-examples` 确认 `examples/*.pyi` 已同步。

## 类型检查

项目使用 strict mypy 检查公共源码：

```bash
make typecheck
```

## 测试

使用 pytest 运行测试：

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_extractor.py

# 显示详细输出
pytest -v
```

覆盖率阈值由 `pyproject.toml` 维护，当前完整测试命令是：

```bash
make test
```

### 测试结构

- `tests/test_extractor.py` — AST 提取相关测试
- `tests/test_emitter.py` — 输出生成相关测试
- `tests/test_inferrer.py` — 类型推断相关测试
- `tests/fixtures/` — 测试用的 Python 模块样本

### 添加测试 fixture

`tests/fixtures/` 目录下的 `.py` 文件是测试用的示例模块。这些文件中的 unused imports 是故意保留的（用于测试 stub 生成的导入提取能力），ruff 已配置忽略此目录的 `F401` 规则。

## 提交规范

- 提交信息简洁明了，说明改动的目的
- 一个 PR 聚焦解决一个问题或添加一个功能
- 确保 `make verify` 通过
- 用户可见行为变化需要同步更新 `README.md` 或 `docs/`

## PR 流程

1. Fork 仓库并创建分支
2. 编写代码和测试
3. 确认 `make verify` 通过
4. 提交 PR，描述改动内容和动机

## 项目架构

详见 [架构文档](docs/zh/architecture.md)。

## 稳定性体系

完整说明见 [稳定性体系](docs/zh/stability.md)。

## 文档体系

文档入口见 [文档中心](docs/README.md)。新增或修改文档后运行：

```bash
make docs-check
```
