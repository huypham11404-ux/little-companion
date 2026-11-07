import http.server
import socketserver
import json
import urllib.parse
import os
import mimetypes
import db
import orchestrator

PORT = int(os.environ.get("PORT", 8080))
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

class LittleRoomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/messages":
            limit = 50
            query = urllib.parse.parse_qs(parsed.query)
            if "limit" in query:
                try:
                    limit = int(query["limit"][0])
                except ValueError:
                    pass
            messages = db.get_recent_messages(limit=limit)
            self.send_json_response(200, {"status": "ok", "messages": messages})
            return

        elif path == "/api/memories":
            memories = db.get_all_memories()
            self.send_json_response(200, {"status": "ok", "memories": memories})
            return

        elif path == "/api/settings":
            settings = db.get_settings()
            safe_settings = dict(settings)
            if safe_settings.get("openai_api_key"):
                safe_settings["openai_api_key_masked"] = safe_settings["openai_api_key"][:4] + "..." + safe_settings["openai_api_key"][-4:]
            if safe_settings.get("gemini_api_key"):
                safe_settings["gemini_api_key_masked"] = safe_settings["gemini_api_key"][:4] + "..." + safe_settings["gemini_api_key"][-4:]
            self.send_json_response(200, {"status": "ok", "settings": safe_settings})
            return

        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.read_json_body()

        if path == "/api/chat":
            content = body.get("content", "").strip()
            if not content:
                self.send_json_response(400, {"error": "Content is required"})
                return

            result = orchestrator.orchestrate_turn(content)
            self.send_json_response(200, {
                "status": "ok",
                "user_message": result["user_message"],
                "agent_replies": result["agent_replies"]
            })
            return

        elif path == "/api/memories":
            category = body.get("category", "general")
            title = body.get("title", "").strip()
            content = body.get("content", "").strip()
            memory_id = body.get("id")

            if not title or not content:
                self.send_json_response(400, {"error": "Title and content are required"})
                return

            saved = db.save_memory(category, title, content, memory_id=memory_id)
            self.send_json_response(200, {"status": "ok", "memory": saved})
            return

        elif path == "/api/settings":
            for k, v in body.items():
                if v is not None and not k.endswith("_masked"):
                    db.save_setting(k, str(v))
            self.send_json_response(200, {"status": "ok", "message": "Settings saved"})
            return

        self.send_json_response(404, {"error": "Not found"})

    def read_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        try:
            data = self.rfile.read(content_length).decode("utf-8")
            return json.loads(data)
        except Exception:
            return {}

    def send_json_response(self, status_code, data):
        response_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response_bytes)

def run_server(port=PORT):
    db.init_db()
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), LittleRoomHandler) as httpd:
        print(f"🏡 Our Little Room is open at http://localhost:{port}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
