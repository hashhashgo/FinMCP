import pkgutil
from pathlib import Path
from typing import Any, Dict
import importlib
from fastmcp import FastMCP
import socket
from langchain_mcp_adapters.sessions import Connection, StreamableHttpConnection
from multiprocessing import Process
import requests
import time
import os
import json
import logging
logger = logging.getLogger(__name__)

MCP_SERVICES: Dict[str, FastMCP] = {}
MCP_CONNECTIONS: Dict[str, Connection] = \
    json.load(open("agent_tools_service_ports.json", "r")) \
        if os.path.exists("agent_tools_service_ports.json") else {}
MCP_PROCESSES: Dict[str, Process] = {}

def _discover_mcp_service_modules():
    """
    扫描当前包下所有 .py 模块，确保它们被导入以注册 MCP 服务。
    """
    package_name = __name__
    package_path = Path(__file__).parent

    for module_info in pkgutil.iter_modules([str(package_path)]):
        mod_name = module_info.name

        if mod_name == "__init__" or mod_name.startswith("_"):
            continue

        full_name = f"{package_name}.{mod_name}"
        module = importlib.import_module(full_name)
        
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, FastMCP):
                MCP_SERVICES[mod_name] = attr

_discover_mcp_service_modules()

def _run_service(mcp_service: str, port: int) -> None:
    MCP_SERVICES[mcp_service].run(
        transport="http",
        host=os.getenv("SERVICE_HOST", "0.0.0.0"),
        port=port,
        path="/mcp",
        show_banner=False
    )

def start_all_services(start_anyway: bool = False, test_max_retries: int = 10, test_timeout: int = 1) -> None:
    global MCP_CONNECTIONS
    if os.getenv("START_SERVICES_INTERNAL", "false").lower() == "true" or start_anyway:
        logger.info("Starting MCP services...")
        current_port = 8000
        for mcp_service in MCP_SERVICES:
            logger.info(f"Starting MCP service: {mcp_service}")
            while current_port < 9000:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    try:
                        s.bind(("127.0.0.1", current_port))
                        break
                    except OSError:
                        logger.info(f"Port {current_port} is in use, trying next port...")
                        current_port += 1
            MCP_PROCESSES[mcp_service] = Process(target=_run_service, args=(mcp_service, current_port))
            MCP_PROCESSES[mcp_service].daemon = True
            MCP_PROCESSES[mcp_service].start()
            MCP_CONNECTIONS[mcp_service] = StreamableHttpConnection(
                transport="streamable_http",
                url=f"http://127.0.0.1:{current_port}/mcp",
            )
            logger.info(f"MCP service {mcp_service} is running on port {current_port}")
            current_port += 1
        with open("agent_tools_service_ports.json", "w") as f:
            json.dump(MCP_CONNECTIONS, f, indent=4)
    else:
        logger.info("Skipping MCP services startup as per configuration.")
    check_services_running(test_max_retries, test_timeout)

def check_services_running(test_max_retries: int = 10, test_timeout: int = 1) -> None:
    retry_counts = {mcp_service: 0 for mcp_service in MCP_CONNECTIONS}
    while True:
        all_running = True
        for mcp_service in MCP_CONNECTIONS:
            url = MCP_CONNECTIONS[mcp_service].get("url", None)
            assert url is not None, f"MCP service {mcp_service} is not a HTTP service."
            if retry_counts[mcp_service] == -1: continue
            try:
                req = requests.get(url, timeout=test_timeout)
                if req.status_code >= 500: # 启动完成会返回406，因为格式不对
                    all_running = False
                    retry_counts[mcp_service] += 1
                    time.sleep(test_timeout)
                else:
                    retry_counts[mcp_service] = -1
            except Exception:
                all_running = False
                retry_counts[mcp_service] += 1
            if retry_counts[mcp_service] > test_max_retries:
                raise RuntimeError(f"MCP service {mcp_service} failed to connect after {test_max_retries} retries.")
        if all_running:
            break
    logger.info("All MCP services are up and running.")

def close_all_services() -> None:
    logger.info("Closing all MCP services...")
    for mcp_service, process in MCP_PROCESSES.items():
        logger.info(f"Terminating MCP service: {mcp_service}")
        process.terminate()
        process.join()
    MCP_PROCESSES.clear()
    MCP_CONNECTIONS.clear()
    logger.info("All MCP services have been closed.")
    os.remove("agent_tools_service_ports.json")

__all__ = ["MCP_SERVICES", "MCP_CONNECTIONS", "MCP_PROCESSES", "start_all_services", "close_all_services"]
