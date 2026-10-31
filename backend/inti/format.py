from decimal import ROUND_HALF_UP, Decimal

SEN = Decimal("0.01")


def bulatkan(nilai: Decimal) -> Decimal:
    return nilai.quantize(SEN, rounding=ROUND_HALF_UP)


def rupiah(nilai: Decimal | int | None) -> str:
    angka = Decimal(nilai or 0)
    desimal = 2 if angka != angka.to_integral_value() else 0
    teks = f"{angka:,.{desimal}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"Rp {teks}"


def stok_teks(botol: int, isi_terbesar: int, nama_terbesar: str) -> str:
    """Contoh: 2888 botol dengan dus isi 24 menjadi `120 dus 8 botol`."""
    if isi_terbesar <= 1:
        return f"{botol:,} {nama_terbesar or 'botol'}".replace(",", ".")
    utuh, lepas = divmod(botol, isi_terbesar)
    if utuh == 0:
        return f"{lepas} botol"
    teks = f"{utuh:,} {nama_terbesar}".replace(",", ".")
    return f"{teks} {lepas} botol" if lepas else teks
