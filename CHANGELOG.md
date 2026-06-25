# Changelog

本项目遵循 [Semantic Versioning](https://semver.org/)。

## [0.1.1] - 2026-06-26

### Improved

- PyPI 页面展示完整 README 描述和项目链接
- 添加 `py.typed` marker（PEP 561）
- 添加 PyPI version badge
- `pip install tiny-stubgen` 作为首选安装方式
- 发布流程增加 tag 与版本号一致性校验

### Added

- CHANGELOG.md、CODE_OF_CONDUCT.md、SECURITY.md
- GitHub Issue / PR 模板

## [0.1.0] - 2026-06-25

### Added

- 核心 stub 生成管线：Extractor → Resolver → Emitter
- 智能类型推断：字面量、集合、元组、字典、构造函数调用
- 函数签名提取：位置参数、关键字参数、`*args`、`**kwargs`、默认值
- 类处理：继承、实例属性提取、`ClassVar`、`Final`、`__slots__`、嵌套类
- 装饰器识别：`@property`、`@classmethod`、`@staticmethod`、`@abstractmethod`、`@overload`
- 特殊类支持：`@dataclass`、`NamedTuple`、`TypedDict`、`Enum`
- TypeVar / ParamSpec / TypeVarTuple 赋值保留
- 条件块保留：`sys.platform`、`sys.version_info`
- 导入管理：自动去重、TYPE_CHECKING 处理、re-export `as` 别名
- 导出控制：`__all__` 过滤、私有名称排除
- 无返回值函数自动推断 `-> None`
- 同名重定义冲突处理
- CLI 工具：单文件 / 目录批量处理
- GitHub Actions CI（lint + test + examples 同步检查）
- PyPI 自动发布（tag 触发）

[0.1.1]: https://github.com/MrLYC/tiny-stubgen/releases/tag/v0.1.1
[0.1.0]: https://github.com/MrLYC/tiny-stubgen/releases/tag/v0.1.0
