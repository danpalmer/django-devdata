from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from django.conf import settings as django_settings
from django.utils.module_loading import import_string

from .extras import ExtraImport
from .types import Anonymiser
from .utils import get_all_models, to_app_model_label

if TYPE_CHECKING:
    from .strategies import Strategy

T = TypeVar("T")

DEFAULT_FIELD_ANONYMISERS: dict[str, Anonymiser] = {}
DEFAULT_MODEL_ANONYMISERS: dict[str, dict[str, Anonymiser]] = {}
DEFAULT_FAKER_LOCALES = ["en_US"]


def import_strategy(strategy: tuple[str, dict[str, Any]] | T) -> T:
    try:
        klass_path, kwargs = strategy  # type: ignore[misc]
        klass = import_string(klass_path)
        return klass(**kwargs)
    except (ValueError, TypeError, IndexError):
        return strategy  # type: ignore[return-value]


class Settings:
    @property
    def strategies(self) -> dict[str, list[Strategy]]:
        model_strategies = django_settings.DEVDATA_STRATEGIES

        ret: dict[str, list[Strategy]] = {}

        for model in get_all_models():
            if model._meta.abstract:
                continue

            app_model_label = to_app_model_label(model)  # type: ignore[arg-type]  # mypy can't see that models are hashable

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
    def extra_strategies(self) -> list[ExtraImport]:
        return [
            import_strategy(x)
            for x in getattr(django_settings, "DEVDATA_EXTRA_STRATEGIES", ())
        ]

    @property
    def field_anonymisers(self) -> dict[str, Anonymiser]:
        return getattr(
            django_settings,
            "DEVDATA_FIELD_ANONYMISERS",
            DEFAULT_FIELD_ANONYMISERS,
        )

    @property
    def model_anonymisers(self) -> dict[str, dict[str, Anonymiser]]:
        return getattr(
            django_settings,
            "DEVDATA_MODEL_ANONYMISERS",
            DEFAULT_MODEL_ANONYMISERS,
        )

    @property
    def faker_locales(self) -> list[str]:
        return getattr(
            django_settings, "DEVDATA_FAKER_LOCALES", DEFAULT_FAKER_LOCALES
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(django_settings, name)


settings = Settings()
