"""
Alternative implementations for ensuring a clean database before import.
"""

import abc

from django.db import connections

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
    slug = "drop"

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


class NoReset(Reset):
    slug = "none"

    requires_confirmation = False

    description_for_confirmation = ""

    def reset_database(self, django_dbname: str) -> None:
        pass
