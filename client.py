import socket
import sys
import json
from urllib.request import Request, urlopen

# Classic DES implementation (ECB), for educational purposes.
# Includes IP/FP, E, P, S-boxes, PC-1/PC-2, key schedule, 16 rounds.

KEY = b'8bytekey'  # 8-byte DES key (64-bit with parity)
SERVER_DEFAULT = 'http://172.168.100.1:8080'  # default relay server base
BLOCK_SIZE = 8

# Tables
IP = [
    58, 50, 42, 34, 26, 18, 10, 2,
    60, 52, 44, 36, 28, 20, 12, 4,
    62, 54, 46, 38, 30, 22, 14, 6,
    64, 56, 48, 40, 32, 24, 16, 8,
    57, 49, 41, 33, 25, 17, 9, 1,
    59, 51, 43, 35, 27, 19, 11, 3,
    61, 53, 45, 37, 29, 21, 13, 5,
    63, 55, 47, 39, 31, 23, 15, 7,
]

FP = [
    40, 8, 48, 16, 56, 24, 64, 32,
    39, 7, 47, 15, 55, 23, 63, 31,
    38, 6, 46, 14, 54, 22, 62, 30,
    37, 5, 45, 13, 53, 21, 61, 29,
    36, 4, 44, 12, 52, 20, 60, 28,
    35, 3, 43, 11, 51, 19, 59, 27,
    34, 2, 42, 10, 50, 18, 58, 26,
    33, 1, 41, 9, 49, 17, 57, 25,
]

E = [
    32, 1, 2, 3, 4, 5,
    4, 5, 6, 7, 8, 9,
    8, 9, 10, 11, 12, 13,
    12, 13, 14, 15, 16, 17,
    16, 17, 18, 19, 20, 21,
    20, 21, 22, 23, 24, 25,
    24, 25, 26, 27, 28, 29,
    28, 29, 30, 31, 32, 1,
]

P = [
    16, 7, 20, 21,
    29, 12, 28, 17,
    1, 15, 23, 26,
    5, 18, 31, 10,
    2, 8, 24, 14,
    32, 27, 3, 9,
    19, 13, 30, 6,
    22, 11, 4, 25,
]

SBOXES = [
    # S1
    [
        [14, 4, 13, 1, 2, 15, 11, 8, 3, 10, 6, 12, 5, 9, 0, 7],
        [0, 15, 7, 4, 14, 2, 13, 1, 10, 6, 12, 11, 9, 5, 3, 8],
        [4, 1, 14, 8, 13, 6, 2, 11, 15, 12, 9, 7, 3, 10, 5, 0],
        [15, 12, 8, 2, 4, 9, 1, 7, 5, 11, 3, 14, 10, 0, 6, 13],
    ],
    # S2
    [
        [15, 1, 8, 14, 6, 11, 3, 4, 9, 7, 2, 13, 12, 0, 5, 10],
        [3, 13, 4, 7, 15, 2, 8, 14, 12, 0, 1, 10, 6, 9, 11, 5],
        [0, 14, 7, 11, 10, 4, 13, 1, 5, 8, 12, 6, 9, 3, 2, 15],
        [13, 8, 10, 1, 3, 15, 4, 2, 11, 6, 7, 12, 0, 5, 14, 9],
    ],
    # S3
    [
        [10, 0, 9, 14, 6, 3, 15, 5, 1, 13, 12, 7, 11, 4, 2, 8],
        [13, 7, 0, 9, 3, 4, 6, 10, 2, 8, 5, 14, 12, 11, 15, 1],
        [13, 6, 4, 9, 8, 15, 3, 0, 11, 1, 2, 12, 5, 10, 14, 7],
        [1, 10, 13, 0, 6, 9, 8, 7, 4, 15, 14, 3, 11, 5, 2, 12],
    ],
    # S4
    [
        [7, 13, 14, 3, 0, 6, 9, 10, 1, 2, 8, 5, 11, 12, 4, 15],
        [13, 8, 11, 5, 6, 15, 0, 3, 4, 7, 2, 12, 1, 10, 14, 9],
        [10, 6, 9, 0, 12, 11, 7, 13, 15, 1, 3, 14, 5, 2, 8, 4],
        [3, 15, 0, 6, 10, 1, 13, 8, 9, 4, 5, 11, 12, 7, 2, 14],
    ],
    # S5
    [
        [2, 12, 4, 1, 7, 10, 11, 6, 8, 5, 3, 15, 13, 0, 14, 9],
        [14, 11, 2, 12, 4, 7, 13, 1, 5, 0, 15, 10, 3, 9, 8, 6],
        [4, 2, 1, 11, 10, 13, 7, 8, 15, 9, 12, 5, 6, 3, 0, 14],
        [11, 8, 12, 7, 1, 14, 2, 13, 6, 15, 0, 9, 10, 4, 5, 3],
    ],
    # S6
    [
        [12, 1, 10, 15, 9, 2, 6, 8, 0, 13, 3, 4, 14, 7, 5, 11],
        [10, 15, 4, 2, 7, 12, 9, 5, 6, 1, 13, 14, 0, 11, 3, 8],
        [9, 14, 15, 5, 2, 8, 12, 3, 7, 0, 4, 10, 1, 13, 11, 6],
        [4, 3, 2, 12, 9, 5, 15, 10, 11, 14, 1, 7, 6, 0, 8, 13],
    ],
    # S7
    [
        [4, 11, 2, 14, 15, 0, 8, 13, 3, 12, 9, 7, 5, 10, 6, 1],
        [13, 0, 11, 7, 4, 9, 1, 10, 14, 3, 5, 12, 2, 15, 8, 6],
        [1, 4, 11, 13, 12, 3, 7, 14, 10, 15, 6, 8, 0, 5, 9, 2],
        [6, 11, 13, 8, 1, 4, 10, 7, 9, 5, 0, 15, 14, 2, 3, 12],
    ],
    # S8
    [
        [13, 2, 8, 4, 6, 15, 11, 1, 10, 9, 3, 14, 5, 0, 12, 7],
        [1, 15, 13, 8, 10, 3, 7, 4, 12, 5, 6, 11, 0, 14, 9, 2],
        [7, 11, 4, 1, 9, 12, 14, 2, 0, 6, 10, 13, 15, 3, 5, 8],
        [2, 1, 14, 7, 4, 10, 8, 13, 15, 12, 9, 0, 3, 5, 6, 11],
    ],
]

