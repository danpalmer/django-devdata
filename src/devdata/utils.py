import functools
import json
import pathlib
import subprocess
from typing import Optional

import tqdm
from django.apps import apps
from django.conf import settings
from django.db.models import Model


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


def get_all_models():
    return apps.get_models(include_auto_created=True)


def psql(command, pg_dbname):
    psql_command = [
        *settings.DEVDATA_PSQL_COMMAND.split(),
        pg_dbname or "postgres",
        "-v",
        "ON_ERROR_STOP=1",
    ]

    try:
        subprocess.run(
            psql_command,
            input=command.encode("utf-8"),
            check=True,
            stdout=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        raise AssertionError("Process failed") from None


def schema_file_path():
    return pathlib.Path(settings.DEVDATA_LOCAL_DIR) / "schema.sql"


def migrations_file_path():
    return pathlib.Path(settings.DEVDATA_LOCAL_DIR) / "migrations.sql"


def progress(sequence):
    return tqdm.tqdm(sequence)


def sort_model_strategies(model_strategies):
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
            for dep in getattr(strategy, "depends_on", ()):
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
def get_exported_pks_for_model(model):
    return [str(x["pk"]) for x in get_exported_objects_for_model(model)]


@functools.lru_cache(maxsize=8)
def get_exported_objects_for_model(model):
    app_model_label = to_app_model_label(model)
    objects = []

    data_dir = pathlib.Path(settings.DEVDATA_LOCAL_DIR) / app_model_label
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
