import socket

from django.conf import settings
from django.db.utils import DEFAULT_DB_ALIAS
from django.core.management.base import BaseCommand, CommandError

from ...engine import sync_data, sync_schema, sync_cleanup, validate_strategies


class Command(BaseCommand):
    help = "Create new database and sync data into it."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            help="The database name to sync.",
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

        sync_schema(database)
        sync_data(database)
        sync_cleanup(database)
