# 发布流程

本项目通过 GitHub Actions 和 PyPI Trusted Publishing 发布。发布 workflow 见 [publish.yml](../../.github/workflows/publish.yml)。

## 发布前检查

1. 确认版本号已更新：

   ```bash
   python -c "from tiny_stubgen import __version__; print(__version__)"
   ```

2. 更新 [CHANGELOG.md](../../CHANGELOG.md)。

3. 运行完整本地检查：

   ```bash
   make verify
   ```

4. 如文档有新增链接，确认：

   ```bash
   make docs-check
   ```

## 构建检查

本地验证包构建和元数据：

```bash
make package-check
```

该命令会：

- 清理旧的 `build/`、`dist/` 和 egg-info。
- 构建 sdist 和 wheel。
- 用 `twine check` 校验包元数据。

## 创建 tag

tag 必须以 `v` 开头，并与 `tiny_stubgen.__version__` 一致：

```bash
git tag v1.0.1
git push origin v1.0.1
```

如果版本不一致，发布 workflow 会失败。

## 发布后检查

发布完成后：

```bash
pip install --upgrade tiny-stubgen
tiny-stubgen --version
```

再用一个简单输入做冒烟测试：

```bash
python - <<'PY'
from tiny_stubgen import generate_stub

assert "x: int" in generate_stub("x = 1\n")
PY
```

## 回滚

PyPI 版本不能覆盖。如果错误版本已经发布：

1. 在 [CHANGELOG.md](../../CHANGELOG.md) 记录问题。
2. 修复代码或元数据。
3. 发布新的补丁版本。
4. 如有安全影响，按 [SECURITY.md](../../SECURITY.md) 处理。
