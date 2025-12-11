Languages: [English](README.md) | 中文

***直接使用此库的用法已经弃用了。请直接import finmcp或者python -m finmcp。并采用在entry_points中注册的方法。具体用法请转到[README](../../README.zh_CN.md)***

# 介绍

一个基于 **FastMCP** 的动态、自动发现式 MCP 服务管理器。
它会自动加载 `finmcp.agent_tools` 包中定义的所有 `FastMCP` 服务实例，并提供：

* 自动启动 MCP Server（多进程 + HTTP）
* 连接到已存在的远程 MCP 服务
* 统一管理所有服务与连接
* 定时健康检查（周期性 ping）

# 功能特性

| 功能项                | 描述                                                                                   |
| ------------------ | ------------------------------------------------------------------------------------ |
| **自动发现**           | 扫描 `agent_tools/` 下所有 `.py` 文件，自动加载其中暴露的 `FastMCP` 实例。                              |
| **统一注册管理**         | 所有发现的服务存入 `MCP_SERVICES: Dict[str, FastMCP]`，自动创建并存储连接于 `Dict[str, Connection]`。     |
| **多进程 Server 管理器** | `start_all_services()` 会为每个服务启动独立的 HTTP MCP 服务。<br>使用 `close_all_services()` 关闭全部服务。 |
| **支持外部服务**         | 可以连接外部已运行的 MCP 服务，而不是自动启动它们。                                                         |
| **环境变量控制**         | 使用 `.env` 决定是否启动或仅连接服务。                                                              |
| **自动启动器**          | `python -m finmcp.agent_tools` 可一次性启动所有服务（推荐）。                                  |
| **健康检测器**          | 周期性 ping 检查所有服务是否存活。                                                                 |

# 使用方法

导入模块：

```python
from finmcp.agent_tools import (
    MCP_SERVICES,
    MCP_CONNECTIONS,
    MCP_PROCESSES,
    start_all_services,
    close_all_services,
)
```

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

## 外部启动服务（推荐）

```bash
uv run -m finmcp.agent_tools
```

这将执行包内的 `__main__`，并将：

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

## 使用 FastMCP CLI 启动服务

```bash
fastmcp run my_service.py --transport http --port [port]
```

## 关闭所有服务

**如果服务是内部启动的：**

```python
close_all_services()
```

**如果服务是外部启动：**

使用 `Ctrl + C` 或向进程发送 `SIGINT` / `SIGTERM`，模块会自动关闭所有服务。

## 环境变量说明

| 变量                            | 行为              |
| ----------------------------- | --------------- |
| `START_SERVICES=True`         | 在当前应用中启动 MCP 服务 |
| `START_SERVICES=False`        | 不启动本地服务，仅连接远程服务 |
| `[PACKAGE_NAME]_SERVICE_PORT` | 指定外部服务的端口       |

# 自动发现行为

任何放在 `finmcp/agent_tools/` 下且 **在顶层定义并暴露 `FastMCP` 实例** 的 `.py` 文件都会自动被加载。

示例：

```python
from fastmcp import FastMCP

mcp = FastMCP("my_custom_service")

@mcp.tool(...)
def some_tool(...):
    ...
```

> ⚠️ **不要把 FastMCP 实例隐藏在函数或类内部**
> 自动扫描只能识别顶层暴露的 FastMCP 对象。


# 与 LangChain 的集成示例

当服务已启动或连接成功后，获取工具非常简单：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from finmcp.agent_tools import MCP_CONNECTIONS

client = MultiServerMCPClient(MCP_CONNECTIONS)

tools = await client.get_tools()
```

然后即可将工具交由 LangChain Agent 使用。


# 创建一个新的 MCP 服务

直接遵循标准的 [FastMCP](https://gofastmcp.com/getting-started/quickstart) 语法即可，无需额外代码：

```python
from fastmcp import FastMCP

mcp = FastMCP("My MCP Server")

@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

保存文件后：

* 它会被自动发现
* 启动时自动分配端口
* 可立即被 LangChain 使用

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
