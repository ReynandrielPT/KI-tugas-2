import socket
import sys
import json
import threading
from des_traditional import encrypt_ecb_bytes, decrypt_ecb_bytes

KEY = b'8bytekey'

def handle_client_connection(conn, addr):
    print(f"\n[info] Connection received from {addr}")
    try:
        data = b''
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(1024)
            if not chunk:
                break
            data += chunk
        
        header_part, _, rest = data.partition(b"\r\n\r\n")
        
        print("\n--- RAW HTTP REQUEST (HEADERS) ---")
        print(header_part.decode('utf-8', 'ignore'))
        print("----------------------------------")
        
        headers = {}
        try:
            lines = header_part.decode('utf-8').split('\r\n')
            for line in lines[1:]:
                if ':' in line:
                    k, v = line.split(':', 1)
                    headers[k.strip().lower()] = v.strip()
        except Exception as e:
            print(f"[warn] Could not parse headers: {e}")

        length = int(headers.get('content-length', '0'))
        
        body_part = rest
        while len(body_part) < length:
            chunk = conn.recv(length - len(body_part))
            if not chunk:
                break
            body_part += chunk

        print("\n--- RAW HTTP REQUEST (BODY) ---")
        print(body_part.decode('utf-8', 'ignore'))
        print("-------------------------------")

        payload = json.loads(body_part.decode('utf-8'))
        cipher_hex = payload.get('cipher')
        
        if not cipher_hex:
            raise ValueError("No 'cipher' in JSON body")

        print(f"\nEncrypted (hex): {cipher_hex}")
        
        decrypted_bytes = decrypt_ecb_bytes(bytes.fromhex(cipher_hex), KEY)
        decrypted_text = decrypted_bytes.decode('utf-8')
        
        print(f"Decrypted: {decrypted_text}")
        print("> ", end="", flush=True)

        response_body = b'{"status": "OK"}'
        response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Connection: close\r\n"
            b"Content-Length: " + str(len(response_body)).encode() + b"\r\n"
            b"\r\n"
        ) + response_body
        conn.sendall(response)

    except Exception as e:
        print(f"\n[error] Failed to process request: {e}")
        print("> ", end="", flush=True)
        try:
            response = b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n"
            conn.sendall(response)
        except Exception:
            pass
    finally:
        conn.close()

def run_listener(listen_port):
    host = '0.0.0.0'
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, listen_port))
            s.listen(5)
            print(f"[info] Listener started on {host}:{listen_port}. Ready to receive messages.")
            while True:
                conn, addr = s.accept()
                handler_thread = threading.Thread(
                    target=handle_client_connection,
                    args=(conn, addr),
                    daemon=True
                )
                handler_thread.start()
    except Exception as e:
        print(f"\n[fatal] Listener failed: {e}. Quitting.")
    except KeyboardInterrupt:
        pass

def run_sender(peer_ip, peer_port, message):
    print(f"\n[info] Sending to {peer_ip}:{peer_port}...")
    
    encrypted_bytes = encrypt_ecb_bytes(message.encode('utf-8'), KEY)
    cipher_hex = encrypted_bytes.hex()
    
    print(f"Plaintext: {message}")
    print(f"Encrypted (hex): {cipher_hex}")
    
    body = json.dumps({"cipher": cipher_hex})
    body_bytes = body.encode('utf-8')

    request_lines = [
        f"POST / HTTP/1.1",
        f"Host: {peer_ip}:{peer_port}",
        "Content-Type: application/json",
        f"Content-Length: {len(body_bytes)}",
        "Connection: close",
        "\r\n" + body
    ]
    http_request = "\r\n".join(request_lines)
    
    print("\n--- FULL HTTP REQUEST TO BE SENT ---")
    print(http_request)
    print("------------------------------------")

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((peer_ip, peer_port))
            s.sendall(http_request.encode('utf-8'))
            
            response = s.recv(4096)
            print("\n--- RAW RESPONSE FROM PEER ---")
            print(response.decode('utf-8', errors='ignore'))
            print("--------------------------------")
            
    except socket.timeout:
        print(f"\n[error] Connection to {peer_ip}:{peer_port} timed out.")
    except ConnectionRefusedError:
        print(f"\n[error] Connection refused by {peer_ip}:{peer_port}.")
    except Exception as e:
        print(f"\n[error] Failed to send message: {e}")

def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <your_listen_port>")
        sys.exit(1)

    try:
        my_port = int(sys.argv[1])
    except ValueError:
        print("[error] Port must be a number.")
        sys.exit(1)

    listener_thread = threading.Thread(
        target=run_listener,
        args=(my_port,),
        daemon=True
    )
    listener_thread.start()

    peer_ip, peer_port = None, None
    print("\n[info] Type '/quit' to exit.")
    print("[info] Set peer before sending: /to <ip>:<port>")

    while True:
        try:
            line = input("> ").strip()
            if not line:
                continue
            
            if line.lower() == '/quit':
                print("[info] Shutting down.")
                break
            
            if line.lower().startswith('/to '):
                try:
                    _, target = line.split(None, 1)
                    peer_ip, port_str = target.split(':')
                    peer_port = int(port_str)
                    print(f"[info] Peer set to {peer_ip}:{peer_port}")
                except Exception:
                    print("[error] Invalid format. Use: /to 127.0.0.1:8080")
            
            elif not peer_ip or not peer_port:
                print("[error] Peer not set. Use: /to <ip>:<port> first.")
            
            else:
                run_sender(peer_ip, peer_port, line)

        except (EOFError, KeyboardInterrupt):
            print("\n[info] Shutting down.")
            break

if __name__ == "__main__":
    main()