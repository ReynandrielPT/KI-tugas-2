import socket
import sys
import json
import threading
import os
import time
import mimetypes
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from des_traditional import encrypt_ecb_bytes, decrypt_ecb_bytes

KEY = b'8bytekey'  # 8-byte DES key (64-bit with parity)
SERVER_DEFAULT = 'http://172.168.100.1:8080'  # default relay server base



def http_post_json(url: str, obj: dict) -> tuple[int, bytes]:
    data = json.dumps(obj).encode('utf-8')
    req = Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    with urlopen(req) as resp:
        return resp.getcode(), resp.read()


def http_get(url: str) -> tuple[int, bytes]:
    req = Request(url, method='GET')
    with urlopen(req) as resp:
        return resp.getcode(), resp.read()


def http_post_json_verbose(base: str, path: str, obj: dict) -> dict:
    # Returns dict with request_text, response_text, status, body
    body_bytes = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    headers = {
        'Host': urlparse(base).netloc,
        'Content-Type': 'application/json',
        'Content-Length': str(len(body_bytes)),
        'Connection': 'close',
    }
    req_text = render_http('POST', path, headers, body_bytes)
    url = base.rstrip('/') + path
    req = Request(url, data=body_bytes, headers={'Content-Type': 'application/json'}, method='POST')
    with urlopen(req) as resp:
        status = resp.getcode()
        reason = getattr(resp, 'reason', '') or ''
        resp_headers = {k: v for k, v in resp.getheaders()}
        resp_body = resp.read()
    resp_text = render_http_response(status, reason, resp_headers, resp_body)
    return {'request_text': req_text, 'response_text': resp_text, 'status': status, 'body': resp_body}


def http_get_verbose(base: str, path: str) -> dict:
    headers = {
        'Host': urlparse(base).netloc,
        'Connection': 'close',
    }
    req_text = render_http('GET', path, headers, b'')
    url = base.rstrip('/') + path
    req = Request(url, method='GET')
    with urlopen(req) as resp:
        status = resp.getcode()
        reason = getattr(resp, 'reason', '') or ''
        resp_headers = {k: v for k, v in resp.getheaders()}
        resp_body = resp.read()
    resp_text = render_http_response(status, reason, resp_headers, resp_body)
    return {'request_text': req_text, 'response_text': resp_text, 'status': status, 'body': resp_body}


# ---------------- Embedded lightweight relay server (optional) ---------------- #
_embedded_started = False


def _embedded_parse_request(conn):
    data = b''
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(4096)
        if not chunk:
            break
        data += chunk
    header_part, _, rest = data.partition(b"\r\n\r\n")
    lines = header_part.decode('iso-8859-1', errors='replace').split('\r\n')
    if not lines or ' ' not in lines[0]:
        return '', '', '', {}, b'', data
    method, path, version = (lines[0].split(' ') + ['',''])[:3]
    headers = {}
    for line in lines[1:]:
        if ':' in line:
            k, v = line.split(':', 1)
            headers[k.strip().lower()] = v.strip()
    length = int(headers.get('content-length', '0') or '0')
    body = rest
    while len(body) < length:
        chunk = conn.recv(4096)
        if not chunk:
            break
        body += chunk
    raw = header_part + b"\r\n\r\n" + body[:length]
    return method, path, version, headers, body[:length], raw


def _embedded_send_response(conn, status, reason, headers, body):
    hdrs = dict(headers or {})
    hdrs.setdefault('Content-Length', str(len(body or b'')))
    hdrs.setdefault('Connection', 'close')
    lines = [f"HTTP/1.1 {status} {reason}\r\n"]
    for k, v in hdrs.items():
        lines.append(f"{k}: {v}\r\n")
    lines.append("\r\n")
    try:
        conn.sendall(''.join(lines).encode('iso-8859-1') + (body or b''))
    except Exception:
        pass


