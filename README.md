# Sistem Komunikasi Server-Client (Python)

Repositori ini berisi sistem komunikasi sederhana antara server dan client menggunakan protokol HTTP berbasis socket di Python. Sistem ini dapat digunakan untuk mengirim pesan terenkripsi antar client melalui server relay.

## Penjelasan Singkat

- **server.py**: Program server relay yang menerima pesan dari client dan menyimpannya sementara, lalu mengirimkan pesan tersebut ke client tujuan saat diminta.
- **client.py**: Program client yang dapat mengirim dan menerima pesan ke/dari client lain melalui server relay. Mendukung mode chat, pengiriman file, dan enkripsi pesan (DES).

## Setup & Persiapan

1. **Pastikan Python 3 sudah terinstal di komputer Anda.**

   - Download di: [python.org/downloads](https://www.python.org/downloads/)

2. **Pastikan semua file (`server.py`, `client.py`, dll) berada dalam satu folder.**

3. **Setup cryptography:**
   - Untuk enkripsi DES, pastikan file `des_traditional.py` tersedia di folder yang sama.

## Cara Menjalankan Server dan Client

1. **Jalankan server:**

   ```
   python server.py
   ```

   Server akan berjalan di `localhost:8080` dan siap menerima koneksi client.

2. **Buka terminal baru, jalankan client:**

   ```
   python client.py join <id_tujuan> [id_sendiri]
   ```

   Contoh:

   ```
   python client.py join user2 user1
   ```

   Atau untuk mode sederhana:

   ```
   python client.py user2
   ```

## Skenario: Komunikasi Berdasarkan IP (ID = IP Address)

Selain menggunakan ID berupa nama, Anda juga bisa menggunakan alamat IP sebagai ID client. Ini berguna untuk komunikasi antar komputer dalam satu jaringan.

### Kirim pesan ke IP tertentu:

```
python client.py sendip <server_ip|url> <ip_tujuan> <pesan>
```

Contoh:

```
python client.py sendip 192.168.1.10 192.168.1.20 "Halo dari user A"
```

### Terima pesan dengan ID berupa IP sendiri:

```
python client.py recvip <server_ip|url> <ip_sendiri>
```

Contoh:

```
python client.py recvip 192.168.1.10 192.168.1.20
```

### Catatan:

- Anda bisa mengganti ID client dengan alamat IP, baik saat join, host, maupun listen.
- Untuk komunikasi lintas komputer, pastikan IP server dan client saling terhubung dalam jaringan yang sama.

3. **Kirim pesan:**

   - Ketik pesan lalu tekan Enter.
   - Gunakan perintah `/to <id_client>` untuk ganti tujuan, `/quit` untuk keluar.

4. **Terima pesan:**
   - Client akan otomatis menerima pesan yang dikirim ke ID-nya.

## Catatan Penting

- Jalankan server terlebih dahulu sebelum client.
- Pastikan port 8080 tidak diblokir firewall.
- Untuk komunikasi antar komputer, pastikan IP server diakses oleh client (ubah URL server dengan argumen `--server`).
- Anda bisa menggunakan IP address sebagai ID client agar lebih mudah komunikasi antar komputer.
- Untuk detail mode lain, jalankan `python client.py` tanpa argumen untuk melihat bantuan.

---

**Kontributor:**

- ReynandrielPT
- Amtsal99
