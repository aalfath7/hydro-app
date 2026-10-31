from rest_framework.authentication import SessionAuthentication


class AutentikasiSesi(SessionAuthentication):
    """Mengembalikan 401 (bukan 403) saat belum login, supaya tampilan bisa membedakannya."""

    def authenticate_header(self, request):
        return "Session"
