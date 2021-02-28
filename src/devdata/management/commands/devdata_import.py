import socket

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import DEFAULT_DB_ALIAS

from ...engine import (
    import_cleanup,
    import_data,
    import_schema,
    validate_strategies,
)


class Command(BaseCommand):
    help = "Create new database and import data into it."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            help="The database name to import to.",
            default=DEFAULT_DB_ALIAS,
        )

    def handle(self, database, **options):
        try:
            validate_strategies()
        except AssertionError as e:
            raise CommandError(e)

        if (
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

        import_schema(database)
        import_data(database)
        import_cleanup(database)
