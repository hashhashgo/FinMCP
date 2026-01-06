Languages: English | [中文](README.zh_CN.md)

***This module no longer discovers services by scanning source directories.  
All MCP services must be explicitly registered via entry_points.***

---

# Introduction

A dynamic, plugin-based MCP service manager built on **FastMCP**.

This module is responsible for uniformly managing and running all `FastMCP` instances
registered via `entry_points`, for example:

```toml
[project.entry-points."fintools.mcp_services"]
tool_fin_history = "fintools.api.mcp.tool_fin_history:mcp"
```

It provides:

- Automatic loading and registration of MCP services
- Multi-process + HTTP MCP server startup and lifecycle management
- Ability to connect to already running remote MCP services
- Unified management of all MCP service connections
- Periodic health checks (Ping)

---

# Features

| Feature | Description |
|------|------------|
| **Plugin-based discovery** | Load MCP services via `project.entry-points."fintools.mcp_services"` |
| **Unified registration** | All services are stored in `MCP_SERVICES: Dict[str, FastMCP]` |
| **Centralized connection management** | All connections are maintained in `MCP_CONNECTIONS: Dict[str, Connection]` |
| **Multi-process server manager** | `start_all_services()` launches an independent HTTP server per MCP service |
| **External service support** | Connect to existing MCP services without spawning new processes |
| **Environment variable control** | Control startup vs. connection-only behavior via `.env` |
| **One-command launcher** | `python -m fintools.api.mcp` starts all registered services (recommended) |
| **Health monitoring** | Periodic ping checks to ensure service liveness |

---

# Usage

## MCP Service Registration

All MCP services **must** be registered via `entry_points`.

### Example: Define an MCP service

```python
from fastmcp import FastMCP

mcp = FastMCP("my_custom_service")

@mcp.tool
def echo(text: str) -> str:
    return text
```

### Register via entry_points

```toml
[project.entry-points."fintools.mcp_services"]
my_service = "my_pkg.my_service:mcp"
```

After installing the project, the MCP service will be automatically loaded and managed.

- No modification to `fintools` source code required
- Supports independent extension across multiple projects or teams
- Implicit source-directory scanning is no longer supported

---

## Importing the Module

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

## Starting Services Internally

Configure `.env`:

```bash
START_SERVICES=True
```

Then start services in code:

```python
start_all_services()
```

Or force startup regardless of environment configuration:

```python
start_all_services(start_anyway=True)
```

---

## Starting Services Externally (Recommended)

```bash
uv run -m fintools.api.mcp
```

This executes the module's `__main__` and will:

- Load all MCP services registered via entry_points
- Start an independent HTTP server for each MCP service (ports auto-assigned)
- Periodically ping services to monitor health

Then configure `.env`:

```bash
START_SERVICES=False
MY_SERVICE_PORT=8000
ANOTHER_SERVICE_PORT=8001
...
```

And connect without creating new processes:

```python
start_all_services(create_new=False)
```

---

## Starting a Single Service via FastMCP CLI (Optional)

```bash
fastmcp run my_service.py --transport http --port [port]
```

---

## Shutting Down Services

**If services were started internally:**

```python
close_all_services()
```

**If services were started externally:**

Use `Ctrl + C` or send `SIGINT` / `SIGTERM` to the process.
All services will be shut down gracefully.

---

## Environment Variables

| Variable | Behavior |
|-------|---------|
| `START_SERVICES=True` | Start MCP services in the current application |
| `START_SERVICES=False` | Do not start local services; only connect to remote ones |
| `[PACKAGE_NAME]_SERVICE_PORT` | Specify the port of an external MCP service |

---

# LangChain Integration Example

Once services are started or connected, retrieving tools is straightforward:

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from fintools.api.mcp import MCP_CONNECTIONS

client = MultiServerMCPClient(MCP_CONNECTIONS)
tools = await client.get_tools()
```

The retrieved tools can then be injected into LangChain / LangGraph / Agent systems.

---

# Debugging MCP Services

Start the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector
```

Use the following connection settings:

| Setting | Value |
|------|------|
| Transport Type | Streamable HTTP |
| URL | http://127.0.0.1:[port]/mcp |
| Connection Type | Via Proxy |

All tools exposed by the service will be visible on the **Tools** page.

---

# License

MIT

---
