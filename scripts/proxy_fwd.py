import base64
import socket
import sys
import threading

UPSTREAM_HOST = "gate.rola.vip"
UPSTREAM_PORT = 2000
USER = sys.argv[1] if len(sys.argv) > 1 else "zUJiFEE8ovFl_1-country-us"
PASS = sys.argv[2] if len(sys.argv) > 2 else "I8oir8k"
LISTEN_PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 7777

AUTH = base64.b64encode(f"{USER}:{PASS}".encode()).decode()


def forward(src, dst):
    try:
        while True:
            data = src.recv(16384)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except Exception:
            pass


def handle(client):
    upstream = None
    try:
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = client.recv(8192)
            if not chunk:
                return
            buf += chunk
            if len(buf) > 65535:
                return
        first_line = buf.split(b"\r\n", 1)[0].decode("latin-1", errors="replace")
        upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        upstream.settimeout(30)
        upstream.connect((UPSTREAM_HOST, UPSTREAM_PORT))
        upstream.settimeout(None)
        if first_line.startswith("CONNECT "):
            target = first_line.split()[1]
            req = (
                f"CONNECT {target} HTTP/1.1\r\n"
                f"Host: {target}\r\n"
                f"Proxy-Authorization: Basic {AUTH}\r\n"
                f"Proxy-Connection: Keep-Alive\r\n"
                f"\r\n"
            ).encode()
            upstream.sendall(req)
            resp = b""
            upstream.settimeout(30)
            while b"\r\n\r\n" not in resp:
                chunk = upstream.recv(4096)
                if not chunk:
                    break
                resp += chunk
            upstream.settimeout(None)
            status_line = resp.split(b"\r\n", 1)[0]
            if b" 200 " not in status_line:
                client.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n" + resp[:500])
                return
            client.sendall(b"HTTP/1.1 200 OK\r\n\r\n")
            t = threading.Thread(target=forward, args=(client, upstream), daemon=True)
            t.start()
            forward(upstream, client)
            t.join(timeout=5)
        else:
            headers_part, _, body = buf.partition(b"\r\n\r\n")
            lines = headers_part.split(b"\r\n")
            new_lines = [lines[0]]
            for h in lines[1:]:
                if h.lower().startswith(b"proxy-authorization:"):
                    continue
                new_lines.append(h)
            new_lines.append(f"Proxy-Authorization: Basic {AUTH}".encode())
            new_buf = b"\r\n".join(new_lines) + b"\r\n\r\n" + body
            upstream.sendall(new_buf)
            t = threading.Thread(target=forward, args=(client, upstream), daemon=True)
            t.start()
            forward(upstream, client)
            t.join(timeout=5)
    except Exception as e:
        print(f"[handle] error: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
    finally:
        for s in (client, upstream):
            try:
                if s is not None:
                    s.close()
            except Exception:
                pass


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", LISTEN_PORT))
    srv.listen(128)
    print(
        f"forward proxy 127.0.0.1:{LISTEN_PORT} -> {UPSTREAM_HOST}:{UPSTREAM_PORT} (auth as {USER})",
        flush=True,
    )
    while True:
        client, _ = srv.accept()
        threading.Thread(target=handle, args=(client,), daemon=True).start()


if __name__ == "__main__":
    main()
