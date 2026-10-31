import type { components } from "./api-types";

type S = components["schemas"];

export type Produk = S["Produk"];
export type Satuan = S["Satuan"];
export type Kategori = S["Kategori"];
export type Harga = S["Harga"];
export type Batch = S["Batch"];
export type Mutasi = S["Mutasi"];
export type BarangMasuk = S["BarangMasuk"];
export type Opname = S["Opname"];
export type Pelanggan = S["Pelanggan"];
export type Transaksi = S["Transaksi"];
export type TransaksiDetail = S["TransaksiDetail"];
export type Retur = S["Retur"];
export type Pengguna = S["Pengguna"];
export type Peran = S["Peran"];
export type LogAktivitas = S["LogAktivitas"];
export type Dasbor = S["Dasbor"];
export type Sesi = S["Sesi"];
export type SesiPengguna = S["SesiPengguna"];
export type BarisPenjualan = S["BarisPenjualan"];
export type BarisTerlaris = S["BarisTerlaris"];
export type BarisStok = S["BarisStok"];
export type BarisPiutang = S["BarisPiutang"];

export type Halaman<T> = { count: number; results: T[] };
export type MetodeBayar = "tunai" | "transfer" | "qris";
