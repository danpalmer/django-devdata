import json
from pathlib import Path

import pytest
from django.db import connection, connections
from test_infrastructure import assert_ran_successfully, run_command

from devdata.reset_modes import MODES, Reset


@pytest.mark.django_db(transaction=True)
class TestPostgresSequences:
    SAMPLE_DATA = {
        "sequencename": "foo",
        "data_type": "bigint",
        "start_value": 6,
        "min_value": 6,
        "max_value": 9223372036854775807,
        "increment_by": 4,
        "cycle": False,
        "cache_size": 1,
        "last_value": 14,
    }

    def test_export(
        self,
        test_data_dir: Path,
        cleanup_database: None,
        ensure_migrations_table: None,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE SEQUENCE foo
                AS bigint
                INCREMENT BY 4
                MINVALUE 6
                """,
            )
            cursor.execute("SELECT nextval('foo')")
            cursor.execute("SELECT nextval('foo')")
            cursor.execute("SELECT nextval('foo')")
            (value,) = cursor.fetchone()
            assert value == 14

        # Run the export
        process = run_command(
            "devdata_export",
            test_data_dir.name,
        )
        assert_ran_successfully(process)

        # Read in the exported data
        exported_data = json.loads(
            (test_data_dir / "postgres-sequences.json").read_text(),
        )

        assert exported_data == [self.SAMPLE_DATA]

    def test_export_unused_sequence(
        self,
        test_data_dir: Path,
        cleanup_database: None,
        ensure_migrations_table: None,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE SEQUENCE foo
                AS bigint
                INCREMENT BY 4
                MINVALUE 6
                """,
            )

        # Run the export
        process = run_command(
            "devdata_export",
            test_data_dir.name,
        )
        assert_ran_successfully(process)

        # Read in the exported data
        exported_data = json.loads(
            (test_data_dir / "postgres-sequences.json").read_text(),
        )

        expected_data = {
            **self.SAMPLE_DATA,
            "last_value": 6,
        }
        assert exported_data == [expected_data]

    @pytest.mark.parametrize("reset_mode", MODES.keys())
    def test_import(
        self,
        reset_mode: Reset,
        test_data_dir: Path,
        default_export_data: None,
        cleanup_database: None,
    ) -> None:
        test_data_dir.mkdir(parents=True, exist_ok=True)
        (test_data_dir / "postgres-sequences.json").write_text(
            json.dumps([self.SAMPLE_DATA]),
        )

        # Ensure all database connections are closed before we attempt to import
        # as this will need to drop the database.
        for conn in connections.all():
            conn.close()

        # Run the import
        process = run_command(
            "devdata_import",
            test_data_dir.name,
            "--no-input",
            f"--reset-mode={reset_mode}",
        )
        assert_ran_successfully(process)

        with connection.cursor() as cursor:
            cursor.execute("SELECT nextval('foo')")
            (value,) = cursor.fetchone()
            assert value == 18

    @pytest.mark.parametrize("reset_mode", MODES.keys())
    def test_import_over_existing_data(
        self,
        reset_mode: Reset,
        test_data_dir: Path,
        default_export_data: None,
        cleanup_database: None,
    ) -> None:
        test_data_dir.mkdir(parents=True, exist_ok=True)
        (test_data_dir / "postgres-sequences.json").write_text(
            json.dumps([self.SAMPLE_DATA]),
        )

        # Create an existing sequence of the same name, but with different properties
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE SEQUENCE foo
                AS bigint
                INCREMENT BY 9
                MINVALUE 2
                """,
            )
            cursor.execute("SELECT nextval('foo')")
            cursor.execute("SELECT nextval('foo')")
            (value,) = cursor.fetchone()
            assert value == 11

        # Ensure all database connections are closed before we attempt to import
        # as this will need to drop the database.
        for conn in connections.all():
            conn.close()

        # Run the import
        process = run_command(
            "devdata_import",
            test_data_dir.name,
            "--no-input",
            f"--reset-mode={reset_mode}",
        )
        assert_ran_successfully(process)

        with connection.cursor() as cursor:
            cursor.execute("SELECT nextval('foo'), nextval('foo')")
            values = cursor.fetchone()
            assert values == (18, 22)
