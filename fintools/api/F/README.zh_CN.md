Languages: [English](README.md) | 中文

# FinTools · 函数调用 API（fintools.api.F）

本目录提供 **FinTools 的函数调用版 API**。

该 API 面向 **直接在 Python 中使用金融数据与分析工具的用户**。

所有函数均位于：

```python
fintools.api.F
```

---

## 关于函数文档

函数的行为、参数、返回值，以函数定义本身为准。

* 每个函数的 **参数类型、默认值、语义** 均已在函数签名与 docstring 中明确说明
* 本 README 不会重复描述每个函数的参数或返回结构
* 推荐直接使用 IDE / 编辑器查看函数定义（hover / jump to definition）

---

## 数据类型与枚举

部分函数会使用内置的数据类型或枚举（如市场类型、频率等）。

示例：

```python
from fintools.api.F.types import UnderlyingTypes, DataFrequency
```

具体可用取值请以源码定义为准。

---

## 错误与异常

* 参数校验失败、数据缺失、网络错误等情况会以 Python 异常形式抛出
* 不进行 silent fallback
* 上层应用应自行捕获并处理异常

---
