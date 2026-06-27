.PHONY: help lint format test examples check-examples clean

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

lint: ## 运行 lint 检查
	ruff check src/ tests/ examples/

format: ## 格式化代码
	ruff format src/ tests/ examples/

test: ## 运行测试
	pytest --cov=tiny_stubgen --cov-report=term-missing

examples: ## 重新生成 examples 目录下的 .pyi 文件
	tiny-stubgen examples/ -o examples/ --overwrite

check-examples: examples ## 检查 .pyi 文件是否与源码同步
	@if git diff --quiet -- 'examples/*.pyi'; then \
		echo "examples are up to date"; \
	else \
		echo "ERROR: examples are out of date, run 'make examples' to regenerate"; \
		git diff -- 'examples/*.pyi'; \
		exit 1; \
	fi

clean: ## 清理生成的文件
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name '*.pyc' -delete
