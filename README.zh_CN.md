Languages: [English](README.md) | 中文

# 简介

**FinTools** 是一个金融数据与分析工具包（toolkit），用于统一封装和管理各类可复用的金融工具与数据接口。

它提供一组可直接调用的函数级工具，也可选地通过 MCP（Model Context Protocol）暴露给 LLM / Agent 系统使用。

FinTools 的目标是作为一个轻量、可组合、可复用的金融工具集合。

---

## 提供的工具类型

FinTools 当前包含（并持续扩展）以下类型的工具：

* 获取股票 / 指数 / 期货 / 外汇等历史行情数据
* 获取新闻、公告及其他文本类金融信息
* 网页搜索与外部信息检索
* 用户自定义的金融数据或分析逻辑
* 可选：适用于 LLM 的 MCP 接口封装

---

## MCP 支持说明（可选）

FinTools 可以作为 MCP 服务的管理与启动工具，但 MCP 只是其中一种适配方式：

* 可以完全不使用 MCP，直接在 Python 中调用工具函数
* 也可以通过 MCP，将这些工具暴露给 LLM、LangChain 或多 Agent 系统

FinTools 内置了一些金融相关的 MCP 服务，同时支持用户通过 `entry_points` 插件式扩展额外的 MCP 服务。

---

# 特性

## 工具包定位

* 所有功能均以工具（tool）为核心
* 可独立使用、可组合、可复用
* 不强制依赖任何 Agent、框架或运行时

## 插件式 MCP 扩展（entry_points）

* 支持在外部项目中注册 FastMCP 实例
* 无需修改 FinTools 源码
* 内建服务与外部服务可统一管理（在启用 MCP 时）

## MCP 服务管理能力（可选）

* 自动端口分配
* 服务连接信息统一记录
* 服务存活检测（Ping）

## LangChain / MultiServerMCPClient 集成

* 通过 `MCP_CONNECTIONS` 获取全部 MCP 服务连接
* 无需手动配置 URL

---

# 安装

FinTools 使用 uv 管理依赖，可直接从 GitHub 安装：

```bash
uv add https://github.com/hashhashgo/FinTools.git
```

安装后即可在任意 uv 项目中使用 FinTools。

---

# （可选）启动 MCP 服务

如果不使用 MCP / LLM，可跳过本节。

## 方式 1：命令行启动（推荐）

```bash
uv run -m fintools
```

该命令会：

1. 启动所有通过 `entry_points` 注册的 MCP 服务
2. 自动分配端口并写入连接记录文件
3. 输出：

```bash
All MCP services are up and running.
```

4. 后台每 10 秒 Ping 所有服务，并输出状态日志：

```bash
INFO: 127.0.0.1:39275 - "POST /mcp HTTP/1.1" 200 OK
Pinged service service_name successfully.
```

---

## 方式 2：在主程序中动态启动

设置环境变量：

```toml
START_SERVICES_INTERNAL=true
```

在代码中调用：

```python
start_all_services()
```

程序结束前调用：

```python
close_all_services()
```

---

## MCP 相关环境变量

```toml
START_SERVICES_INTERNAL=false
CONNECTION_RECORD_FILE="agent_tools_service_ports.json"
FINTOOLS_HOST="0.0.0.0"
```

| 变量名                  | 类型    | 说明                        |
| ----------------------- | ------- | --------------------------- |
| START_SERVICES_INTERNAL | boolean | 是否在程序内部启动 MCP 服务 |
| CONNECTION_RECORD_FILE  | str     | MCP 连接信息记录文件路径    |
| FINTOOLS_HOST           | str     | MCP 服务绑定地址            |

不需要手动指定端口，FinTools 会自动检测并分配可用端口。

---

# 在主程序中使用（以 MCP 为例）

```python
from fintools import MCP_CONNECTIONS, start_all_services, close_all_services
from langchain_mcp_adapters.client import MultiServerMCPClient

async def main():

    start_all_services()

    client = MultiServerMCPClient(connections=MCP_CONNECTIONS)
    tools = await client.get_tools()

    result = await client.call_tool(
        "fin_history.history",
        {
            "symbol": "AAPL",
            "start": "2020-01-01",
            "freq": "daily",
        }
    )

    print(result)

    close_all_services()
```

---

# 注册新的 MCP 服务（插件方式）

## 1. 定义 FastMCP 实例

```python
from fastmcp import FastMCP

mcp = FastMCP("MyService")

@mcp.tool
def echo(text: str):
    return text
```

## 2. 在项目中注册 entry_points

```toml
[project.entry-points."fintools.services"]
myservice = "my_pkg.my_service:mcp"
```

## 3. 安装项目

```bash
uv pip install --editable .
uv build
```

完成后，FinTools 会自动加载并管理该 MCP 服务。

---

# 数据库与缓存支持

FinTools 支持将下载的数据缓存至本地数据库。

设置环境变量：

```bash
DB_PATH=history.db
```

示例创建 SQLite 数据库：

```bash
touch history.db
```

---

# 使用说明速览

| 功能                  | 操作                                                  |
| --------------------- | ----------------------------------------------------- |
| 安装 FinTools         | `uv add https://github.com/hashhashgo/FinTools.git` |
| 启动 MCP 服务（可选） | `uv run -m fintools`                                |
| 程序中启动服务        | `start_all_services()`                              |
| 获取 MCP 连接信息     | `MCP_CONNECTIONS`                                   |
| 关闭 MCP 服务         | `close_all_services()`                              |
| 注册外部 MCP 工具     | `entry_points`                                      |

---

# License

MIT

---
