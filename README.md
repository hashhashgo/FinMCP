Languages: English | [中文](README.zh_CN.md)

---

# Introduction

**FinTools** is a financial data and analysis toolkit designed to unify and manage reusable financial tools and data interfaces.

It provides a collection of directly callable, function-level tools, and can optionally expose them to LLM / Agent systems via MCP (Model Context Protocol).

The goal of FinTools is to serve as a lightweight, composable, and reusable collection of financial tools.

---

## Types of Tools Provided

FinTools currently includes (and continues to expand) the following types of tools:

* Retrieval of historical market data for stocks, indices, futures, and FX
* Access to financial news, announcements, and other text-based information
* Web search and external information retrieval
* User-defined financial data or analytical logic
* Optional MCP interfaces for LLM usage

---

## MCP Support (Optional)

FinTools can act as a manager and launcher for MCP services, but MCP is only one of the supported integration methods:

* You may completely skip MCP and directly call tools in Python
* Or use MCP to expose these tools to LLMs, LangChain, or multi-agent systems

FinTools ships with some built-in financial MCP services and also supports plugin-based extension of additional MCP services via `entry_points`.

---

# Features

## Toolkit-Oriented Design

* All functionality is centered around tools
* Tools are independently usable, composable, and reusable
* No mandatory dependency on agents, frameworks, or runtimes

## Plugin-Based MCP Extension (`entry_points`)

* Register FastMCP instances from external projects
* No modification of FinTools source code required
* Built-in and external services can be managed uniformly when MCP is enabled

## MCP Service Management (Optional)

* Automatic port allocation
* Unified connection record management
* Service liveness detection (Ping)

## LangChain / MultiServerMCPClient Integration

* Retrieve all MCP service connections via `MCP_CONNECTIONS`
* No manual URL configuration required

---

# Installation

FinTools uses **uv** for dependency management and can be installed directly from GitHub:

```bash
uv add https://github.com/hashhashgo/FinTools.git
```

After installation, FinTools can be used in any uv-managed project.

---

# (Optional) Starting MCP Services

If you do not use MCP or LLMs, you may skip this section.

## Method 1: Command-Line Startup (Recommended)

```bash
uv run -m fintools
```

This command will:

1. Start all MCP services registered via `entry_points`
2. Automatically allocate ports and write connection records
3. Output:

```bash
All MCP services are up and running.
```

4. Ping all services every 10 seconds in the background and log status messages:

```bash
INFO: 127.0.0.1:39275 - "POST /mcp HTTP/1.1" 200 OK
Pinged service service_name successfully.
```

---

## Method 2: Dynamic Startup in Code

Set the environment variable:

```toml
START_SERVICES_INTERNAL=true
```

Then call in your program:

```python
start_all_services()
```

Before exiting the program, call:

```python
close_all_services()
```

---

## MCP-Related Environment Variables

```toml
START_SERVICES_INTERNAL=false
CONNECTION_RECORD_FILE="agent_tools_service_ports.json"
FINTOOLS_HOST="0.0.0.0"
```

| Variable                | Type    | Description                              |
| ----------------------- | ------- | ---------------------------------------- |
| START_SERVICES_INTERNAL | boolean | Whether to start MCP services internally |
| CONNECTION_RECORD_FILE  | str     | Path to MCP connection record file       |
| FINTOOLS_HOST           | str     | Host address to bind MCP services        |

No manual port configuration is required; FinTools will automatically detect and assign available ports.

---

# Using FinTools in Your Program (MCP Example)

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

# Registering New MCP Services (Plugin-Based)

## 1. Define a FastMCP Instance

```python
from fastmcp import FastMCP

mcp = FastMCP("MyService")

@mcp.tool
def echo(text: str):
    return text
```

## 2. Register via `entry_points` in Your Project

```toml
[project.entry-points."fintools.mcp_services"]
myservice = "my_pkg.my_service:mcp"
```

## 3. Install Your Project

```bash
uv pip install --editable .
uv build
```

After installation, FinTools will automatically discover and manage the MCP service.

---

# Database and Caching Support

FinTools supports caching downloaded data to a local database.

Set the environment variable:

```bash
FINTOOLS_DB=history.db
```

Example of creating a SQLite database file:

```bash
touch history.db
```

---

# Usage Summary

| Functionality           | Command / API                                         |
| ----------------------- | ----------------------------------------------------- |
| Install FinTools        | `uv add https://github.com/hashhashgo/FinTools.git` |
| Start MCP services      | `uv run -m fintools`                                |
| Start services in code  | `start_all_services()`                              |
| Get MCP connection info | `MCP_CONNECTIONS`                                   |
| Close MCP services      | `close_all_services()`                              |
| Register external MCP   | `entry_points`                                      |

---

# License

MIT

---
