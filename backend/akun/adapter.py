from allauth.account.adapter import DefaultAccountAdapter


class AdapterAkun(DefaultAccountAdapter):
    def is_open_for_signup(self, request) -> bool:
        return False


def ip_klien(request) -> str:
    # Nginx menimpa X-Real-IP, jadi nilainya tidak bisa dipalsukan dari browser.
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR", "")


def username_axes(request, credentials) -> str | None:
    return (credentials or {}).get("username")
