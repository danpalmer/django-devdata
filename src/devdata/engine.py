import subprocess

from django.conf import settings
from django.core.management.color import no_style
from django.db import connections

from .exporting import Exporter
from .strategies import Exportable
from .utils import (
    get_all_models,
    migrations_file_path,
    progress,
    psql,
    schema_file_path,
    sort_model_strategies,
    to_app_model_label,
    to_model,
)


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

    schema_file_path().parent.mkdir(parents=True, exist_ok=True)
    with schema_file_path().open("w") as f:
        export_command = [
            *settings.DEVDATA_PGDUMP_COMMAND.split(),
            db_conf["NAME"],
            "--schema-only",
            "--format=plain",
        ]

        subprocess.run(export_command, stdout=f, check=True)

    migrations_file_path().parent.mkdir(parents=True, exist_ok=True)
    with migrations_file_path().open("w") as f:
        export_command = [
            *settings.DEVDATA_PGDUMP_COMMAND.split(),
            db_conf["NAME"],
            "--data-only",
            "--table=django_migrations",
            "--format=plain",
        ]

        subprocess.run(export_command, stdout=f, check=True)


def export_data(django_dbname, only=None, no_update=False):
    model_strategies = sort_model_strategies(settings.DEVDATA_STRATEGIES)
    with Exporter(settings.DEVDATA_DUMP_COMMAND) as exporter:
        bar = progress(model_strategies)
        for app_model_label, strategy in bar:
            if only and app_model_label not in only:
                continue

            model = to_model(app_model_label)
            bar.set_description(
                "{} ({})".format(app_model_label, strategy.name)
            )

            if isinstance(strategy, Exportable):
                strategy.export_data(
                    django_dbname, model, exporter, no_update, log=bar.write
                )


def import_schema(django_dbname):
    db_conf = settings.DATABASES[django_dbname]
    pg_dbname = db_conf["NAME"]
    pg_user = db_conf.get("USER") if db_conf.get("USER") else "postgres"

    psql("DROP DATABASE IF EXISTS {}".format(pg_dbname), None, db_conf)
    psql(
        """
        DO $do$
            BEGIN
                IF NOT EXISTS (
                    SELECT FROM pg_catalog.pg_roles
                    WHERE  rolname = '{owner}'
                )
                THEN
                    CREATE ROLE {owner} SUPERUSER LOGIN;
                END IF;
            END
        $do$
        """.format(
            owner=pg_user
        ),
        None,
        db_conf,
    )
    psql(
        """
        CREATE DATABASE {database} WITH
            TEMPLATE = template0
            ENCODING = 'UTF-8'
            LC_COLLATE = 'en_GB.UTF-8'
            LC_CTYPE = 'en_GB.UTF-8'
            OWNER = {owner}
        """.format(
            owner=pg_user,
            database=pg_dbname,
        ),
        None,
        db_conf,
    )

    with schema_file_path().open() as f:
        psql(settings.DEVDATA_SQL_FILTER(f.read()), pg_dbname, db_conf)

    with migrations_file_path().open() as f:
        psql(settings.DEVDATA_SQL_FILTER(f.read()), pg_dbname, db_conf)


def import_data(django_dbname):
    model_strategies = sort_model_strategies(settings.DEVDATA_STRATEGIES)
    bar = progress(model_strategies)
    for app_model_label, strategy in bar:
        model = to_model(app_model_label)
        bar.set_description("{} ({})".format(app_model_label, strategy.name))
        strategy.import_data(django_dbname, model)


def import_cleanup(django_dbname):
    conn = connections[django_dbname]
    with conn.cursor() as cursor:
        for reset_sql in conn.ops.sequence_reset_sql(
            no_style(),
            get_all_models(),
        ):
            cursor.execute(reset_sql)
