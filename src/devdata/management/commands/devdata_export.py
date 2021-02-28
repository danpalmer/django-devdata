from django.core.management.base import (
    BaseCommand,
    CommandError,
    CommandParser,
)
from django.db.utils import DEFAULT_DB_ALIAS

from ...engine import export_data, export_schema, validate_strategies


class Command(BaseCommand):
    help = "Export data for creating a new database."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "only",
            nargs="*",
            help="Only export specified models.",
            metavar="app_label.ModelName",
        )
        parser.add_argument(
            "--database",
            help="The database name to export from.",
            default=DEFAULT_DB_ALIAS,
        )
        parser.add_argument(
            "--no-update",
            help="Skip updates that already exist and are non-empty.",
            action="store_true",
        )

    def handle(self, *, only=None, database, no_update, **options):
        try:
            validate_strategies(only)
        except AssertionError as e:
            raise CommandError(e)

        export_schema(database)
        export_data(database, only, no_update)
