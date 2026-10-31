from drf_spectacular.extensions import OpenApiAuthenticationExtension


class SkemaAutentikasiSesi(OpenApiAuthenticationExtension):
    target_class = "inti.autentikasi.AutentikasiSesi"
    name = "cookieAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "apiKey", "in": "cookie", "name": "sessionid"}
