Languages: [English](README.md) | 中文

# 简介

**finmcp** 是一个用于统一管理多个 MCP（Model Context Protocol）服务的轻量级框架。
它适用于需要为 LLM（金融数据分析场景）提供可调用工具的项目，例如：

* 获取股票 / 指数 / 期货 / 外汇历史行情
* 获取新闻与文本类信息
* 进行网页搜索
* 以及各种用户自定义的金融数据或分析服务

**finmcp** 自身包含一些内建的金融类 MCP 服务，同时支持用户通过 `entry_points` 扩展额外的 MCP 服务，使它们与内建服务一起被 finmcp 管理。

---

## 特性

* **统一管理 MCP 服务**
  将多个 FastMCP 实例集中管理、统一启动、关闭与连接信息记录。

* **插件式服务扩展（entry_points）**
  用户可以在自己的库中注册 FastMCP 实例，使其被 finmcp 管理（无需修改 finmcp 代码）。

* **自动端口管理与连接记录**
  所有服务启动后会将 URL 写入连接记录文件。

* **服务可存活检测（Ping 模式）**
  使用 `uv run -m finmcp` 启动时，会在后台自动每 10 秒向所有 MCP 服务发送 Ping 请求，并输出状态日志。

* **LangChain / MultiServerMCPClient 无缝集成**
  直接通过 `MCP_CONNECTIONS` 获取全部 MCP 服务 URL。

---

# 安装

finmcp 使用 uv 管理，可直接从 GitHub 安装：

```bash
uv add https://github.com/hashhashgo/FinMCP.git
```

安装后即可在任何 uv 项目中使用 finmcp 管理 MCP 服务。

---

# 启动 MCP 服务

## 方式 1：使用命令自动启动并后台 Ping（推荐）

```bash
uv run -m finmcp
```

该命令会：

1. 启动所有通过 entry_points 注册的 FastMCP 服务
2. 分配端口并写入连接记录文件
3. 输出：

```
All MCP services are up and running.
```

4. 后台每 10 秒 Ping 所有服务，并输出类似日志：

```
INFO:     127.0.0.1:39275 - "POST /mcp HTTP/1.1" 200 OK
Pinged service service_name successfully.
```

用于确保 MCP 服务在线。

## 方式2：在程序中动态启动

需要在环境变量中设置

```bash
START_SERVICES_INTERNAL=true
```

然后当主程序`start_all_services()`时自动启动所有MCP服务。

**注意：**使用此方式在`close_all_services()`时会关闭所有记录的MCP服务，注意释放连接。

## 环境变量

```bash
START_SERVICES_INTERNAL=false
CONNECTION_RECORD_FILE="agent_tools_service_ports.json"
FINMCP_HOST="0.0.0.0"
```

**字段说明：**

| 字段                    | 类型    | 说明                                   |
| ----------------------- | ------- | -------------------------------------- |
| START_SERVICES_INTERNAL | boolean | 是否在程序内部启动服务                 |
| CONNECTION_RECORD_FILE  | str     | 连接信息保存的位置                     |
| FINMCP_HOST             | str     | 服务器绑定地址，如127.0.0.1、0.0.0.0等 |

*不需要手动指定端口，程序会自动检测可用端口并绑定*

---

# 在主程序中使用 finmcp

finmcp 提供三个核心 API：

* `start_all_services()`
* `close_all_services()`
* `MCP_CONNECTIONS`（连接信息字典）

## 示例

```python
from finmcp import MCP_CONNECTIONS, start_all_services, close_all_services
from langchain_mcp_adapters.client import MultiServerMCPClient

async def main():

    # 启动所有 MCP 服务（或加载连接记录）
    start_all_services()

    client = MultiServerMCPClient(connections=MCP_CONNECTIONS)
    tools = await client.get_tools()

    # 示例：使用某个工具
    result = await client.call_tool(
        "fin_history.history",
        {
            "symbol": "AAPL",
            "start": "2020-01-01",
            "freq": "daily",
        }
    )
    print(result)

    # 程序结束前关闭服务或清除连接
    close_all_services()
```

---

# 注册新的 MCP 服务

## 方式1：注册插件方式

finmcp 通过 `entry_points` 接收外部 MCP 服务。
任何第三方库只需提供：

### 1. 定义一个 FastMCP 实例

例如 `my_pkg/my_service.py`：

```python
from fastmcp import FastMCP

mcp = FastMCP("MyService")

@mcp.tool
def echo(text: str):
    return text
```

### 2. 在您的项目的 `pyproject.toml` 注册到 finmcp

```toml
[project.entry-points."finmcp.services"]
myservice = "my_pkg.my_service:mcp"
```

### 3. 安装您的库

```bash
uv pip install --editable .
```

如果对pyproject.toml的entry points有更新，需要重新编译：

```python
uv build
```

**注意：**如果不安装和编译，您注册的记录`uv`不会自动添加到项目的entry points中。

### 4. finmcp 会自动管理您的 MCP

运行：

```bash
uv run -m finmcp
```

## 方式2：自动扫描（已弃用）

`finmcp.agent_tools` 本身也是一个包管理器，它可以自动扫描和管理文件夹下的所有服务。

详细介绍请查看[README](./finmcp/agent_tools/README.zh_CN.md)。

**注意：**如无特殊需求，请不要 `import finmcp.agent_tools` 下的任何模块或者使用这个功能。此功能和 `finmcp` 模块本身的功能冲突。

---

# 使用说明总结

| 功能                     | 操作                                                         |
| ------------------------ | ------------------------------------------------------------ |
| 从 GitHub 安装 finmcp    | `uv add https://github.com/hashhashgo/FinMCP.git`            |
| 启动所有 MCP 并后台 Ping | `uv run -m finmcp`                                           |
| 主程序中启动/读取连接    | `start_all_services()`                                       |
| 在 LangChain 中使用      | `client = MultiServerMCPClient(connections=MCP_CONNECTIONS)` |
| 关闭所有 MCP 服务        | `close_all_services()`                                       |
| 注册新 MCP               | 在您的库的 `pyproject.toml` 写入 `[project.entry-points."finmcp.services"]` |

---

# License

MIT

