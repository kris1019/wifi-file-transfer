import os, json, socket, shutil
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote

ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(ROOT, "uploads")
WEB_DIR = os.path.join(ROOT, "web")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024

def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("1.1.1.1", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()

def safe_name(name):
    name = os.path.basename(name).replace("\\", "_").replace("/", "_").strip()
    return name or "unnamed-file"

class Handler(BaseHTTPRequestHandler):
    server_version = "WiFiFileTransfer/1.0"

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path == "/api/files":
            files = []
            for name in sorted(os.listdir(UPLOAD_DIR), key=str.lower):
                full = os.path.join(UPLOAD_DIR, name)
                if os.path.isfile(full):
                    files.append({"name": name, "size": os.path.getsize(full)})
            return self.send_json(files)

        if path.startswith("/download/"):
            name = safe_name(path[len("/download/"):])
            full = os.path.join(UPLOAD_DIR, name)
            if not os.path.isfile(full):
                return self.send_json({"error": "File not found"}, 404)
            size = os.path.getsize(full)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.send_header("Content-Disposition", 'attachment; filename="' + name.replace('"', "_") + '"')
            self.end_headers()
            with open(full, "rb") as f:
                shutil.copyfileobj(f, self.wfile, length=1024 * 1024)
            return

        if path == "/" or path == "/index.html":
            full = os.path.join(WEB_DIR, "index.html")
        else:
            return self.send_json({"error": "Not found"}, 404)

        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if urlparse(self.path).path != "/api/upload":
            return self.send_json({"error": "Not found"}, 404)

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type or "boundary=" not in content_type:
            return self.send_json({"error": "Use multipart/form-data"}, 400)

        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_FILE_SIZE:
            return self.send_json({"error": "File is empty or too large"}, 413)

        boundary = content_type.split("boundary=", 1)[1].strip().strip('"').encode()
        body = self.rfile.read(length)

        marker = b'filename="'
        start = body.find(marker)
        if start == -1:
            return self.send_json({"error": "No file selected"}, 400)

        name_start = start + len(marker)
        name_end = body.find(b'"', name_start)
        filename = safe_name(body[name_start:name_end].decode("utf-8", "replace"))

        header_end = body.find(b"\r\n\r\n", name_end)
        if header_end == -1:
            return self.send_json({"error": "Invalid upload"}, 400)

        data_start = header_end + 4
        data_end = body.find(b"\r\n--" + boundary, data_start)
        if data_end == -1:
            return self.send_json({"error": "Invalid upload data"}, 400)

        data = body[data_start:data_end]
        target = os.path.join(UPLOAD_DIR, filename)
        base, ext = os.path.splitext(filename)
        n = 1
        while os.path.exists(target):
            target = os.path.join(UPLOAD_DIR, f"{base} ({n}){ext}")
            n += 1

        with open(target, "wb") as f:
            f.write(data)

        return self.send_json({"ok": True, "name": os.path.basename(target), "size": len(data)})

    def do_DELETE(self):
        path = unquote(urlparse(self.path).path)
        if not path.startswith("/api/files/"):
            return self.send_json({"error": "Not found"}, 404)
        name = safe_name(path[len("/api/files/"):])
        full = os.path.join(UPLOAD_DIR, name)
        if not os.path.isfile(full):
            return self.send_json({"error": "File not found"}, 404)
        os.remove(full)
        return self.send_json({"ok": True})

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")

if __name__ == "__main__":
    ip = local_ip()
    print("\n=== WiFi File Transfer ===")
    print(f"PC:    http://localhost:8765")
    print(f"PHONE: http://{ip}:8765")
    print("Keep this window open while transferring files.")
    print("Press Ctrl+C to stop.\n")
    ThreadingHTTPServer(("0.0.0.0", 8765), Handler).serve_forever()
