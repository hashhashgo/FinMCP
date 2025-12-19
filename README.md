Languages: English | [中文](README.zh_CN.md)

# Introduction

**finmcp** is a lightweight framework for **unified management of multiple MCP (Model Context Protocol) services**.
It is designed for LLM-centered financial data analysis tasks, such as:

* Retrieving historical data for stocks, indices, futures, and foreign exchange
* Fetching news and textual information
* Performing web searches
* Managing custom MCP services provided by users

finmcp includes several built-in financial MCP services and also allows users to extend additional MCP services via `entry_points`, so they can be managed alongside the built-in ones.

---

# Features

* **Unified MCP Service Management**
  Centralized startup, shutdown, and connection tracking for multiple FastMCP instances.
* **Plugin-based Service Extension (entry_points)**
  Users can register their own FastMCP instances without modifying finmcp’s source code.
* **Automatic Port Assignment & Connection Recording**
  All services write their assigned URLs into a connection record file after startup.
* **Service Health Check (Ping Mode)**
  When launched via `uv run -m finmcp`, the framework automatically pings all MCP services every 10 seconds and prints status logs.
* **Seamless LangChain / MultiServerMCPClient Integration**
  All MCP service URLs are directly available through `MCP_CONNECTIONS`.

---

# Installation

finmcp is uv-managed and can be installed directly from GitHub:

```bash
uv add https://github.com/hashhashgo/FinMCP.git
```

After installation, finmcp can be used in any uv-managed project.

---

# Starting MCP Services

## Method 1: Start via CLI with Background Ping (Recommended)

```bash
uv run -m finmcp
```

This command will:

1. Start all FastMCP services registered via `entry_points`.
2. Assign ports and write the connection information to the connection record file.
3. Output:

```
All MCP services are up and running.
```

4. Perform background ping checks every 10 seconds, printing logs like:

```
INFO:     127.0.0.1:39275 - "POST /mcp HTTP/1.1" 200 OK
Pinged service service_name successfully.
```

This ensures all MCP services remain healthy and reachable.

---

## Method 2: Start Services Programmatically

Set the following environment variable:

```bash
START_SERVICES_INTERNAL=true
```

Then call `start_all_services()` in your main program.
Services will automatically start internally.

**Note:**
When this mode is enabled, calling `close_all_services()` will shut down all MCP services that were recorded. Ensure you release all resources properly.

---

## Environment Variables

```bash
START_SERVICES_INTERNAL=false
CONNECTION_RECORD_FILE="agent_tools_service_ports.json"
FINMCP_HOST="0.0.0.0"
```

**Description**

| Field                   | Type    | Description                                             |
| ----------------------- | ------- | ------------------------------------------------------- |
| START_SERVICES_INTERNAL | boolean | Whether to start services internally                    |
| CONNECTION_RECORD_FILE  | str     | Path to store service connection records                |
| FINMCP_HOST             | str     | Host binding of MCP services (e.g., 127.0.0.1, 0.0.0.0) |

*Ports do not need to be manually assigned—finmcp automatically discovers available ports.*

---

# Using finmcp in Your Program

finmcp provides three primary APIs:

* `start_all_services()`
* `close_all_services()`
* `MCP_CONNECTIONS` (service connection dictionary)

## Example

```python
from finmcp import MCP_CONNECTIONS, start_all_services, close_all_services
from langchain_mcp_adapters.client import MultiServerMCPClient

async def main():

    # Start all MCP services or load existing connections
    start_all_services()

    client = MultiServerMCPClient(connections=MCP_CONNECTIONS)
    tools = await client.get_tools()

    # Example: invoke a tool
    result = await client.call_tool(
        "fin_history.history",
        {
            "symbol": "AAPL",
            "start": "2020-01-01",
            "freq": "daily",
        }
    )
    print(result)

    # Shut down services or clean up connections
    close_all_services()
```

---

# Registering a New MCP Service

## Method 1: Register via Plugin (Recommended)

finmcp loads third-party MCP services through `entry_points`.
Any external library can provide an MCP service by following these steps:

### 1. Define a FastMCP Instance

`my_pkg/my_service.py`:

```python
from fastmcp import FastMCP

mcp = FastMCP("MyService")

@mcp.tool
def echo(text: str):
    return text
```

### 2. Register Your MCP Service in `pyproject.toml`

```toml
[project.entry-points."finmcp.services"]
myservice = "my_pkg.my_service:mcp"
```

### 3. Install Your Package

```bash
uv pip install --editable .
```

If you update entry_points, rebuild:

```bash
uv build
```

**Note:**
If the package is not installed or built, uv will not detect your entry_points.

### 4. finmcp Will Manage Your MCP Automatically

Run:

```bash
uv run -m finmcp
```

Your service will appear among managed services.

---

## Method 2: Automatic Scanning (Deprecated)

`finmcp.agent_tools` also contains an automatic scanning mechanism that discovers MCP services inside the package folder.

For details, see: [README](finmcp/agent_tools/README.md)

**Warning:**
Do **not** import anything inside `finmcp.agent_tools` unless necessary.
This feature conflicts with the primary finmcp service manager and should generally not be used.

---

# Database Support

This project supports caching all downloaded data by storing it in the database file specified by the `DB_PATH` environment variable.

Please create the corresponding SQLite3 database file yourself, for example:

```bash
sqlite3 history.db
> select * from sqlite_master;
> .quit
```

---

# Summary

| Feature                    | Usage                                                      |
| -------------------------- | ---------------------------------------------------------- |
| Install finmcp from GitHub | `uv add https://github.com/hashhashgo/FinMCP.git`        |
| Start all MCP services     | `uv run -m finmcp`                                       |
| Start/load connections     | `start_all_services()`                                   |
| Use with LangChain         | `MultiServerMCPClient(connections=MCP_CONNECTIONS)`      |
| Stop all services          | `close_all_services()`                                   |
| Register a new MCP service | Add entry under `project.entry-points."finmcp.services"` |

---

# License

MIT
