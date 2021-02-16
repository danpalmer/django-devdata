import subprocess

from django.db import connections
from django.conf import settings
from django.core.management.color import no_style

from .utils import (
    psql,
    progress,
    to_model,
    get_all_models,
    schema_file_path,
    to_app_model_label,
    migrations_file_path,
    sort_model_strategies,
    get_pg_connection_args,
)
from .strategies import Exportable


def validate_strategies(only=None):
    not_found = []

    for model in get_all_models():
        if model._meta.abstract:
            continue

        app_model_label = to_app_model_label(model)

        if app_model_label not in settings.DEVDATA_STRATEGIES:
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


def export_schema(django_dbname):
    db_conf = settings.DATABASES[django_dbname]

    schema_file_path().parent.mkdir(exist_ok=True)
    with schema_file_path().open("w") as f:
        export_command = [
            *settings.DEVDATA_PGDUMP_COMMAND.split(),
            db_conf["NAME"],
            "--schema-only",
            "--format=plain",
            *get_pg_connection_args(db_conf),
        ]

        subprocess.run(export_command, stdout=f, check=True)

    migrations_file_path().parent.mkdir(exist_ok=True)
    with migrations_file_path().open("w") as f:
        export_command = [
            *settings.DEVDATA_PGDUMP_COMMAND.split(),
            db_conf["NAME"],
            "--data-only",
            "--table=django_migrations",
            "--format=plain",
            *get_pg_connection_args(db_conf),
        ]

        subprocess.run(export_command, stdout=f, check=True)


def export_data(django_dbname, only=None, no_update=False):
    model_strategies = sort_model_strategies(settings.DEVDATA_STRATEGIES)

    for app_model_label, strategy in progress(model_strategies):
        if only and app_model_label not in only:
            continue

        model = to_model(app_model_label)

        if isinstance(strategy, Exportable):
            print("Exporting {} ({})".format(app_model_label, strategy.name))
            strategy.export(django_dbname, model, no_update)


def sync_schema(django_dbname):
    db_conf = settings.DATABASES[django_dbname]
    pg_dbname = db_conf["NAME"]

    psql("DROP DATABASE IF EXISTS {}".format(pg_dbname), None, db_conf)
    psql(
        """
        CREATE DATABASE {database} WITH
            TEMPLATE = template0
            ENCODING = 'UTF-8'
            LC_COLLATE = 'en_GB.UTF-8'
            LC_CTYPE = 'en_GB.UTF-8'
            OWNER = {owner}
        """.format(
            owner=db_conf.get("USER", "postgres"),
            database=pg_dbname,
        ),
        None,
        db_conf,
    )

    with schema_file_path().open() as f:
        psql(f.read(), pg_dbname, db_conf)

    with migrations_file_path().open() as f:
        psql(f.read(), pg_dbname, db_conf)


def sync_data(django_dbname):
    model_strategies = sort_model_strategies(settings.DEVDATA_STRATEGIES)
    for app_model_label, strategy in model_strategies:
        model = to_model(app_model_label)

        print("Syncing {} ({})".format(app_model_label, strategy.name))
        strategy.sync(django_dbname, model)


def sync_cleanup(django_dbname):
    print("Resetting sequences")
    conn = connections[django_dbname]
    with conn.cursor() as cursor:
        for reset_sql in conn.ops.sequence_reset_sql(
            no_style(),
            get_all_models(),
        ):
            # TODO: Handle Zendesk sequence not starting at 1
            cursor.execute(reset_sql)
