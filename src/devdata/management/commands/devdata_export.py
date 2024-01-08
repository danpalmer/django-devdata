from __future__ import annotations

import argparse
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db.utils import DEFAULT_DB_ALIAS

from ...engine import (
    export_data,
    export_migration_state,
    export_extras,
    validate_strategies,
)


class Command(BaseCommand):
    help = "Export data for creating a new database."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "dest",
            nargs=argparse.OPTIONAL,
            help="Export destination",
            default="./devdata",
            type=Path,
        )
        parser.add_argument(
            "only",
            nargs=argparse.ZERO_OR_MORE,
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

    def handle(
        self,
        *,
        dest: Path,
        only: list[str],
        database: str,
        no_update: bool,
        **options: object,
    ) -> None:
        try:
            for app_model_label in only:
                apps.get_model(app_model_label, require_ready=False)
        except LookupError as e:
            raise CommandError(e) from e

        try:
            validate_strategies(only)
        except AssertionError as e:
            raise CommandError(e)

        dest_dir = (Path.cwd() / dest).absolute()

        export_migration_state(database, dest_dir)
        export_data(database, dest_dir, only, no_update)
        export_extras(database, dest_dir)