PC1 = [
    57, 49, 41, 33, 25, 17, 9,
    1, 58, 50, 42, 34, 26, 18,
    10, 2, 59, 51, 43, 35, 27,
    19, 11, 3, 60, 52, 44, 36,
    63, 55, 47, 39, 31, 23, 15,
    7, 62, 54, 46, 38, 30, 22,
    14, 6, 61, 53, 45, 37, 29,
    21, 13, 5, 28, 20, 12, 4,
]

PC2 = [
    14, 17, 11, 24, 1, 5,
    3, 28, 15, 6, 21, 10,
    23, 19, 12, 4, 26, 8,
    16, 7, 27, 20, 13, 2,
    41, 52, 31, 37, 47, 55,
    30, 40, 51, 45, 33, 48,
    44, 49, 39, 56, 34, 53,
    46, 42, 50, 36, 29, 32,
]

SHIFTS = [1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1]


def bytes_to_bits(b: bytes) -> list:
    bits = []
    for byte in b:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def bits_to_bytes(bits: list) -> bytes:
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        out.append(byte)
    return bytes(out)


def permute(bits: list, table: list) -> list:
    # Table indices are 1-based
    return [bits[i - 1] for i in table]


def left_rotate(lst: list, n: int) -> list:
    return lst[n:] + lst[:n]


def xor_bits(a: list, b: list) -> list:
    return [i ^ j for i, j in zip(a, b)]


def sbox_substitution(bits48: list) -> list:
    out = []
    for i in range(8):
        block = bits48[i * 6:(i + 1) * 6]
        row = (block[0] << 1) | block[5]
        col = (block[1] << 3) | (block[2] << 2) | (block[3] << 1) | block[4]
        val = SBOXES[i][row][col]
        # 4-bit to bits
        out.extend([(val >> 3) & 1, (val >> 2) & 1, (val >> 1) & 1, val & 1])
    return out


def feistel(right32: list, subkey48: list) -> list:
    expanded = permute(right32, E)
    xored = xor_bits(expanded, subkey48)
    sboxed = sbox_substitution(xored)
    return permute(sboxed, P)


def generate_subkeys(key8: bytes) -> list:
    key_bits = bytes_to_bits(key8)
    key56 = permute(key_bits, PC1)
    c = key56[:28]
    d = key56[28:]
    subkeys = []
    for shift in SHIFTS:
        c = left_rotate(c, shift)
        d = left_rotate(d, shift)
        cd = c + d
        subkeys.append(permute(cd, PC2))
    return subkeys


def des_block_encrypt(block8: bytes, subkeys: list) -> bytes:
    bits = bytes_to_bits(block8)
    bits = permute(bits, IP)
    l = bits[:32]
    r = bits[32:]
    for i in range(16):
        f = feistel(r, subkeys[i])
        l, r = r, xor_bits(l, f)
    # combine R then L (swap) before FP
    preoutput = r + l
    out_bits = permute(preoutput, FP)
    return bits_to_bytes(out_bits)


def des_block_decrypt(block8: bytes, subkeys: list) -> bytes:
    bits = bytes_to_bits(block8)
    bits = permute(bits, IP)
    l = bits[:32]
    r = bits[32:]
    for i in range(15, -1, -1):
        f = feistel(r, subkeys[i])
        l, r = r, xor_bits(l, f)
    preoutput = r + l
    out_bits = permute(preoutput, FP)
    return bits_to_bytes(out_bits)


def pkcs5_pad(data: bytes) -> bytes:
    pad_len = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    return data + bytes([pad_len] * pad_len)


