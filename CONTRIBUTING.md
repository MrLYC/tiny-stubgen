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
pytest
ruff check src/ tests/
```

## 代码规范

项目使用 [ruff](https://docs.astral.sh/ruff/) 进行代码检查和格式化。

```bash
# 检查
ruff check src/ tests/

# 格式化
ruff format src/ tests/
```

CI 会自动运行 lint 检查，请确保提交前通过。

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
- 确保所有测试通过，lint 无报错

## PR 流程

1. Fork 仓库并创建分支
2. 编写代码和测试
3. 确认 `pytest` 和 `ruff check` 通过
4. 提交 PR，描述改动内容和动机

## 项目架构

详见 [架构文档](docs/architecture.md)。
