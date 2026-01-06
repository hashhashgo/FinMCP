Languages: [English](README.md) | 中文

***本模块不再通过扫描源码目录自动发现服务，所有 MCP 服务必须通过 entry_points 显式注册。***

---

# 介绍

一个基于 **FastMCP** 的动态、自动发现式 MCP 服务管理器。

该模块负责统一管理和运行所有注册到 `entry-points` 的 `FastMCP` 实例，例如：

```toml
[project.entry-points."fintools.mcp_services"]
tool_fin_history = "fintools.api.mcp.tool_fin_history:mcp"
```

并提供：

* MCP 服务的自动加载与注册
* 多进程 + HTTP 的 MCP Server 启动与管理
* 已存在远程 MCP 服务的连接能力
* MCP 服务连接的统一维护
* 周期性的服务健康检查（Ping）

---

# 功能特性

| 功能项               | 描述                                                            |
| ----------------- | ------------------------------------------------------------- |
| **插件式发现**         | 通过 `project.entry-points."fintools.mcp_services"` 加载所有 MCP 服务 |
| **统一注册管理**        | 所有服务统一存入 `MCP_SERVICES: Dict[str, FastMCP]`                   |
| **连接集中管理**        | 所有服务连接统一维护在 `MCP_CONNECTIONS: Dict[str, Connection]`          |
| **多进程 Server 管理** | `start_all_services()` 为每个 MCP 服务启动独立 HTTP Server             |
| **外部服务支持**        | 支持仅连接已存在的 MCP 服务，而不创建新进程                                      |
| **环境变量控制**        | 通过 `.env` 控制“启动 / 仅连接”行为                                      |
| **一键启动器**         | `python -m fintools.api.mcp` 启动全部已注册服务（推荐）                    |
| **健康检测**          | 周期性 ping 检测所有 MCP 服务存活状态                                      |

---

# 使用方法

## MCP 服务注册

所有 MCP 服务 必须 通过 entry_points 注册。

**示例：定义 MCP 服务**

```python
from fastmcp import FastMCP

mcp = FastMCP("my_custom_service")

@mcp.tool
def echo(text: str) -> str:
    return text
```

**在项目中注册 entry_points**
```toml
[project.entry-points."fintools.mcp_services"]
my_service = "my_pkg.my_service:mcp"
```

安装该项目后，该 MCP 服务将被自动加载并纳入统一管理。

* 无需修改 fintools 源码
* 支持多项目、多团队独立扩展
* 不再支持隐式扫描源码目录

---

## 导入模块

```python
from fintools.api.mcp import (
    MCP_SERVICES,
    MCP_CONNECTIONS,
    MCP_PROCESSES,
    start_all_services,
    close_all_services,
)
```

---

## 在应用中内部启动服务

在 `.env` 中配置：

```bash
START_SERVICES=True
```

然后在程序中启动：

```python
start_all_services()
```

或无论如何强制启动：

```python
start_all_services(start_anyway=True)
```

---

## 外部启动服务（推荐）

```bash
uv run -m fintools.api.mcp
```

这将执行包内的 `__main__`，并将：

* 加载所有通过 entry_points 注册的 MCP 服务
* 为每个 MCP 服务启动独立 HTTP Server（端口自动递增）
* 周期性 ping 检查服务状态

然后在 `.env` 中配置：

```bash
START_SERVICES=false
MY_SERVICE_PORT=8000
ANOTHER_SERVICE_PORT=8001
......
```

在程序中使用：

```python
start_all_services(create_new=False)
```

---

## 使用 FastMCP CLI 启动单个服务（可选）

```bash
fastmcp run my_service.py --transport http --port [port]
```

---

## 关闭所有服务

**如果服务是内部启动的：**

```python
close_all_services()
```

**如果服务是外部启动：**

使用 `Ctrl + C` 或向进程发送 `SIGINT` / `SIGTERM`，模块会自动关闭所有服务。

---

## 环境变量说明

| 变量                            | 行为              |
| ----------------------------- | --------------- |
| `START_SERVICES=True`         | 在当前应用中启动 MCP 服务 |
| `START_SERVICES=False`        | 不启动本地服务，仅连接远程服务 |
| `[PACKAGE_NAME]_SERVICE_PORT` | 指定外部服务的端口       |

---

# 与 LangChain 的集成示例

当服务已启动或连接成功后，获取工具非常简单：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from fintools.api.mcp import MCP_CONNECTIONS

client = MultiServerMCPClient(MCP_CONNECTIONS)

tools = await client.get_tools()
```

随后即可将 `tools` 注入 LangChain / LangGraph / Agent 系统使用。

---

# 调试 MCP 服务

启动 MCP inspector：
```bash
npx @modelcontextprotocol/inspector
```

使用以下设置连接：

| 设置            | 值                          |
| --------------- | --------------------------- |
| Transport Type  | Streamable HTTP             |
| URL             | http://127.0.0.1:[port]/mcp |
| Connection Type | Via Proxy                   |

然后在`Tools`页面就可以看见服务的所有工具了。

---

# License

MIT

---