def _embedded_server_loop(host: str, port: int):
    import threading as _th
    from urllib.parse import urlparse as _urlparse, parse_qs as _parse_qs
    inboxes: dict[str, list[dict]] = {}
    cond = _th.Condition()

    def enqueue(recipient: str, payload: dict):
        with cond:
            inboxes.setdefault(recipient, []).append(payload)
            cond.notify_all()

    def dequeue(recipient: str):
        with cond:
            q = inboxes.get(recipient, [])
            if q:
                return q.pop(0)
            return None

    def handle(conn, addr):
        try:
            method, path, version, headers, body, raw = _embedded_parse_request(conn)
            if not method:
                _embedded_send_response(conn, 400, 'Bad Request', {'Content-Type': 'text/plain'}, b'')
                return
            parsed = _urlparse(path)
            if method == 'POST' and parsed.path == '/send':
                try:
                    payload = json.loads(body.decode('utf-8'))
                except Exception:
                    _embedded_send_response(conn, 400, 'Bad Request', {'Content-Type': 'text/plain'}, b'')
                    return
                if not {'from','to'}.issubset(payload.keys()):
                    _embedded_send_response(conn, 400, 'Bad Request', {'Content-Type': 'text/plain'}, b'')
                    return
                cipher_hex = payload.get('cipher') or payload.get('msg')
                if not isinstance(cipher_hex, str):
                    _embedded_send_response(conn, 400, 'Bad Request', {'Content-Type': 'text/plain'}, b'')
                    return
                forwarded = {'from': payload['from'], 'msg': cipher_hex}
                for k in ('type','filename','mimetype','size'):
                    if k in payload:
                        forwarded[k] = payload[k]
                enqueue(payload['to'], forwarded)
                resp = json.dumps({'queued': True}).encode('utf-8')
                _embedded_send_response(conn, 200, 'OK', {'Content-Type': 'application/json', 'Content-Length': str(len(resp))}, resp)
                return
            if method == 'GET' and parsed.path == '/recv':
                qs = _parse_qs(parsed.query or '')
                client_id = (qs.get('client') or [''])[0]
                wait_param = (qs.get('wait') or ['0'])[0]
                try:
                    wait_secs = max(0, min(60, int(wait_param)))
                except ValueError:
                    wait_secs = 0
                if not client_id:
                    _embedded_send_response(conn, 400, 'Bad Request', {'Content-Type': 'text/plain'}, b'')
                    return
                msg = dequeue(client_id)
                if msg is None and wait_secs > 0:
                    with cond:
                        cond.wait(timeout=wait_secs)
                    msg = dequeue(client_id)
                if msg is None:
                    _embedded_send_response(conn, 204, 'No Content', {'Content-Type': 'text/plain'}, b'')
                    return
                resp = json.dumps(msg).encode('utf-8')
                _embedded_send_response(conn, 200, 'OK', {'Content-Type': 'application/json', 'Content-Length': str(len(resp))}, resp)
                return
            _embedded_send_response(conn, 404, 'Not Found', {'Content-Type': 'text/plain'}, b'')
        finally:
            try:
                conn.close()
            except Exception:
                pass

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            s.listen(5)
        except Exception:
            return  # likely already running elsewhere
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle, args=(conn, addr), daemon=True)
            t.start()


def start_embedded_server_if_needed(base_url: str):
    global _embedded_started
    if _embedded_started:
        return
    try:
        # Probe
        res = http_get_verbose(base_url, f"/recv?client=__probe__&wait=0")
        # If reachable, do not start embedded
        if res['status'] in (200, 204, 400):
            _embedded_started = True  # mark checked to avoid repeated probes
            return
    except Exception:
        pass
    # Start local embedded server on the same port (bind localhost)
    parsed = urlparse(base_url)
    host = '127.0.0.1'
    port = int(parsed.port or (443 if parsed.scheme == 'https' else 80))
    try:
        threading.Thread(target=_embedded_server_loop, args=(host, port), daemon=True).start()
        _embedded_started = True
        print(f"[info] Embedded relay started on http://{host}:{port}")
    except Exception as e:
        print(f"[warn] Failed to start embedded relay: {e}")


def render_http(method: str, path: str, headers: dict, body: bytes) -> str:
    lines = [f"{method} {path} HTTP/1.1\r\n"]
    for k, v in headers.items():
        lines.append(f"{k}: {v}\r\n")
    lines.append("\r\n")
    text = ''.join(lines) + (body.decode('utf-8', errors='replace'))
    return text


def render_http_response(status: int, reason: str, headers: dict, body: bytes) -> str:
    status_line = f"HTTP/1.1 {status} {reason or ''}\r\n"
    lines = [status_line]
    for k, v in headers.items():
        lines.append(f"{k}: {v}\r\n")
    lines.append("\r\n")
    text = ''.join(lines) + (body.decode('utf-8', errors='replace'))
    return text


