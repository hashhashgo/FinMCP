import os
import socket
import json
import time

from langchain_mcp_adapters.sessions import Connection, StreamableHttpConnection
from fastmcp import FastMCP
from multiprocessing import Process

from typing import Dict, List, Tuple

from .ping_client import PingClient

import logging


CONNECTION_RECORD_FILE = os.getenv("CONNECTION_RECORD_FILE", "agent_tools_service_ports.json")

ENTRYPOINT_GROUP = "finmcp.services"
MCP_HOST = os.environ.get("FINMCP_HOST", "127.0.0.1")
MCP_PATH = "/mcp"


MCP_SERVICES: Dict[str, FastMCP] = {}
MCP_CONNECTIONS: Dict[str, Connection] = \
    json.load(open(CONNECTION_RECORD_FILE, "r")) \
        if os.path.exists(CONNECTION_RECORD_FILE) else {}
MCP_PROCESSES: Dict[str, Process] = {}



def _discover_services() -> None:
    """
    从 entry_points 发现所有 MCP 服务。
    返回列表: [(service_name, module, attr), ...]
    """
    from importlib.metadata import entry_points

    eps = entry_points(group=ENTRYPOINT_GROUP)

    for ep in eps:
        # ep.module / ep.attr 类似 "pkg.mod" / "mcp"
        # ep.load() 返回对象，这里可以顺便验证一下类型
        try:
            obj = ep.load()
        except Exception:
            logging.warning(f"Failed to load MCP service entry point: {ep.name}", exc_info=True)
            continue

        if not isinstance(obj, FastMCP):
            continue

        # service_name 用 mcp.name，而不是 ep.name
        MCP_SERVICES[ep.name] = obj

_discover_services()

def _run_service(mcp_service: str, port: int) -> None:
    MCP_SERVICES[mcp_service].run(
        transport="http",
        host=MCP_HOST,
        port=port,
        path=MCP_PATH,
        show_banner=False
    )

def start_all_services(start_anyway: bool = False, test_max_retries: int = 10, test_timeout: int = 1) -> None:
    global MCP_CONNECTIONS
    if MCP_PROCESSES:
        print("MCP services are already running.")
        check_services_running(test_max_retries, test_timeout)
        return
    if MCP_CONNECTIONS:
        print("MCP services connections already exist. Assuming services are running.")
        check_services_running(test_max_retries, test_timeout)
        return
    if os.getenv("START_SERVICES_INTERNAL", "false").lower() == "true" or start_anyway:
        print("Starting MCP services...")
        current_port = 8000
        for mcp_service in MCP_SERVICES:
            print(f"Starting MCP service: {mcp_service}")
            while current_port < 9000:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    try:
                        s.bind((MCP_HOST, current_port))
                        break
                    except OSError:
                        print(f"Port {current_port} is in use, trying next port...")
                        current_port += 1
            MCP_PROCESSES[mcp_service] = Process(target=_run_service, args=(mcp_service, current_port))
            MCP_PROCESSES[mcp_service].daemon = True
            MCP_PROCESSES[mcp_service].start()
            MCP_CONNECTIONS[mcp_service] = StreamableHttpConnection(
                transport="streamable_http",
                url=f"http://{MCP_HOST}:{current_port}/mcp",
            )
            print(f"MCP service {mcp_service} is running on port {current_port}")
            current_port += 1
        with open(CONNECTION_RECORD_FILE, "w") as f:
            json.dump(MCP_CONNECTIONS, f, indent=4)
    else:
        print("Skipping MCP services startup as per configuration.")
    check_services_running(test_max_retries, test_timeout)

def check_services_running(test_max_retries: int = 10, test_timeout: int = 1) -> None:
    retry_counts = {mcp_service: 0 for mcp_service in MCP_CONNECTIONS}
    while True:
        all_running = True
        for mcp_service in MCP_CONNECTIONS:
            url = MCP_CONNECTIONS[mcp_service].get("url", None)
            assert url is not None, f"MCP service {mcp_service} is not a HTTP service."
            if retry_counts[mcp_service] == -1: continue
            time_start = time.time()
            try:
                client = PingClient(url, timeout=test_timeout)
                client.ping_connection()
                client.disconnect()
                retry_counts[mcp_service] = -1
            except Exception:
                all_running = False
                retry_counts[mcp_service] += 1
                while time.time() - time_start < test_timeout:
                    time.sleep(0.1)
            if retry_counts[mcp_service] > test_max_retries:
                raise RuntimeError(f"MCP service {mcp_service} failed to connect after {test_max_retries} retries.")
        if all_running:
            break
    print("All MCP services are up and running.")

def close_all_services() -> None:
    if not MCP_PROCESSES:
        MCP_CONNECTIONS.clear()
        return
    print("Closing all MCP services...")
    for mcp_service, process in MCP_PROCESSES.items():
        print(f"Terminating MCP service: {mcp_service}")
        try:
            process.terminate()
            process.join()
            del MCP_CONNECTIONS[mcp_service]
            with open(CONNECTION_RECORD_FILE, "w") as f:
                json.dump(MCP_CONNECTIONS, f, indent=4)
        except Exception as e:
            print(f"Error terminating MCP service {mcp_service}: {e}")
    MCP_PROCESSES.clear()
    MCP_CONNECTIONS.clear()
    print("All MCP services have been closed.")
    if not json.load(open(CONNECTION_RECORD_FILE)):
        os.remove(CONNECTION_RECORD_FILE)

__all__ = ["MCP_SERVICES", "MCP_CONNECTIONS", "start_all_services", "close_all_services"]
