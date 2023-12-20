"""
Alternative implementations for ensuring a clean database before import.
"""

import abc

from django.db import connections
from django.db.migrations.recorder import MigrationRecorder

from .settings import settings
from .utils import nodb_cursor

MODES = {}


class Reset(abc.ABC):
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        MODES[cls.slug] = cls()

    @property
    @abc.abstractclassmethod
    def slug(self) -> str:
        raise NotImplementedError

    @property
    def requires_confirmation(self) -> bool:
        return True

    @property
    @abc.abstractclassmethod
    def description_for_confirmation(self) -> str:
        raise NotImplementedError

    def reset_database(self, django_dbname: str) -> None:
        raise NotImplementedError

    def __str__(self) -> str:
        # Use the slug as the str for easier integration into the CLI
        return self.slug


class DropDatabaseReset(Reset):
    """
    Drop the entire database and re-create it using Django's test utils.

    This is suitable in cases where Django is configured with a database
    superuser account, which is likely to be the case in local development.
    """

    slug = "drop-database"

    description_for_confirmation = "delete the database"

    def reset_database(self, django_dbname: str) -> None:
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


class DropTablesReset(Reset):
    """
    Drop all the tables which Django knows about.

    This is suitable in cases where the current state of the database can be
    assumed to be similar enough to the new state that removing the tables alone
    is sufficient to clear out the data. For databases which support other forms
    of data (e.g: Postgres sequences decoupled from tables) this mode will not
    touch those data and the user must ensure they are handled suitably.

    This is expected to be useful in cases where Django is configured with
    administrative privileges within a database, but may not have access to drop
    the entire database.
    """

    slug = "drop-tables"

    description_for_confirmation = "delete all tables in the database"

    def reset_database(self, django_dbname: str) -> None:
        connection = connections[django_dbname]

        with connection.cursor() as cursor:
            table_names = connection.introspection.table_names(cursor)

            models = connection.introspection.installed_models(table_names)

            if MigrationRecorder(connection).has_table():
                models.add(MigrationRecorder.Migration)

            with connection.schema_editor() as editor:
                for model in models:
                    editor.delete_model(model)


class NoReset(Reset):
    """
    Perform no resetting against the database.

    This is suitable in cases where the user has already manually configured the
    target database or otherwise wants more control over the setup. The user is
    responsible for ensuring that the database is in a state ready to have the
    schema migrated into it.
    """

    slug = "none"

    requires_confirmation = False

    description_for_confirmation = ""

    def reset_database(self, django_dbname: str) -> None:
        pass
