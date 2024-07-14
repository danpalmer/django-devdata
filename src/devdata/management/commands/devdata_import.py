import argparse
import socket
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import DEFAULT_DB_ALIAS

from ...engine import (
    import_cleanup,
    import_data,
    import_extras,
    import_schema,
    validate_strategies,
)
from ...reset_modes import MODES, DropDatabaseReset, Reset
from ...settings import settings


class Command(BaseCommand):
    help = "Create new database and import data into it."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "src",
            nargs=argparse.OPTIONAL,
            help="Import source",
            default="./devdata",
            type=Path,
        )
        parser.add_argument(
            "--database",
            help="The database name to import to.",
            default=DEFAULT_DB_ALIAS,
        )
        parser.add_argument(
            "--reset-mode",
            choices=MODES.values(),
            type=MODES.__getitem__,
            help="How to ensure the database is empty before importing the new schema (default: %(default)s).",
            default=DropDatabaseReset.slug,
        )
        parser.add_argument(
            "--no-input",
            help="Disable confirmations before danger actions.",
            action="store_true",
        )

    def handle(
        self,
        src: Path,
        database: str,
        reset_mode: Reset,
        no_input: bool = False,
        **options: object
    ) -> None:
        try:
            validate_strategies()
        except AssertionError as e:
            raise CommandError(e)

        if not no_input and (
            input(
                "You're about to {} {} ({}) from the host {}. "
                "Are you sure you want to continue? [y/N]: ".format(
                    reset_mode.description_for_confirmation,
                    self.style.WARNING(database),
                    self.style.WARNING(settings.DATABASES[database]["NAME"]),
                    self.style.WARNING(socket.gethostname()),
                ),
            ).lower()
            != "y"
        ):
            raise CommandError("Aborted")

        reset_mode.reset_database(database)

        src = (Path.cwd() / src).absolute()

        import_schema(src, database)
        import_data(src, database)
        import_extras(src, database)
        import_cleanup(src, database)
