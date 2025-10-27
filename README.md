# KI-tugas-2

## Encrypted Chat Client (`client2.py`)

This project provides a simple encrypted chat client using DES encryption and HTTP for message relay.

---

## Requirements

- Python 3.x
- `des_traditional.py` module (must be present in the same directory as `client2.py`)

---

## Usage

### 1. Prepare the Environment

- Ensure `client2.py` and `des_traditional.py` are in the same folder.
- Install Python 3 if not already installed.

### 2. Start the Client

Open a terminal in the project directory and run:

```
python client2.py <my_id> [peer_id]
```

- `<my_id>`: Your unique chat ID (required)
- `[peer_id]`: The ID of the person you want to chat with (optional; can be set later)

#### Example:

```
python client2.py alice bob
```

### 3. Commands in Chat

- `/to <peer_id>`: Set or change the peer you want to chat with.
- `/quit`: Exit the chat client.

### 4. How It Works

- Messages are encrypted with DES before sending.
- The client communicates with a relay server (default: `http://127.0.0.1:8001`).
- If the relay server is not running, an embedded server will start locally.

---

## Notes

- You must provide the `des_traditional.py` file with `encrypt_ecb_bytes` and `decrypt_ecb_bytes` functions for encryption to work.
- The client will print both the encrypted and decrypted messages for clarity.

---

## Troubleshooting

- If you see errors about missing `des_traditional.py`, add the required file.
- If the server is unreachable, check your network or firewall settings.

---

## License

MIT
