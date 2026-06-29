# 限制与排错

tiny-stubgen 的核心原则是静态、安全、保守。它不会导入或执行目标代码，因此有些场景天然不适合由它完全解决。

## 适合场景

- 纯 Python 包或应用代码。
- 希望从未注解代码中生成初始 `.pyi`。
- 需要比基础 stubgen 更好的字面量和属性类型推断。
- 希望保留条件块和 `TYPE_CHECKING` 导入结构。
- CI 中快速检查示例 stub 是否同步。

## 非目标

- 不对 C 扩展、动态模块或运行时生成的属性做反射。
- 不做跨模块类型解析。
- 不执行装饰器、metaclass、descriptor 或 import side effect。
- 不保证生成的类型完全表达运行时所有行为。
- 不替代 mypy、pyright 等类型检查器。

## 推断边界

| 场景 | 当前策略 |
|------|----------|
| 简单字面量 | 推断为 `int`、`str`、`bool`、`float`、`bytes`、`complex`、`None` |
| 列表、集合、字典、元组 | 从元素类型推断，混合类型使用联合或 `Any` |
| 函数默认值 | 只做保守推断，避免把默认值误当成完整参数类型 |
| `self.x = value` | 优先使用参数注解，无法获得时从赋值值推断 |
| 动态赋值 | 无法静态确定时输出 `Any` 或跳过 |
| 条件定义 | 只保留常见平台和版本条件 |

## 常见问题

### 输出文件被跳过

默认不会覆盖已有 `.pyi`。使用：

```bash
tiny-stubgen src/ -o stubs/ --overwrite
```

### 私有函数没有出现在 stub 中

默认排除 `_private` 形式的名称。使用：

```bash
tiny-stubgen src/ --include-private --overwrite
```

### `__all__` 中缺少的名称触发 warning

如果源码包含：

```python
__all__ = ["public_name", "missing_name"]
```

而 `missing_name` 没有对应定义，tiny-stubgen 会打印 warning。修复方式是更新 `__all__` 或补齐定义。

### 生成结果里有 `Any`

这通常表示源码缺少足够静态信息。可以通过以下方式改善：

- 给函数参数或返回值添加注解。
- 给复杂变量添加显式注解。
- 避免把同一变量赋值为多个互不相关的形状。
- 对动态属性提供 `.pyi` 手工补丁。

### 条件导入没有按预期保留

当前只识别常见条件，例如 `sys.platform`、`sys.version_info`、`os.name`、`platform.*`。其他业务条件可能被普通 AST 流程处理，而不是作为条件 stub 输出。

### 生成的 stub 还需要人工调整吗

对大型库通常需要。推荐把 tiny-stubgen 作为初始生成器和回归检查工具，再用类型检查器验证输出质量。

## 选择 tiny-stubgen 还是 mypy stubgen

| 需求 | 推荐 |
|------|------|
| 纯 Python 静态源码、希望推断字面量和属性 | tiny-stubgen |
| C 扩展或运行时反射 | mypy stubgen |
| 需要跨模块类型解析 | mypy stubgen 或类型检查器 |
| 希望避免执行目标代码 | tiny-stubgen |
