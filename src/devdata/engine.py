import json

from django.conf import settings
from django.core.management.color import no_style
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connections

from .strategies import Exportable
from .utils import (
    get_all_models,
    migrations_file_path,
    progress,
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


def export_migration_state(django_dbname):
    migrations_file_path().parent.mkdir(parents=True, exist_ok=True)
    with migrations_file_path().open("w") as f:
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


def export_data(django_dbname, only=None, no_update=False):
    model_strategies = sort_model_strategies(settings.DEVDATA_STRATEGIES)
    bar = progress(model_strategies)
    for app_model_label, strategy in bar:
        if only and app_model_label not in only:
            continue

        model = to_model(app_model_label)
        bar.set_postfix(
            {"strategy": "{} ({})".format(app_model_label, strategy.name)}
        )

        if app_model_label in (
            'contenttypes.ContentTypes',
            'auth.Permissions',
        ):
            bar.write(
                "Warning! Exporter {} configured for {} may not import as "
                "Django automatically manages this table. You may get "
                "conflicts. It's recommended that you don't use any strategies "
                "for this table.".format(app_model_label, strategy.name),
            )

        if isinstance(strategy, Exportable):
            strategy.export_data(
                django_dbname, model, no_update, log=bar.write
            )


def import_schema(django_dbname):
    db_conf = settings.DATABASES[django_dbname]
    pg_dbname = db_conf["NAME"]
    pg_user = db_conf.get("USER") if db_conf.get("USER") else "postgres"

    with connections[django_dbname]._nodb_connection.cursor() as cursor:
        cursor.execute("DROP DATABASE IF EXISTS {}".format(pg_dbname))
        cursor.execute(
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
        )
        cursor.execute(
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
        )

    # TODO: import migrations


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
