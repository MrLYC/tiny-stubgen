# 文档中心

这里是 tiny-stubgen 的项目文档入口。README 负责快速介绍，专题文档负责可维护的使用、开发和发布细节。

English documentation: [../en/README.md](../en/README.md).

## 用户文档

| 文档 | 内容 |
|------|------|
| [使用指南](usage.md) | 安装、常见生成流程、输出策略和推荐实践 |
| [CLI 参考](cli.md) | 命令行参数、退出码和批量使用示例 |
| [Python API](api.md) | `generate_stub`、核心组件和稳定性约定 |
| [示例索引](examples.md) | `examples/` 中每个输入/输出样例的说明 |
| [限制与排错](limitations.md) | 适用边界、非目标和常见问题处理 |

## 维护者文档

| 文档 | 内容 |
|------|------|
| [架构设计](architecture.md) | AST 提取、后处理、输出生成和数据模型 |
| [稳定性体系](stability.md) | 本地检查、CI、发布检查和依赖维护 |
| [发布流程](release.md) | 版本、changelog、tag 和 PyPI 发布步骤 |
| [贡献指南](../../CONTRIBUTING.md) | 开发环境、测试、PR 流程 |
| [安全策略](../../SECURITY.md) | 漏洞报告方式和支持版本 |

## 文档维护规则

- README 只保留快速入口和核心卖点，详细内容放在 `docs/`。
- 新增或修改功能时，同步更新对应的用户文档和示例。
- 修改生成逻辑时，运行 `make examples` 和 `make docs-check`。
- 新增文档链接后，运行 `make docs-check` 验证本地 Markdown 链接。
