# Hydro

Website internal untuk mencatat produk, stok per batch, pembelian pelanggan, pembayaran, retur, piutang, dan laporan pada perusahaan air minum kemasan.

| Bagian | Isi |
|---|---|
| `backend/` | Django 5.2 LTS, Django REST Framework, aturan bisnis dan hak akses |
| `frontend/` | Next.js statis, TypeScript, Tailwind, shadcn/ui |
| `deploy/` | Nginx, skrip rilis, backup, dan pemulihan |
| `compose.yaml` | Mencoba aplikasi di komputer sendiri dengan satu perintah |
| `compose.prod.yaml` | Produksi: `web`, `api`, `db` |

## Mencoba dengan satu perintah

Hanya butuh Docker:

```bash
docker compose up --build
```

Buka http://localhost:8080. Akun contoh: `pemilik`, `admin`, `gudang`, dengan password `hydro-demo-123`. Akun `pemilik` akan diminta mengaktifkan 2FA.

Hentikan dengan `docker compose down`. Tambahkan `-v` untuk menghapus datanya juga. Mode ini memakai password contoh dan tanpa HTTPS, jadi jangan dipakai untuk produksi.

## Menjalankan untuk development

Butuh Docker, Python 3.13+, dan Node.js 26. Cara ini memberi reload otomatis saat kode diubah.

```bash
docker compose -p hydro-dev -f compose.dev.yaml up -d --wait

cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt     # Linux/macOS: .venv/bin/pip
export DJANGO_DEBUG=1                                  # PowerShell: $env:DJANGO_DEBUG=1
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py isi_demo
.venv/Scripts/python manage.py runserver

cd ../frontend
npm install
npm run dev
```

Buka http://localhost:3000. Akun contoh: `pemilik`, `admin`, `gudang`, dengan password `hydro-demo-123`. Akun `pemilik` akan diminta mengaktifkan 2FA.

Di Windows, PDF nota dan laporan butuh [pustaka GTK/Pango](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html). Fitur lain tetap jalan tanpa pustaka ini, dan image Docker sudah memuatnya.

## Pengujian

```bash
cd backend
.venv/Scripts/ruff check . && .venv/Scripts/ruff format --check .
.venv/Scripts/mypy .
.venv/Scripts/pytest --create-db

cd ../frontend
npm run typecheck
npm run build
```

Setelah API berubah, perbarui tipe TypeScript supaya kedua aplikasi tetap selaras:

```bash
cd backend && .venv/Scripts/python manage.py spectacular --file schema.yaml --fail-on-warn
cd ../frontend && npm run tipe-api
```

## Aturan pencatatan di kode

- Stok hanya berubah lewat `ubah_stok()` di `backend/stok/layanan.py`, dan setiap perubahan menulis `mutasi_stok`.
- Stok disimpan dalam botol per batch. Database menolak sisa minus lewat `CHECK (sisa >= 0)`.
- Penjualan mengunci baris batch, lalu mengambil batch kedaluwarsa terdekat (FEFO). Batch kedaluwarsa tidak ikut terjual.
- Harga dan total selalu dihitung di server, lalu disalin ke nota.
- Izin dideklarasikan di tiap view lewat atribut `izin`. View tanpa deklarasi selalu ditolak. Tabel izin ada di `backend/inti/izin.py`.

## Deploy ke VPS

Butuh VPS Ubuntu LTS dengan Docker, Tailscale, `age`, dan `rclone`.

1. Di VPS, salin `compose.prod.yaml` dan folder `deploy/` ke `/opt/hydro`, lalu buat `.env` dari `.env.example` dengan `chmod 600 .env`.
2. Aktifkan HTTPS Tailscale, lalu buat sertifikat. Nginx berjalan sebagai UID 101, jadi kunci harus bisa dibacanya:

   ```bash
   sudo tailscale cert --cert-file deploy/certs/tls.crt --key-file deploy/certs/tls.key hydro.nama-tailnet.ts.net
   sudo chown 101 deploy/certs/tls.key deploy/certs/tls.crt
   sudo chmod 640 deploy/certs/tls.key
   ```

   Sertifikat Tailscale berumur 90 hari, jadi jadwalkan perintah ini setiap bulan lalu `docker compose restart web`.
3. Rilis image dengan tag Git `v1.0.0`. GitHub Actions menjalankan pengujian, memindai image, dan mengirimnya ke GHCR.
4. Jalankan pertama kali:

   ```bash
   docker compose pull
   docker compose up -d db
   docker compose run --rm api python manage.py migrate
   docker compose run --rm -it api python manage.py buat_pemilik NAMA_PEMILIK
   docker compose up -d
   ```

5. Pasang backup harian di cron:

   ```cron
   0 19 * * * cd /opt/hydro && bash deploy/backup.sh >> /var/log/hydro-backup.log 2>&1
   ```

Rilis berikutnya: `bash deploy/rilis.sh 1.1.0`. Skrip ini membuat backup, mengambil image, menjalankan migrasi, lalu menyalakan container baru.

Kalau rilis bermasalah, ubah `APP_VERSION` di `.env` ke versi sebelumnya lalu `docker compose up -d`. Kalau migrasi sudah mengubah database, pulihkan dengan `bash deploy/pulihkan.sh BERKAS.dump.age KUNCI.txt`. Simpan kunci privat `age` di luar VPS, dan uji pemulihan di server lain secara berkala.

## Uji image seperti produksi di komputer lokal

Buat `.env.local` dari `.env.example` dengan `TAILSCALE_IP=127.0.0.1`, `DJANGO_ALLOWED_HOSTS=localhost`, dan `DJANGO_CSRF_TRUSTED_ORIGINS=https://localhost:8443`. Taruh sertifikat uji di `deploy/certs/`, lalu:

```bash
docker compose -p hydro-lokal --env-file .env.local -f compose.prod.yaml -f compose.local.yaml up -d --build
```
