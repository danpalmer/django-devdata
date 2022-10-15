import json

import pytest
from django.db import connection, connections
from test_infrastructure import assert_ran_successfully, run_command


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

    def test_export(self, test_data_dir, cleanup_database):
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

    def test_import(self, test_data_dir, default_export_data, cleanup_database):
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
        )
        assert_ran_successfully(process)

        with connection.cursor() as cursor:
            cursor.execute("SELECT nextval('foo')")
            (value,) = cursor.fetchone()
            assert value == 18
