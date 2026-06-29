# 稳定性体系

tiny-stubgen 的稳定性门禁分为本地检查、CI 检查、发布检查和依赖维护四层。目标是让每次改动都能回答四个问题：

- 代码是否符合项目风格。
- 公共源码是否通过严格类型检查。
- 行为是否被测试覆盖，且示例 stub 是否与生成逻辑同步。
- 发布包是否能正确构建、校验并安装使用。

## 本地检查

先安装开发依赖：

```bash
pip install -e ".[dev]"
```

常用命令：

| 命令 | 作用 |
|------|------|
| `make lint` | 运行 Ruff lint |
| `make format-check` | 检查 Ruff 格式 |
| `make typecheck` | 对 `src/tiny_stubgen` 运行 strict mypy |
| `make test` | 运行 pytest、分支覆盖率和覆盖率阈值 |
| `make check-examples` | 重新生成 `examples/*.pyi` 并检查是否有差异 |
| `make docs-check` | 检查 Markdown 本地链接 |
| `make package-check` | 构建 sdist/wheel 并用 twine 校验元数据 |
| `make verify` | 运行完整本地稳定性门禁 |

建议安装 Git hooks：

```bash
pre-commit install --hook-type pre-commit --hook-type pre-push
```

当前 hook 策略：

- pre-commit：`make lint`、`make format-check`、`make typecheck`、`make docs-check`
- pre-push：`make test`、`make check-examples`、`make package-check`

## CI 门禁

`.github/workflows/ci.yml` 在 push 和 pull request 上运行：

- `quality`：Ruff lint、Ruff format check、strict mypy、文档链接检查。
- `test`：Python 3.11、3.12、3.13 矩阵测试，并执行覆盖率阈值。
- `check-examples`：验证生成的 `examples/*.pyi` 与源码同步。
- `package`：构建包、校验元数据，并安装 wheel 做 CLI/API 冒烟测试。

覆盖率阈值在 `pyproject.toml` 的 `[tool.coverage.report]` 中维护，当前阈值为 90%。

## 发布门禁

`.github/workflows/publish.yml` 只在 `v*` tag 上发布。发布前会执行：

- 与 CI 一致的质量检查。
- Python 3.11、3.12、3.13 测试矩阵。
- tag 版本与 `tiny_stubgen.__version__` 的一致性校验。
- sdist/wheel 构建和 twine 元数据校验。

发布前人工检查清单：

- `CHANGELOG.md` 已记录用户可见变化。
- `README.md` 和 `docs/` 已同步更新。
- 本地 `make verify` 通过。
- tag 形如 `v0.1.0`，且不重复已有发布版本。

## 依赖维护

`.github/dependabot.yml` 每周检查 GitHub Actions 和 Python 依赖更新。依赖更新 PR 仍需要通过完整 CI 后再合并。
