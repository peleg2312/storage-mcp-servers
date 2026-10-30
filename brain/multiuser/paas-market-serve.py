#!/usr/bin/env python3
"""This VM's marketplace for other VMs, read-only over HTTPS (paas-market-serve.service, port 3443).

  GET /snapshot.tar.gz   with 'Authorization: Bearer <token>': the skills, agents and plugins of /opt/paas/marketplace
                         and /opt/paas/plugins, plus what people shared. MCP servers stay on this VM (their addresses
                         and tokens are this VM's), so they are left out.

On another VM: paas-market connect https://<this vm>:3443 <token>   (root reads the token: cat /etc/paas/market/token)
It runs as the system user paas-market, which can read only /etc/paas/market (token, copy of the VM's certificate).
"""
import hashlib
import hmac
import io
import json
import os
import re
import ssl
import tarfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.environ.get("PAAS_ROOT", "/opt/paas")
CRED = os.environ.get("PAAS_MARKET_ETC", "/etc/paas/market")     # token + TLS certificate, readable by this service only
PORT = int(os.environ.get("PAAS_MARKET_PORT", "3443"))
TOKEN = open(os.path.join(CRED, "token")).read().strip().encode()
_cache = ["", b""]                                  # [etag, tar.gz]
_lock = threading.Lock()


def etag():
    """a hash of the names, sizes and times of what the snapshot holds: cheap next to building it"""
    h = hashlib.sha256()
    m = os.path.join(ROOT, "marketplace")
    for top in ("index.json", "defaults.json", "items/skills", "items/agents", "contrib"):
        top = os.path.join(m, top)
        for root, dirs, files in os.walk(top):
            for n in sorted(files):
                st = os.stat(os.path.join(root, n))
                h.update(f"{root}/{n}{st.st_size}{st.st_mtime_ns}".encode())
        if os.path.isfile(top):
            st = os.stat(top)
            h.update(f"{top}{st.st_size}{st.st_mtime_ns}".encode())
    for top in ("plugins", "plugin-sources"):
        for root, dirs, files in os.walk(os.path.join(ROOT, top)):
            dirs[:] = [d for d in dirs if d != ".git"]
            for n in sorted(files):
                st = os.stat(os.path.join(root, n))
                h.update(f"{root}/{n}{st.st_size}{st.st_mtime_ns}".encode())
    return f'"{h.hexdigest()[:32]}"'


def snapshot(tag):
    """marketplace/ (no MCP items) + plugins/ + plugin-sources/ as tar.gz, built once per change (one thread at a time)"""
    with _lock:
        if _cache[0] != tag:
            _cache[:] = [tag, build()]
        return _cache[1]


def build():
    m = os.path.join(ROOT, "marketplace")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        def put(name, obj):
            data = json.dumps(obj, indent=1).encode()
            ti = tarfile.TarInfo(name)
            ti.size, ti.mode, ti.mtime = len(data), 0o644, int(time.time())
            t.addfile(ti, io.BytesIO(data))
        put("marketplace/index.json", [i for i in json.load(open(os.path.join(m, "index.json"))) if i["kind"] != "mcp"])
        put("marketplace/defaults.json", [i for i in json.load(open(os.path.join(m, "defaults.json"))) if not i.startswith("mcp/")])
        skip = lambda ti: None if os.path.basename(ti.name).startswith("._") or ti.issym() or ti.islnk() else ti
        for sub in ("skills", "agents"):
            p = os.path.join(m, "items", sub)
            if os.path.isdir(p):
                t.add(p, f"marketplace/items/{sub}", filter=skip)
        contrib = os.path.join(m, "contrib")
        for user in sorted(os.listdir(contrib)) if os.path.isdir(contrib) else []:
            for sub in ("skills", "agents"):
                p = os.path.join(contrib, user, sub)
                if os.path.isdir(p):
                    t.add(p, f"marketplace/contrib/{user}/{sub}", filter=skip)
        if os.path.isdir(os.path.join(ROOT, "plugins")):
            t.add(os.path.join(ROOT, "plugins"), "plugins", filter=skip)
        if os.path.isdir(os.path.join(ROOT, "plugin-sources")):     # other marketplaces root added (paas-market source add)
            t.add(os.path.join(ROOT, "plugin-sources"), "plugin-sources",
                  filter=lambda ti: None if re.search(r"(^|/)(\.git|\.[^/]+\.(new|old))(/|$)", ti.name) else skip(ti))
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    server_version = "paas-market"
    timeout = 30                                     # a client that stalls is dropped
    sys_version = ""

    def do_GET(self):
        sent = self.headers.get("Authorization", "").removeprefix("Bearer ").strip().encode()
        if not hmac.compare_digest(sent, TOKEN):
            return self.reply(401, b'{"error":"token needed"}', "application/json")
        if self.path != "/snapshot.tar.gz":
            return self.reply(404, b'{"error":"not found"}', "application/json")
        tag = etag()
        if self.headers.get("If-None-Match") == tag:       # the client already holds this snapshot
            self.send_response(304)
            self.send_header("ETag", tag)
            self.send_header("Content-Length", "0")
            return self.end_headers()
        self.reply(200, snapshot(tag), "application/gzip", tag)

    def reply(self, code, body, ctype, tag=""):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if tag:
            self.send_header("ETag", tag)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}", flush=True)


if __name__ == "__main__":
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(os.path.join(CRED, "paas-ui.crt"), os.path.join(CRED, "paas-ui.key"))
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True, do_handshake_on_connect=False)  # handshake in the worker thread
    print(f"marketplace for other VMs on https://0.0.0.0:{PORT}", flush=True)
    srv.serve_forever()
