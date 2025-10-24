# KI-tugas-2 — Encrypted relay chat (DES/ECB)

This repo contains a simple relay server and a Python client that can send/receive messages and files encrypted with DES (ECB) for educational purposes.

- Relay endpoints: `POST /send` and `GET /recv?client=<id>&wait=<secs>`
- Client encrypts/decrypts with `des_traditional.py` using an 8-byte key
- Interactive chat and one-shot send/recv modes are supported

Note: DES in ECB mode is not secure for real-world use. This project is for learning/demo only.

## Prerequisites

- Python 3.8+ (Windows PowerShell commands are shown)
- No external Python packages required
- Optional: a C++ compiler if you want to build `DES.cpp` (MinGW-w64 g++ or MSVC)

## Project structure

- `server.py` — HTTP-like relay over raw sockets, stores messages in memory
- `client.py` — chat client with DES encryption; can also start an embedded relay if the remote server is unreachable
- `des_traditional.py` — classic DES implementation (ECB + PKCS#5 padding)
- `DES.cpp` — interactive C++ program demonstrating DES
- `legacy_http.py` — a tiny legacy HTTP helper (not used by `server.py`)

## Quick start (local)

1. Start the relay server (optional; the client can auto-start an embedded relay if nothing is reachable):

```powershell
python .\server.py 127.0.0.1 8080
```

2. Open another terminal and start a chat client (join a peer IP; will ping once):

```powershell
# Treats the single argument as peer id/IP; pings it once
python .\client.py 192.168.1.50
```

- If the ping succeeds, chat proceeds.
- If the ping fails, the client idles in listen mode. Set a peer later with `/to <peer_id>`.

3. Or run two terminals to chat locally through the relay:

```powershell
# Terminal A
python .\client.py --server http://127.0.0.1:8080 host Alice

# Terminal B
python .\client.py --server http://127.0.0.1:8080 join Alice Bob
```

Type a message and press Enter to send. Use `/quit` to exit.

## Running the relay server

```powershell
# Listen on all interfaces (not recommended on shared networks)
python .\server.py 0.0.0.0 8080

# Listen on localhost only (recommended for local testing)
python .\server.py 127.0.0.1 8080
```

- Logs are printed to console and appended to `server.log`.
- Messages are stored in memory; they are lost if the server restarts.

## Client usage

The client provides several modes. If `--server` is omitted, it uses the default base in the code and will try to start an embedded relay on localhost if unreachable.

### Interactive chat modes

```powershell
# Host (optionally specify my id)
python .\client.py [--server URL] host [my_id]

# Join a peer (peer id required, optionally specify my id)
python .\client.py [--server URL] join <peer_id> [my_id]

# Convenience: single argument behaves like join <peer_id>
python .\client.py <peer_id>
```

While running:

- Type a message and press Enter to send
- Commands in the prompt:
  - `/to <peer_id>` — set/change the peer you send to
  - `/sendfile <path>` — send a file (saved under `./received/` on the receiver)
  - `/quit` — exit the chat

### Passive listening (long poll)

```powershell
python .\client.py [--server URL] listen [my_id]
```

### One-shot send/receive

```powershell
# Send one message from <from> to <to>
python .\client.py [--server URL] send <from> <to> <message>

# Receive one message (waits up to 30s)
python .\client.py [--server URL] recv <client_id>
```

### IP shortcuts

```powershell
# Send: auto-detect sender IP towards the server, to receiver_ip
python .\client.py sendip <server_ip|url> <receiver_ip> <message>

# Receive: poll for messages addressed to own_ip
python .\client.py recvip <server_ip|url> <own_ip>
```

## Embedded relay behavior

- The client probes the server base. If unreachable, it automatically starts a minimal embedded relay on `127.0.0.1:<port>` (port inferred from the base URL).
- This lets you run the client without manually starting `server.py`.

## Peer reachability (ping fallback)

- When you pass a peer that looks like an IPv4 (e.g., `192.168.1.23`) in `host/join` or the one-argument shortcut, the client pings the peer once:
  - If ping succeeds: chat proceeds
  - If ping fails: the client idles in listen mode; you can set a peer later with `/to <peer_id>`

## File transfer

- Use `/sendfile <path>` in the chat to send a file. The receiver saves it under `./received/` with the original filename.
- Files are encrypted as bytes with DES (ECB) using the same key as text messages.

## Encryption details

- Key: defined in `client.py` as `KEY = b'8bytekey'` (8 bytes). Sender and receiver must use the same key.
- Mode: DES in ECB with PKCS#5 padding (educational, not secure for production).
- Implementation: `des_traditional.py` matches classical DES tables.

## Build and run the C++ DES demo (optional)

Using MinGW-w64 g++:

```powershell
# compile
g++ -std=c++11 -O2 -o des.exe .\DES.cpp

# run
.\des.exe
```

Using MSVC (Developer Command Prompt):

```powershell
cl /EHsc DES.cpp
DES.exe
```

## Troubleshooting

- Windows Firewall may block inbound connections to the relay; for local testing, bind to `127.0.0.1`.
- If `recv` returns HTTP 204, there are no queued messages.
- If messages don’t decrypt correctly, ensure both sides use the same 8-byte key in `client.py`.
- If you don’t start `server.py` and the client can’t reach the default base, it should auto-start an embedded relay on localhost and continue.

## License / Notes

This code is intended for coursework/learning. DES/ECB must not be used for real security.
