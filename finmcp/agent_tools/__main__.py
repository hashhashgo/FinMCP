from . import start_all_services, close_all_services, MCP_CONNECTIONS
import time
from signal import signal, SIGINT, SIGTERM
import requests

running = True
def stop_services(signum, frame):
    global running
    print("Stopping all MCP services...")
    running = False
    close_all_services()
    exit(0)

def init_connection(url, id = 1):
    if not url: return
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json"
    }
    init_payload = {
        "jsonrpc": "2.0",
        "id": id,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {
                "name": "Background Pinger",
                "version": "1.0.0"
            }
        }
    }
    resp = requests.post(url, json=init_payload, headers=headers, timeout=5)
    resp.raise_for_status()
    # print(resp.headers)
    # print(resp.text)
    headers['mcp-session-id'] = resp.headers.get('mcp-session-id', '')
    requests.post(url, json={
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }, headers=headers, timeout=5).raise_for_status()
    return {
        "headers": headers,
        "url": url,
        "payload": {
            "jsonrpc": "2.0",
            "id": id,
            "method": "initialize",
        }
    }

def ping_connection(connection):
    if not connection: return False
    ping_payload = {
        "jsonrpc": "2.0",
        "id": connection["payload"]["id"],
        "method": "ping",
        "params": {}
    }
    resp = requests.post(connection["url"], json=ping_payload, headers=connection["headers"], timeout=5)
    resp.raise_for_status()

if __name__ == "__main__":
    signal(SIGINT, stop_services)
    signal(SIGTERM, stop_services)
    start_all_services(True)
    connections = {}
    for mcp_service in MCP_CONNECTIONS:
        connections[mcp_service] = init_connection(MCP_CONNECTIONS[mcp_service].get("url", ""))
    while running:
        for mcp_service in MCP_CONNECTIONS:
            try:
                ping_connection(connections[mcp_service])
                print(f"Pinged service {mcp_service} successfully.")
            except Exception as e:
                print(f"Error pinging connection: {e}")
        time.sleep(10)