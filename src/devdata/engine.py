import json

from django.core.management import call_command
from django.core.management.color import no_style
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connections

from .settings import settings
from .strategies import DeleteFirstQuerySetStrategy, Exportable
from .utils import (
    disable_migrations,
    get_all_models,
    migrations_file_path,
    nodb_cursor,
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


def export_migration_state(django_dbname, dest):
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


def export_data(django_dbname, dest, only=None, no_update=False):
    model_strategies = sort_model_strategies(settings.strategies)
    bar = progress(model_strategies)
    for app_model_label, strategy in bar:
        if only and app_model_label not in only:
            continue

        model = to_model(app_model_label)
        bar.set_postfix(
            {"strategy": "{} ({})".format(app_model_label, strategy.name)}
        )

        if (
            app_model_label
            in (
                "contenttypes.ContentTypes",
                "auth.Permissions",
            )
            and not isinstance(strategy, DeleteFirstQuerySetStrategy)
        ):
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


def import_schema(src, django_dbname):
    db_conf = settings.DATABASES[django_dbname]
    pg_dbname = db_conf["NAME"]

    connection = connections[django_dbname]

    with nodb_cursor(connection) as cursor:
        cursor.execute("DROP DATABASE IF EXISTS {}".format(pg_dbname))

        creator = connection.creation
        creator._execute_create_test_db(
            cursor,
            {
                "dbname": pg_dbname,
                "suffix": creator.sql_table_creation_suffix(),
            },
        )

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

    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO django_migrations (app, name, applied)
            VALUES (%s, %s, %s)
            """,
            [(x["app"], x["name"], x["applied"]) for x in migrations],
        )


def import_data(src, django_dbname):
    model_strategies = sort_model_strategies(settings.strategies)
    bar = progress(model_strategies)
    for app_model_label, strategy in bar:
        model = to_model(app_model_label)
        bar.set_postfix(
            {"strategy": "{} ({})".format(app_model_label, strategy.name)}
        )
        strategy.import_data(django_dbname, src, model)


def import_cleanup(src, django_dbname):
    conn = connections[django_dbname]
    with conn.cursor() as cursor:
        for reset_sql in conn.ops.sequence_reset_sql(
            no_style(),
            get_all_models(),
        ):
            cursor.execute(reset_sql)
