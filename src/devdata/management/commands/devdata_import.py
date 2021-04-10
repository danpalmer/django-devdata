import argparse
import socket
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import DEFAULT_DB_ALIAS

from ...engine import (
    import_cleanup,
    import_data,
    import_schema,
    validate_strategies,
)
from ...settings import settings


class Command(BaseCommand):
    help = "Create new database and import data into it."

    def add_arguments(self, parser):
        parser.add_argument(
            "src",
            nargs=argparse.OPTIONAL,
            help="Import source",
            default="./devdata",
        )
        parser.add_argument(
            "--database",
            help="The database name to import to.",
            default=DEFAULT_DB_ALIAS,
        )
        parser.add_argument(
            "--no-input",
            help="Disable confirmations before danger actions.",
            action="store_true",
        )

    def handle(self, src, database, no_input=False, **options):
        try:
            validate_strategies()
        except AssertionError as e:
            raise CommandError(e)

        if not no_input and (
            input(
                "You're about to delete the database {} ({}) from the host {}. "
                "Are you sure you want to continue? [y/N]: ".format(
                    self.style.WARNING(database),
                    self.style.WARNING(settings.DATABASES[database]["NAME"]),
                    self.style.WARNING(socket.gethostname()),
                ),
            ).lower()
            != "y"
        ):
            raise CommandError("Aborted")

        src = (Path.cwd() / src).absolute()

        import_schema(src, database)
        import_data(src, database)
        import_cleanup(src, database)
