import requests
import logging
logger = logging.getLogger(__name__)

class PingClient:
    
    def __init__(self, url: str, timeout: int = 5):
        self.url = url
        self.timeout = timeout
        self.session = 1
        self.connected = False
        self.init_connection()

    def init_connection(self):
        self.headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json"
        }
        self.init_payload = {
            "jsonrpc": "2.0",
            "id": self.session,
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
        resp = requests.post(self.url, json=self.init_payload, headers=self.headers, timeout=self.timeout)
        resp.raise_for_status()
        self.headers['mcp-session-id'] = resp.headers.get('mcp-session-id', '')
        requests.post(self.url, json={
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }, headers=self.headers, timeout=self.timeout).raise_for_status()
        self.connected = True
    
    def ping_connection(self):
        if not self.connected:
            raise Exception("Not connected. Please initialize the connection first.")
        ping_payload = {
            "jsonrpc": "2.0",
            "id": self.session,
            "method": "ping",
            "params": {}
        }
        try:
            resp = requests.post(self.url, json=ping_payload, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
        except Exception as e:
            self.connected = False
            logger.error(f"Ping failed: {e}")
            return False
        return True

    def disconnect(self):
        self.session += 1
        self.connected = False

    def reconnect(self):
        self.disconnect()
        self.init_connection()
    