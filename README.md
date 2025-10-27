# Simple Encrypted Chat

* Python 3.x
* File `client2.py`
* File `des_traditional.py` (tool enkripsi dan dekripsi)

## Cara Penggunaan

Buka **dua terminal** di folder yang sama.

### 1. Terminal 1 (Klien Pertama, cth: "clientA")

Jalankan ini dulu. Klien ini akan otomatis menjadi server relay.
```bash
python client2.py clientA
````
  * Saat ditanya `[setup] Enter peer id to chat...`, tekan **Enter** saja.
  * Biarkan terminal ini terbuka.

### 2\. Terminal 2 (Klien Kedua, cth: "clientB")

Jalankan di terminal baru, dengan target "clientA".

```bash
# Format: python chat_simple.py <ID_SAYA> <ID_TEMAN>
python chat_simple.py clientB clientA
```
  * Terminal ini sekarang bisa langsung mengirim pesan ke "clientA".

### 3\. Mengobrol

  * **Dari clientB ke clientA:**

      * Di **Terminal 2 (clientB)**, ketik `Halo clientA!` lalu Enter.
      * Pesan akan muncul di **Terminal 1 (clientA)**.

  * **Dari clientA ke clientB:**

      * Di **Terminal 1 (clientA)**, ketik `/to clientB` lalu Enter (untuk mengatur target).
      * Sekarang ketik `Halo clientB!` lalu Enter.
      * Pesan akan muncul di **Terminal 2 (clientB)**.

## Perintah

  * `/to <id_client>`: Mengatur siapa penerima pesan.
  * `/quit`: Keluar dari chat.

---

**Kontributor:**

- ReynandrielPT
- Amtsal99

