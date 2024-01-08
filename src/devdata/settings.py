from __future__ import annotations

from typing import Any

from django.conf import settings as django_settings
from django.utils.module_loading import import_string

from .types import Anonymiser
from .utils import get_all_models, to_app_model_label

DEFAULT_FIELD_ANONYMISERS: dict[str, Anonymiser] = {}
DEFAULT_MODEL_ANONYMISERS: dict[str, dict[str, Anonymiser]] = {}
DEFAULT_FAKER_LOCALES = ["en_US"]


def import_strategy(strategy):
    try:
        klass_path, kwargs = strategy
        klass = import_string(klass_path)
        return klass(**kwargs)
    except (ValueError, TypeError, IndexError):
        return strategy


class Settings:
    @property
    def strategies(self):
        model_strategies = django_settings.DEVDATA_STRATEGIES

        ret = {}

        for model in get_all_models():
            if model._meta.abstract:
                continue

            app_model_label = to_app_model_label(model)

            ret[app_model_label] = []
            strategies = model_strategies.get(app_model_label)

            if strategies is None:
                default_strategy = getattr(
                    django_settings,
                    "DEVDATA_DEFAULT_STRATEGY",
                    None,
                )
                if default_strategy is not None:
                    ret[app_model_label] = [default_strategy]
            else:
                for strategy in strategies:
                    ret[app_model_label].append(
                        import_strategy(strategy),
                    )

        return ret

    @property
    def extra_strategies(self):
        return [
            import_strategy(x)
            for x in getattr(django_settings, "DEVDATA_EXTRA_STRATEGIES", ())
        ]

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
    def faker_locales(self):
        return getattr(
            django_settings, "DEVDATA_FAKER_LOCALES", DEFAULT_FAKER_LOCALES
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(django_settings, name)


settings = Settings()
