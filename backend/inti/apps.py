from django.apps import AppConfig


class IntiConfig(AppConfig):
    name = "inti"

    def ready(self) -> None:
        from . import skema  # noqa: F401
