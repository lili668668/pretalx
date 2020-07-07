from django.apps import AppConfig


class OrgaConfig(AppConfig):
    name = "pretalx.orga"

    def ready(self):
        from . import permissions  # noqa
        from . import signals  # noqa
        from .phrases import OrgaPhrases  # noqa


default_app_config = "pretalx.orga.OrgaConfig"
