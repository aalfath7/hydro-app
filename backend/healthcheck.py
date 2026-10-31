import os
import sys
import urllib.request

host = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(",")[0].strip()
permintaan = urllib.request.Request(  # noqa: S310
    "http://127.0.0.1:8000/api/kesehatan/", headers={"Host": host}
)
try:
    with urllib.request.urlopen(permintaan, timeout=4) as respons:  # noqa: S310
        sys.exit(0 if respons.status == 200 else 1)
except OSError:
    sys.exit(1)
