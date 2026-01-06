Languages: [English](README.md) | 中文

***从当前版本起，所有外部调用都应使用 `fintools.api`***。

# FinTools

**FinTools** 是一个金融数据与分析工具包（toolkit），用于统一封装和管理各类可复用的金融工具与数据接口。

FinTools 提供多种数据：

- 历史价格
- 历史新闻
- 历史研报

FinTools 是成为一个 **轻量、可组合、可复用的金融工具集合**。

---

## 统一 API 入口说明

根据使用方式不同，FinTools 提供不同形态的API：

- [函数调用 API](./fintools/api/F/README.zh_CN.md)：`fintools.api.F`
- [MCP API](./fintools/api/mcp/README.zh_CN.md)：`fintools.api.mcp`

两种 API **功能来源一致，仅调用方式不同**。

---

## 提供的工具类型

FinTools 当前包含（并持续扩展）以下类型的工具：

- 获取股票 / 指数 / 期货 / 外汇 / 加密资产等历史行情数据
- 获取新闻、公告及其他文本类金融信息
- [todo] 网页搜索与外部信息检索
- 用户自定义的金融数据或分析逻辑

---

## 安装

FinTools 使用 **uv** 管理依赖，可直接从 GitHub 安装：

```bash
uv add https://github.com/hashhashgo/FinTools.git
```

安装后即可在任意 uv 项目中使用：

```python
import fintools
```

---

## 数据库与缓存支持

FinTools 支持将下载的数据缓存至本地数据库（如 SQLite）。

设置环境变量：

```bash
FINTOOLS_DB=history.db
```

示例创建 SQLite 数据库：

```bash
touch history.db
```

具体缓存策略与表结构说明见对应工具文档。

---

# License

MIT

---
