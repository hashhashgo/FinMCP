Languages: English | [中文](README.zh_CN.md)

***Directly using this package is deprecated. Please import fintools or start fintools as a module. And register the mcp instance in entry points.
For more information, please read [README](../../README.md)***

# Introduction
A dynamic, auto-discovering MCP service manager built on FastMCP.
It automatically loads all FastMCP service instances defined under the fintools.agent_tools package and provides:

* Automatic MCP server startup (multi-process, HTTP)

* Connection to existing remote MCP services

* Centralized registry of services and active connections

* Health monitoring (periodic ping checks)

# Features

| Feature                          | Description                                                  |
| -------------------------------- | ------------------------------------------------------------ |
| **Auto-discovery**               | Scans all `.py` files in `agent_tools/`, loads exposed `FastMCP` instances automatically. |
| **Unified registry**             | All discovered services are stored in `MCP_SERVICES: Dict[str, FastMCP]`.<br />Automatically create connections to services, storing in `Dict[str, Connection]` |
| **Multi-process server manager** | `start_all_services()` launches each service as an independent HTTP MCP server.<br />`close_all_services()` for closing all services. |
| **External server support**      | Can connect to existing running servers instead of starting new ones. |
| **Environment-driven config**    | `.env` controls whether to start or merely connect to services. |
| **Auto-launcher**                | `python -m fintools.agent_tools` starts all services externally (recommended). |
| **Health checker**               | Periodic ping monitoring for all active MCP servers.         |

# Usage

Import the built-in control module:

```python
from fintools.agent_tools import (
    MCP_SERVICES,
    MCP_CONNECTIONS,
    MCP_PROCESSES,
    start_all_services,
    close_all_services,
)
```

## Starting Services Internally (From Your App)

Configure in `.env`:

```bash
START_SERVICES=True
```

Then start all services in your app:

```python
start_all_services()
```

Or force starting new services with :

```python
start_all_services(start_anyway=True)
```

## Starting Services Externally (Recommended)

```bash
uv run -m fintools.agent_tools
```

This executes the package’s `__main__`, which:

- Spawns each MCP service as an HTTP server on increasing ports
- Periodically pings all servers to verify health

Then in `.env`:

```bash
START_SERVICES=false
MY_SERVICE_PORT=8000
ANOTHER_SERVICE_PORT=8001
......
```

In your app:

```python
start_all_services(create_new=False)
```

## Using FastMCP CLI

```bash
fastmcp run my_service.py --transport http --port [port]
```

## Close All services

**If you start services internally:**

```python
close_all_services()
```

**If you start service externally:**

Just send `SIGINT` or `SIGTERM` to the python runtime, the module will automatically terminate them.

## Environment Variables

| Variable                      | Behavior                                              |
| ----------------------------- | ----------------------------------------------------- |
| `START_SERVICES=True`         | Launch MCP servers inside the current app             |
| `START_SERVICES=False`        | Do not launch local servers; connect to existing ones |
| `[PACKAGE_NAME]_SERVICE_PORT` | Manual port mapping when using external services      |

# Auto-Discovery Behavior

Any `.py` module inside `fintools/agent_tools/` that **exposes a `FastMCP` instance at top-level** will be automatically registered.

Example:

```python
from fastmcp import FastMCP

mcp = FastMCP("my_custom_service")

@mcp.tool(...)
def some_tool(...):
    ...
```

> ⚠️ **Do not hide the instance behind functions or classes.**
>  The module loader detects **only top-level exported `FastMCP` objects**.

# Example Integration With LangChain

Once services are started or connected, simply load their tools normally:

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from fintools.agent_tools import MCP_CONNECTIONS

client = MultiServerMCPClient(MCP_CONNECTIONS)

tools = await client.get_tools()
```

Now the tools can be passed into any LangChain agent.

# Creating a New MCP Service

Just follow standard [FastMCP](https://gofastmcp.com/getting-started/quickstart) syntax.

```python
from fastmcp import FastMCP

mcp = FastMCP("My MCP Server")

@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

After saving the file:

- It is automatically discovered
- It will be assigned a port when launched
- It becomes available to LangChain

# Debug a MCP Service

Start a MCP inspector:
```bash
npx @modelcontextprotocol/inspector
```

Connect with:

| Settings        | Values                      |
| --------------- | --------------------------- |
| Transport Type  | Streamable HTTP             |
| URL             | http://127.0.0.1:[port]/mcp |
| Connection Type | Via Proxy                   |

Then you can view your tools in `Tools` tab.