def usage():
    print(
        "Usage:\n"
        "  Sender: python client.py [--server URL] send <client_id> <to_client_id> <message>\n"
        "  Receiver (long poll): python client.py [--server URL] recv <client_id>\n"
        "  Sender by IP: python client.py sendip <server_ip|url> <receiver_ip> <message>\n"
        "  Receiver by IP: python client.py recvip <server_ip|url> <own_ip>\n"
        "\nQuick start chat:\n"
        "  python client.py <peer_ip_or_id>\n"
        "\nPeer chat modes:\n"
        "  Host (listen): python client.py [--server URL] host [my_id]\n"
        "  Join (connect): python client.py [--server URL] join <peer_id> [my_id]\n"
        "    While running: type a message and press Enter to send.\n"
        "    Commands: /to <peer_id>, /sendfile <path>, /quit\n"
        "\nContinuous listening:\n"
        "  Listen (idle until Ctrl+C): python client.py [--server URL] listen [my_id]\n"
        "Options:\n"
    f"  --server URL    Base URL of relay server (default {SERVER_DEFAULT})\n"
    )


def main():
    # Convenience:
    #  - `python client.py <peer>` => join <peer>
    #  - `python client.py <peer> <my_id>` => join <peer> <my_id>
    if len(sys.argv) in (2, 3) and sys.argv[1] not in ("send", "recv", "rcv", "--server", "host", "join", "listen", "sendip", "recvip"):
        if len(sys.argv) == 2:
            peer = sys.argv[1]
            sys.argv = [sys.argv[0], "join", peer]
        else:
            peer = sys.argv[1]
            myid = sys.argv[2]
            sys.argv = [sys.argv[0], "join", peer, myid]

    # Parse optional --server
    base = SERVER_DEFAULT
    args = sys.argv[1:]
    if args and args[0].startswith('--server'):
        flag = args.pop(0)
        if '=' in flag:
            base = flag.split('=', 1)[1]
        else:
            if not args:
                usage()
                return
            base = args.pop(0)

    if len(args) < 1:
        usage()
        return
    mode = args[0]
    if mode == 'rcv':
        mode = 'recv'

    def make_base(server_arg: str) -> str:
        if server_arg.startswith('http://') or server_arg.startswith('https://'):
            return server_arg
        return f"http://{server_arg}:8080"

    def get_local_ip_towards(target_host: str) -> str:
        try:
            host_only = target_host
            if host_only.startswith('http://') or host_only.startswith('https://'):
                host_only = host_only.split('://', 1)[1].split('/', 1)[0].split(':', 1)[0]
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((host_only, 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return 'unknown'

    if mode in ('host', 'join'):
        # Ensure a relay is available (start embedded if remote is unreachable)
        start_embedded_server_if_needed(base)
        my_id = None
        peer_id = None
        if mode == 'host':
            if len(args) >= 2:
                my_id = args[1]
        else:  # join
            if len(args) < 2:
                usage()
                return
            peer_id = args[1]
            if len(args) >= 3:
                my_id = args[2]
        if not my_id:
            my_id = get_local_ip_towards(base)
        print(f"[info] Using my_id={my_id}")
        if peer_id:
            print(f"[info] Peer set to {peer_id}")
        else:
            # Prompt once to allow immediate chatting without /to
            try:
                initial_peer = input("[setup] Enter peer id to chat (press Enter to just listen): ").strip()
                if initial_peer:
                    peer_id = initial_peer
                    print(f"[info] Peer set to {peer_id}")
            except (EOFError, KeyboardInterrupt):
                pass

        # Quick server reachability test (non-blocking)
        try:
            probe = http_get_verbose(base, f"/recv?client={my_id}&wait=0")
            if probe['status'] in (200, 204):
                print(f"[info] Server reachable at {base} (HTTP {probe['status']}).")
            else:
                print(f"[warn] Server responded with HTTP {probe['status']}; continuing to listen.")
        except Exception as e:
            print(f"[warn] Server not reachable ({e}); will keep listening and retry.")

        # Optional: send a small presence/hello packet so the peer sees we are online
        if peer_id:
            try:
                hello = encrypt_ecb_bytes(b"HELLO", KEY).hex()
                payload = { 'from': my_id, 'to': peer_id, 'type': 'presence', 'cipher': hello, 'size': 5 }
                res = http_post_json_verbose(base, '/send', payload)
                print("\n>>> HTTP REQUEST (presence)")
                print(res['request_text'])
                print("<<< HTTP RESPONSE (presence)")
                print(res['response_text'])
            except Exception as e:
                print(f"[warn] Presence send failed: {e}")

        stop_flag = {'stop': False}

        def receiver_loop():
            save_dir = os.path.join(os.getcwd(), 'received')
            os.makedirs(save_dir, exist_ok=True)
            while not stop_flag['stop']:
                try:
                    res = http_get_verbose(base, f"/recv?client={my_id}&wait=30")
                except Exception as e:
                    print(f"[recv] error: {e}")
                    time.sleep(1)
                    continue
                if res['status'] == 200:
                    print("\n<<< HTTP RESPONSE (recv)")
                    print(res['response_text'])
                    try:
                        payload = json.loads(res['body'].decode('utf-8'))
                    except Exception as e:
                        print(f"[recv] invalid JSON: {e}")
                        continue
                    cipher_hex = payload.get('msg') or payload.get('cipher') or ''
                    print(f"[recv] Encrypted (hex): {cipher_hex}")
                    try:
                        pt = decrypt_ecb_bytes(bytes.fromhex(cipher_hex), KEY)
                    except Exception as e:
                        print(f"[recv] decrypt error: {e}")
                        continue
                    mtype = payload.get('type') or 'text'
                    if mtype == 'image':
                        fname = payload.get('filename') or f"received_{int(time.time())}.bin"
                        out_path = os.path.join(save_dir, fname)
                        try:
                            with open(out_path, 'wb') as f:
                                f.write(pt)
                            print(f"[recv] Saved image to {out_path}")
                        except Exception as e:
                            print(f"[recv] save error: {e}")
                    else:
                        try:
                            print("[recv] Decrypted:", pt.decode('utf-8', errors='replace'))
                        except Exception:
                            print("[recv] Decrypted bytes:", pt[:64])
                elif res['status'] == 204:
                    pass
                else:
                    try:
                        print(f"[recv] HTTP {res['status']}\n" + res['response_text'])
                    except Exception:
                        pass

        t = threading.Thread(target=receiver_loop, daemon=True)
        t.start()
        print("[chat] Type messages and press Enter. Use /to <peer>, /sendfile <path>, /quit")
        while True:
            try:
                line = input('> ').strip()
            except (EOFError, KeyboardInterrupt):
                line = '/quit'
            if not line:
                continue
            if line.lower().startswith('/quit'):
                stop_flag['stop'] = True
                t.join(timeout=0.2)
                return
            if line.lower().startswith('/to '):
                peer_id = line.split(None, 1)[1].strip()
                print(f"[chat] Peer set to {peer_id}")
                continue
            if not peer_id:
                print("[chat] Set a peer first: /to <peer_id>")
                continue
            if line.lower().startswith('/sendfile '):
                path = line.split(None, 1)[1].strip().strip('"')
                if not os.path.isfile(path):
                    print(f"[send] File not found: {path}")
                    continue
                with open(path, 'rb') as f:
                    data = f.read()
                cipher = encrypt_ecb_bytes(data, KEY)
                print("[send] Plain bytes:", f"{len(data)} bytes")
                print("[send] Encrypted (hex):", cipher.hex())
                filename = os.path.basename(path)
                mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                payload = {
                    'from': my_id,
                    'to': peer_id,
                    'type': 'image' if mimetype.startswith('image/') else 'file',
                    'filename': filename,
                    'mimetype': mimetype,
                    'cipher': cipher.hex(),
                    'size': len(data),
                }
                res = http_post_json_verbose(base, '/send', payload)
                print("\n>>> HTTP REQUEST (send)")
                print(res['request_text'])
                print("<<< HTTP RESPONSE (send)")
                print(res['response_text'])
                continue
            # Send as text
            data = line.encode('utf-8')
            cipher = encrypt_ecb_bytes(data, KEY)
            print("[send] Plaintext:", line)
            print("[send] Encrypted (hex):", cipher.hex())
            payload = {
                'from': my_id,
                'to': peer_id,
                'type': 'text',
                'cipher': cipher.hex(),
                'size': len(data),
            }
            res = http_post_json_verbose(base, '/send', payload)
            print("\n>>> HTTP REQUEST (send)")
            print(res['request_text'])
            print("<<< HTTP RESPONSE (send)")
            print(res['response_text'])

    elif mode == 'listen':
        # Ensure a relay is available
        start_embedded_server_if_needed(base)
        my_id = args[1] if len(args) >= 2 else None
        if not my_id:
            my_id = get_local_ip_towards(base)
        print(f"[listen] Listening as {my_id} on {base}. Press Ctrl+C to disconnect.")
        save_dir = os.path.join(os.getcwd(), 'received')
        os.makedirs(save_dir, exist_ok=True)
        try:
            while True:
                try:
                    res = http_get_verbose(base, f"/recv?client={my_id}&wait=30")
                except Exception as e:
                    print(f"[listen] error: {e}")
                    time.sleep(1)
                    continue
                if res['status'] == 200:
                    print("\n<<< HTTP RESPONSE (recv)")
                    print(res['response_text'])
                    try:
                        payload = json.loads(res['body'].decode('utf-8'))
                    except Exception as e:
                        print(f"[listen] invalid JSON: {e}")
                        continue
                    cipher_hex = payload.get('msg') or payload.get('cipher') or ''
                    print(f"[listen] Encrypted (hex): {cipher_hex}")
                    try:
                        pt = decrypt_ecb_bytes(bytes.fromhex(cipher_hex), KEY)
                    except Exception as e:
                        print(f"[listen] decrypt error: {e}")
                        continue
                    mtype = payload.get('type') or 'text'
                    if mtype == 'image':
                        fname = payload.get('filename') or f"received_{int(time.time())}.bin"
                        out_path = os.path.join(save_dir, fname)
                        try:
                            with open(out_path, 'wb') as f:
                                f.write(pt)
                            print(f"[listen] Saved image to {out_path}")
                        except Exception as e:
                            print(f"[listen] save error: {e}")
                    else:
                        print("[listen] Decrypted:", pt.decode('utf-8', errors='replace'))
                elif res['status'] == 204:
                    pass
                else:
                    print(f"[listen] HTTP {res['status']}\n" + res['response_text'])
        except KeyboardInterrupt:
            print("\n[listen] Disconnected.")

    elif mode == 'send':
        if len(args) < 4:
            usage()
            return
        client_from = args[1]
        client_to = args[2]
        message = ' '.join(args[3:])
        encrypted = encrypt_ecb_bytes(message.encode('utf-8'), KEY)
        print('Plaintext :', message)
        print('Encrypted :', encrypted.hex())
        status, body = http_post_json(base + '/send', {
            'from': client_from,
            'to': client_to,
            'cipher': encrypted.hex(),
        })
        print('Server response:', status, body.decode('utf-8') if body else '')

    elif mode == 'recv':
        if len(args) < 2:
            usage()
            return
        client_id = args[1]
        status, body = http_get(base + '/recv?client=' + client_id + '&wait=30')
        print('HTTP status:', status)
        if status == 204:
            print('No message available.')
            return
        if status != 200:
            print('Error:', body.decode('utf-8', errors='ignore'))
            return
        payload = json.loads(body.decode('utf-8'))
        print('Received JSON:', payload)
        try:
            cipher_hex = payload.get('msg') or payload.get('cipher')
            cipher_bytes = bytes.fromhex(cipher_hex)
            plain_bytes = decrypt_ecb_bytes(cipher_bytes, KEY)
            print('Decrypted  :', plain_bytes.decode('utf-8', errors='replace'))
        except Exception as e:
            print('Decrypt error:', e)

    elif mode == 'sendip':
        if len(args) < 4:
            usage()
            return
        base = make_base(args[1])
        receiver_ip = args[2]
        message = ' '.join(args[3:])
        sender_id = get_local_ip_towards(base)
        encrypted = encrypt_ecb_bytes(message.encode('utf-8'), KEY)
        print('Plaintext :', message)
        print('From      :', sender_id)
        print('To        :', receiver_ip)
        print('Encrypted :', encrypted.hex())
        status, body = http_post_json(base + '/send', {
            'from': sender_id,
            'to': receiver_ip,
            'cipher': encrypted.hex(),
        })
        print('Server response:', status, body.decode('utf-8') if body else '')

    elif mode == 'recvip':
        if len(args) < 3:
            usage()
            return
        base = make_base(args[1])
        client_id = args[2]
        status, body = http_get(base + '/recv?client=' + client_id + '&wait=30')
        print('HTTP status:', status)
        if status == 204:
            print('No message available.')
            return
        if status != 200:
            print('Error:', body.decode('utf-8', errors='ignore'))
            return
        payload = json.loads(body.decode('utf-8'))
        print('Received JSON:', payload)
        try:
            cipher_hex = payload.get('msg') or payload.get('cipher')
            cipher_bytes = bytes.fromhex(cipher_hex)
            plain_bytes = decrypt_ecb_bytes(cipher_bytes, KEY)
            print('Decrypted  :', plain_bytes.decode('utf-8', errors='replace'))
        except Exception as e:
            print('Decrypt error:', e)
    else:
        usage()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[exit] Interrupted by user.")
        try:
            sys.exit(0)
        except SystemExit:
            pass
