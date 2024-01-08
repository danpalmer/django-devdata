from __future__ import annotations

import json
from collections.abc import Collection
from pathlib import Path

from django.core.management import call_command
from django.core.management.color import no_style
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connections
from django.db.migrations.recorder import MigrationRecorder

from .extras import ExtraExport
from .settings import settings
from .strategies import DeleteFirstQuerySetStrategy, Exportable
from .utils import (
    disable_migrations,
    get_all_models,
    migrations_file_path,
    progress,
    sort_model_strategies,
    to_app_model_label,
    to_model,
)


def validate_strategies(only: Collection[str] = ()) -> None:
    not_found = []

    for model in get_all_models():
        if model._meta.abstract:
            continue

        app_model_label = to_app_model_label(model)  # type: ignore[arg-type]  # mypy can't see that models are hashable

        if app_model_label not in settings.strategies:
            if only and app_model_label not in only:
                continue

            not_found.append(app_model_label)

    if not_found:
        raise AssertionError(
            "\n".join(
                [
                    "Found models without strategies for local database creation:\n",
                    *[
                        "  * {}".format(app_model_label)
                        for app_model_label in not_found
                    ],
                ]
            )
        )


def export_migration_state(django_dbname: str, dest: Path) -> None:
    file_path = migrations_file_path(dest)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w") as f:
        with connections[django_dbname].cursor() as cursor:
            cursor.execute(
                """
                SELECT app, name, applied
                FROM django_migrations
                ORDER BY id ASC
                """
            )
            migration_state = [
                {"app": app, "name": name, "applied": applied}
                for app, name, applied in cursor.fetchall()
            ]
            json.dump(migration_state, f, indent=4, cls=DjangoJSONEncoder)


def export_data(
    django_dbname: str,
    dest: Path,
    only: Collection[str] = (),
    no_update: bool = False,
) -> None:
    model_strategies = sort_model_strategies(settings.strategies)
    bar = progress(model_strategies)
    for app_model_label, strategy in bar:
        if only and app_model_label not in only:
            continue

        model = to_model(app_model_label)
        bar.set_postfix(
            {"strategy": "{} ({})".format(app_model_label, strategy.name)}
        )

        if app_model_label in (
            "contenttypes.ContentTypes",
            "auth.Permissions",
        ) and not isinstance(strategy, DeleteFirstQuerySetStrategy):
            bar.write(
                "Warning! Django auto-creates entries in {} which means there "
                "may be conflicts on import. It's recommended that strategies "
                "for this table inherit from `DeleteFirstQuerySetStrategy` to "
                "ensure the table is cleared out first. This should be safe to "
                "do if imports are done on a fresh database as is "
                "recommended.".format(app_model_label),
            )

        if isinstance(strategy, Exportable):
            strategy.export_data(
                django_dbname, dest, model, no_update, log=bar.write
            )


def export_extras(
    django_dbname: str,
    dest: Path,
    no_update: bool = False,
) -> None:
    bar = progress(settings.extra_strategies)
    for strategy in bar:
        bar.set_postfix({"extra": strategy.name})

        if isinstance(strategy, ExtraExport):
            strategy.export_data(
                django_dbname,
                dest,
                no_update,
                log=bar.write,
            )


def import_schema(src: Path, django_dbname: str) -> None:
    connection = connections[django_dbname]

    with disable_migrations():
        call_command(
            "migrate",
            verbosity=0,
            interactive=False,
            database=django_dbname,
            run_syncdb=True,
            skip_checks=True,
        )

    call_command("createcachetable", database=django_dbname)

    with migrations_file_path(src).open() as f:
        migrations = json.load(f)

    if migrations:
        # Django 4+ doesn't create `django_migrations` table when it detects
        # there aren't any migrations to run (including when using `run_syncdb`
        # as we do above). However since we do actually have data to import we
        # need to force the creation of the table.
        MigrationRecorder(connection).ensure_schema()

    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO django_migrations (app, name, applied)
            VALUES (%s, %s, %s)
            """,
            [(x["app"], x["name"], x["applied"]) for x in migrations],
        )


def import_data(src: Path, django_dbname: str) -> None:
    model_strategies = sort_model_strategies(settings.strategies)
    bar = progress(model_strategies)
    for app_model_label, strategy in bar:
        model = to_model(app_model_label)
        bar.set_postfix(
            {"strategy": "{} ({})".format(app_model_label, strategy.name)}
        )
        strategy.import_data(django_dbname, src, model)


def import_extras(src: Path, django_dbname: str) -> None:
    bar = progress(settings.extra_strategies)
    for strategy in bar:
        bar.set_postfix({"extra": strategy.name})
        strategy.import_data(django_dbname, src)


def import_cleanup(src: Path, django_dbname: str) -> None:
    conn = connections[django_dbname]
    with conn.cursor() as cursor:
        for reset_sql in conn.ops.sequence_reset_sql(
            no_style(),
            get_all_models(),
        ):
            cursor.execute(reset_sql)
