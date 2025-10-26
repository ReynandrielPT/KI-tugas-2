import socket
import sys
import json
import threading
import os
import time
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from des_traditional import encrypt_ecb_bytes, decrypt_ecb_bytes

KEY = b'8bytekey' 
SERVER_DEFAULT = 'http://127.0.0.1:8001'

def http_post_json(url: str, obj: dict) -> tuple[int, bytes]:
    """Kirim POST dan kembalikan (status_code, body_bytes)"""
    data = json.dumps(obj).encode('utf-8')
    req = Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    with urlopen(req) as resp:
        return resp.getcode(), resp.read()

def http_get(url: str) -> tuple[int, bytes]:
    """Kirim GET dan kembalikan (status_code, body_bytes)"""
    req = Request(url, method='GET')
    with urlopen(req) as resp:
        return resp.getcode(), resp.read()

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
                forwarded = {
                    'from': payload['from'], 
                    'msg': cipher_hex,
                    'type': payload.get('type', 'text'),
                    'size': payload.get('size', 0)
                }
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
            return  
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle, args=(conn, addr), daemon=True)
            t.start()


def start_embedded_server_if_needed(base_url: str):
    global _embedded_started
    if _embedded_started:
        return
    try:
        status, _ = http_get(base_url + f"/recv?client=__probe__&wait=0")
        if status in (200, 204, 400):
            _embedded_started = True  
            return
    except Exception:
        pass
    parsed = urlparse(base_url)
    host = '127.0.0.1'
    port = int(parsed.port or (443 if parsed.scheme == 'https' else 80))
    try:
        threading.Thread(target=_embedded_server_loop, args=(host, port), daemon=True).start()
        _embedded_started = True
        print(f"[info] Embedded relay started on http://{host}:{port}")
    except Exception as e:
        print(f"[warn] Failed to start embedded relay: {e}")


def usage():
    print(
        "Usage: python chat_simple.py <my_id> [peer_id]\n\n"
        "  <my_id>    ID Anda (wajib)\n"
        "  [peer_id]  ID teman bicara Anda (opsional, bisa diatur nanti)\n"
        "\nCommands:\n"
        "  /to <peer_id>   Mengatur target teman bicara\n"
        "  /quit             Keluar dari chat\n"
    )

def main():
    base = SERVER_DEFAULT
    args = sys.argv[1:]

    if len(args) < 1:
        usage()
        return
    
    my_id = args[0]
    peer_id = args[1] if len(args) >= 2 else None

    start_embedded_server_if_needed(base)
    
    print(f"[info] Using my_id={my_id}")
    if peer_id:
        print(f"[info] Peer set to {peer_id}")
    else:
        try:
            initial_peer = input("[setup] Enter peer id to chat (press Enter to just listen): ").strip()
            if initial_peer:
                peer_id = initial_peer
                print(f"[info] Peer set to {peer_id}")
        except (EOFError, KeyboardInterrupt):
            pass 

    try:
        status, _ = http_get(base + f"/recv?client={my_id}&wait=0")
        if status in (200, 204):
            print(f"[info] Server reachable at {base} (HTTP {status}).")
        else:
            print(f"[warn] Server responded with HTTP {status}; continuing to listen.")
    except Exception as e:
        print(f"[warn] Server not reachable ({e}); will keep listening and retry.")

    stop_flag = {'stop': False}

    def receiver_loop():
        while not stop_flag['stop']:
            try:
                status, body = http_get(base + f"/recv?client={my_id}&wait=30")
            except Exception as e:
                if not stop_flag['stop']:
                    print(f"[recv] error: {e}")
                time.sleep(1)
                continue
            
            if status == 200:
                try:
                    payload = json.loads(body.decode('utf-8'))
                except Exception as e:
                    print(f"[recv] invalid JSON: {e}")
                    continue
                
                cipher_hex = payload.get('msg') or payload.get('cipher') or ''
                print(f"\n[recv] Encrypted (from {payload.get('from')}): {cipher_hex}")
                try:
                    pt = decrypt_ecb_bytes(bytes.fromhex(cipher_hex), KEY)
                    print("[recv] Decrypted:", pt.decode('utf-8', errors='replace'))
                except Exception as e:
                    print(f"[recv] decrypt error: {e}")
            
            elif status == 204:
                pass
            else:
                print(f"[recv] HTTP {status}")

    t = threading.Thread(target=receiver_loop, daemon=True)
    t.start()
    
    print("[chat] Type messages and press Enter. Use /to <peer>, /quit")
    
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
            print("[chat] Quitting...")
            return
        
        if line.lower().startswith('/to '):
            peer_id = line.split(None, 1)[1].strip()
            print(f"[chat] Peer set to {peer_id}")
            continue
        
        if not peer_id:
            print("[chat] Set a peer first: /to <peer_id>")
            continue
        
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
        
        try:
            status, body = http_post_json(base + '/send', payload)
            if status == 200:
                print(f"[send] Server response: OK ({body.decode('utf-8')})")
            else:
                print(f"[send] Server error: HTTP {status} ({body.decode('utf-8')})")
        except Exception as e:
            print(f"[send] Error: {e}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[exit] Interrupted by user.")
        try:
            sys.exit(0)
        except SystemExit:
            pass