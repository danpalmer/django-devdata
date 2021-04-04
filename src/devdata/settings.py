from typing import Any

from django.conf import settings as django_settings
from django.utils.module_loading import import_string

DEFAULT_FIELD_ANONYMISERS = {}
DEFAULT_MODEL_ANONYMISERS = {}
DEFAULT_FAKER_LOCALES = ["en_US"]


class Settings:
    @property
    def strategies(self):
        model_strategies = django_settings.DEVDATA_STRATEGIES

        ret = {}

        for model, strategies in model_strategies.items():
            ret[model] = []
            for strategy in strategies:
                try:
                    klass_path, kwargs = strategy
                    klass = import_string(klass_path)
                    return klass(**kwargs)
                except (ValueError, TypeError, IndexError):
                    ret[model].append(strategy)

        return ret

    @property
    def field_anonymisers(self):
        return getattr(
            django_settings,
            "DEVDATA_FIELD_ANONYMISERS",
            DEFAULT_FIELD_ANONYMISERS,
        )

    @property
    def model_anonymisers(self):
        return getattr(
            django_settings,
            "DEVDATA_MODEL_ANONYMISERS",
            DEFAULT_MODEL_ANONYMISERS,
        )

    @property
    def local_dir(self):
        return django_settings.DEVDATA_LOCAL_DIR

    @property
    def faker_locales(self):
        return getattr(
            django_settings, "DEVDATA_FAKER_LOCALES", DEFAULT_FAKER_LOCALES
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(django_settings, name)


settings = Settings()