def pkcs5_unpad(data: bytes) -> bytes:
    if not data:
        return data
    pad_len = data[-1]
    if pad_len < 1 or pad_len > BLOCK_SIZE:
        raise ValueError('Invalid padding length')
    if data[-pad_len:] != bytes([pad_len] * pad_len):
        raise ValueError('Invalid padding bytes')
    return data[:-pad_len]


def des_encrypt_ecb(data: bytes, key8: bytes) -> bytes:
    subkeys = generate_subkeys(key8)
    out = b''
    for i in range(0, len(data), BLOCK_SIZE):
        out += des_block_encrypt(data[i:i + BLOCK_SIZE], subkeys)
    return out


def des_decrypt_ecb(data: bytes, key8: bytes) -> bytes:
    subkeys = generate_subkeys(key8)
    out = b''
    for i in range(0, len(data), BLOCK_SIZE):
        out += des_block_decrypt(data[i:i + BLOCK_SIZE], subkeys)
    return out


def http_post_json(url: str, obj: dict) -> tuple[int, bytes]:
    data = json.dumps(obj).encode('utf-8')
    req = Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    with urlopen(req) as resp:
        return resp.getcode(), resp.read()


def http_get(url: str) -> tuple[int, bytes]:
    req = Request(url, method='GET')
    with urlopen(req) as resp:
        return resp.getcode(), resp.read()


def usage():
    print(
        "Usage:\n"
        "  Sender: python client.py [--server URL] send <client_id> <to_client_id> <message>\n"
        "  Receiver (long poll): python client.py [--server URL] recv <client_id>\n"
        "  Sender by IP: python client.py sendip <server_ip|url> <receiver_ip> <message>\n"
        "  Receiver by IP: python client.py recvip <server_ip|url> <own_ip>\n"
        "Options:\n"
    f"  --server URL    Base URL of relay server (default {SERVER_DEFAULT})\n"
    )


def main():
    # Convenience: allow `python client.py "message..."` to act as
    # send from cli1 -> cli2 using defaults.
    if len(sys.argv) == 2 and sys.argv[1] not in ("send", "recv", "rcv", "--server"):
        sys.argv = [sys.argv[0], "send", "cli1", "cli2", sys.argv[1]]

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
        # Accept raw IP or full URL
        if server_arg.startswith('http://') or server_arg.startswith('https://'):
            return server_arg
        return f"http://{server_arg}:8080"

    def get_local_ip_towards(target_host: str) -> str:
        try:
            host_only = target_host
            if host_only.startswith('http://') or host_only.startswith('https://'):
                # crude parse
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
    if mode == 'send':
        if len(args) < 4:
            usage()
            return
        client_from = args[1]
        client_to = args[2]
        message = ' '.join(args[3:])
        padded = pkcs5_pad(message.encode('utf-8'))
        encrypted = des_encrypt_ecb(padded, KEY)
        print('Plaintext :', message)
        print('Encrypted :', encrypted.hex())
        status, body = http_post_json(base + '/send', {
            'from': client_from,
            'to': client_to,
            'msg': encrypted.hex(),
        })
        print('Server response:', status, body.decode('utf-8') if body else '')
    elif mode == 'recv':
        if len(args) < 2:
            usage()
            return
        client_id = args[1]
        # long poll up to 30 seconds
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
            cipher_hex = payload['msg']
            cipher_bytes = bytes.fromhex(cipher_hex)
            out = des_decrypt_ecb(cipher_bytes, KEY)
            try:
                plain = pkcs5_unpad(out)
            except Exception:
                plain = out
            print('Decrypted  :', plain.decode('utf-8', errors='replace'))
        except Exception as e:
            print('Decrypt error:', e)
    elif mode == 'sendip':
        # Usage: sendip <server_ip|url> <receiver_ip> <message>
        if len(args) < 4:
            usage()
            return
        base = make_base(args[1])
        receiver_ip = args[2]
        message = ' '.join(args[3:])
        sender_id = get_local_ip_towards(base)
        padded = pkcs5_pad(message.encode('utf-8'))
        encrypted = des_encrypt_ecb(padded, KEY)
        print('Plaintext :', message)
        print('From      :', sender_id)
        print('To        :', receiver_ip)
        print('Encrypted :', encrypted.hex())
        status, body = http_post_json(base + '/send', {
            'from': sender_id,
            'to': receiver_ip,
            'msg': encrypted.hex(),
        })
        print('Server response:', status, body.decode('utf-8') if body else '')
    elif mode == 'recvip':
        # Usage: recvip <server_ip|url> <own_ip>
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
            cipher_hex = payload['msg']
            cipher_bytes = bytes.fromhex(cipher_hex)
            out = des_decrypt_ecb(cipher_bytes, KEY)
            try:
                plain = pkcs5_unpad(out)
            except Exception:
                plain = out
            print('Decrypted  :', plain.decode('utf-8', errors='replace'))
        except Exception as e:
            print('Decrypt error:', e)
    else:
        usage()


if __name__ == '__main__':
    main()
