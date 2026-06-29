PYTHON ?= python
PYTEST ?= pytest
RUFF ?= ruff

.PHONY: help lint format format-check typecheck test test-fast examples check-examples docs-check clean clean-build package-check verify ci

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

lint: ## 运行 lint 检查
	$(RUFF) check src/ tests/ examples/

format: ## 格式化代码
	$(RUFF) format src/ tests/ examples/

format-check: ## 检查代码格式
	$(RUFF) format --check src/ tests/ examples/

typecheck: ## 运行静态类型检查
	$(PYTHON) -m mypy

test: ## 运行测试
	$(PYTEST) --cov=tiny_stubgen --cov-report=term-missing

test-fast: ## 不统计覆盖率，快速运行测试
	$(PYTEST)

examples: ## 重新生成 examples 目录下的 .pyi 文件
	tiny-stubgen examples/ -o examples/ --overwrite --import-mode all --decorator-mode all-safe --emit-typing-assignments --emit-class-keywords

check-examples: examples ## 检查 .pyi 文件是否与源码同步
	@if git diff --quiet -- 'examples/*.pyi'; then \
		echo "examples are up to date"; \
	else \
		echo "ERROR: examples are out of date, run 'make examples' to regenerate"; \
		git diff -- 'examples/*.pyi'; \
		exit 1; \
	fi

docs-check: ## 检查 Markdown 本地链接
	$(PYTHON) scripts/check_docs.py

clean: ## 清理生成的文件
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name '*.pyc' -delete
	rm -rf .coverage coverage.xml htmlcov/ .pytest_cache/ .ruff_cache/ .mypy_cache/ .hypothesis/

clean-build: ## 清理构建产物
	rm -rf build/ dist/ *.egg-info src/*.egg-info

package-check: clean-build ## 构建包并校验元数据
	$(PYTHON) -m build
	$(PYTHON) -m twine check dist/*

verify: lint format-check typecheck test check-examples docs-check package-check ## 本地完整稳定性检查

ci: verify ## CI 使用的完整稳定性检查入口
