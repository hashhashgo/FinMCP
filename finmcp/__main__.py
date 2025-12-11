from . import start_all_services, close_all_services, MCP_CONNECTIONS
from .ping_client import PingClient
import time
from signal import signal, SIGINT, SIGTERM

running = True
def stop_services(signum, frame):
    global running
    print("Stopping all MCP services...")
    running = False
    close_all_services()
    exit(0)

if __name__ == "__main__":
    signal(SIGINT, stop_services)
    signal(SIGTERM, stop_services)
    start_all_services(True)
    connections = {}
    for mcp_service in MCP_CONNECTIONS:
        connections[mcp_service] = PingClient(MCP_CONNECTIONS[mcp_service].get("url", ""))
    while running:
        for mcp_service in MCP_CONNECTIONS:
            try:
                connections[mcp_service].ping_connection()
                print(f"Pinged service {mcp_service} successfully.")
            except Exception as e:
                print(f"Error pinging connection: {e}")
        time.sleep(10)