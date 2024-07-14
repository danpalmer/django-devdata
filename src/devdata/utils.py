from __future__ import annotations

import contextlib
import functools
import itertools
import json
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, Optional, Tuple, TypeVar

import django
import tqdm
from django.apps import apps
from django.conf import settings as django_settings
from django.db.models import Model

if TYPE_CHECKING:
    from .strategies import Strategy

T = TypeVar("T")
TModel = TypeVar("TModel", bound=Model)


@functools.lru_cache(maxsize=1024)
def to_app_model_label(model: Model) -> str:
    return "{}.{}".format(model._meta.app_label, model.__name__)


@functools.lru_cache(maxsize=1024)
def to_model(app_model_label: str) -> Optional[Model]:
    app_label, model_name = app_model_label.split(".")
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        # App is not installed, that's ok.
        return None


def get_all_models() -> list[type[Model]]:
    return apps.get_models(include_auto_created=True)


def migrations_file_path(dir: Path) -> Path:
    return dir / "migrations.json"


def progress(sequence: Iterable[T]) -> tqdm.tqdm[T]:
    return tqdm.tqdm(sequence)


def sort_model_strategies(
    model_strategies: dict[str, list[Strategy]],
) -> list[tuple[str, Strategy]]:
    model_dependencies = []
    models = set()

    for app_model_label, strategies in model_strategies.items():
        model = to_model(app_model_label)
        if not model:
            continue

        models.add(model)

        if hasattr(model, "natural_key"):
            deps = getattr(model.natural_key, "dependencies", [])
            if deps:
                deps = [apps.get_model(dep) for dep in deps]
        else:
            deps = []

        for field in model._meta.fields:
            if field.remote_field and field.remote_field.model != model:
                deps.append(field.remote_field.model)

        for field in model._meta.many_to_many:
            if (
                field.remote_field.through._meta.auto_created
                and field.remote_field.model != model
            ):
                deps.append(field.remote_field.model)

        for strategy in strategies:
            for dep in strategy.depends_on:
                deps.append(to_model(dep))

        model_dependencies.append((model, deps))

    model_dependencies.reverse()

    model_list = []
    while model_dependencies:
        skipped = []
        changed = False
        while model_dependencies:
            model, deps = model_dependencies.pop()

            # If all of the models in the dependency list are either already
            # on the final model list, or not on the original serialization list,
            # then we've found another model with all it's dependencies satisfied.
            if all(d not in models or d in model_list for d in deps):
                model_list.append(model)
                changed = True
            else:
                skipped.append((model, deps))
        if not changed:
            raise RuntimeError(
                "Can't resolve dependencies for {} in serialized app list.".format(
                    ", ".join(
                        "{}.{}".format(
                            model._meta.app_label, model._meta.object_name
                        )
                        for model, _ in sorted(
                            skipped, key=lambda obj: obj[0].__name__
                        )
                    ),
                ),
            )

        model_dependencies = skipped

    return [
        (to_app_model_label(y), x)
        for y in model_list
        for x in model_strategies[to_app_model_label(y)]
    ]


@functools.lru_cache(maxsize=32)
def get_exported_pks_for_model(dest: Path, model: type[Model]) -> list[str]:
    return [
        str(x["pk"])
        for x in get_exported_objects_for_model(dest, model)  # type: ignore[arg-type]  # mypy can't see that models are hashable
    ]


@functools.lru_cache(maxsize=8)
def get_exported_objects_for_model(
    dest: Path,
    model: type[Model],
) -> list[dict[str, Any]]:
    app_model_label = to_app_model_label(model)  # type: ignore[arg-type]  # mypy can't see that models are hashable
    objects = []

    data_dir = dest / app_model_label
    data_files = data_dir.glob("*.json")

    for data_file in data_files:
        with data_file.open() as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print("Invalid file {}".format(data_file))
                raise e

            objects.extend(data)

    return objects


def is_empty_iterator(iterator: Iterator[T]) -> Tuple[Iterator[T], bool]:
    try:
        first = next(iterator)
    except StopIteration:
        empty = True
    else:
        empty = False
        iterator = itertools.chain([first], iterator)

    return (iterator, empty)


@contextlib.contextmanager
def disable_migrations() -> Iterator[None]:
    original_migration_modules = django_settings.MIGRATION_MODULES

    class DisableMigrations:
        def __contains__(self, item: object) -> bool:
            return True

        def __getitem__(self, item: object) -> None:
            return None

    django_settings.MIGRATION_MODULES = DisableMigrations()
    yield
    django_settings.MIGRATION_MODULES = original_migration_modules


def nodb_cursor(connection):  # type: ignore[no-untyped-def]
    if django.VERSION < (3, 1):
        return connection._nodb_connection.cursor()
    else:
        return connection._nodb_cursor()
