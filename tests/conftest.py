import json
import shutil
from pathlib import Path
from typing import Iterator

import pytest
from django.db import connection, connections
from django.db.migrations.recorder import MigrationRecorder

ALL_TEST_STRATEGIES = (
    ("admin.LogEntry", "default"),
    ("auth.Permission", "replaced"),
    ("auth.Group_permissions", "default"),
    ("auth.Group", "default"),
    ("auth.User_groups", "default"),
    ("auth.User_user_permissions", "default"),
    ("contenttypes.ContentType", "replaced"),
    ("sessions.Session", "default"),
    ("polls.Question", "default"),
    ("polls.Choice", "default"),
    ("photofeed.Photo", "default"),
    ("photofeed.Like", "latest"),
    ("photofeed.View", "random"),
    ("turtles.Turtle", "default"),
    ("turtles.World", "default"),
    ("auth.User", "internal"),
    ("auth.User", "test_users"),
)


@pytest.fixture()
def test_data_dir() -> Path:
    return Path(__file__).parent / "test-data-tmp"


@pytest.fixture()
def default_export_data(test_data_dir: Path) -> None:
    # Write out defaults of empty exports for everything first, not all
    # tests will use all models.
    empty_model = json.dumps([])
    for model, strategy in ALL_TEST_STRATEGIES:
        path = test_data_dir / model / f"{strategy}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(empty_model)

    (test_data_dir / "migrations.json").write_text(empty_model)

    (test_data_dir / "postgres-sequences.json").write_text(empty_model)


@pytest.fixture()
def ensure_migrations_table() -> Iterator[None]:
    # Ensure there's an existing django_migrations table, as there would be
    # for a real database.
    for conn in connections.all():
        MigrationRecorder(conn).ensure_schema()

    yield

    # Remove the table at the end of the test, back to how the test database
    # would normally be.
    for conn in connections.all():
        if MigrationRecorder(conn).has_table():
            with conn.schema_editor() as editor:
                editor.delete_model(MigrationRecorder.Migration)


@pytest.fixture(autouse=True)
def cleanup_test_data(test_data_dir: Path) -> Iterator[None]:
    yield
    shutil.rmtree(test_data_dir, ignore_errors=True)


@pytest.fixture()
def cleanup_database() -> Iterator[None]:
    yield

    with connection.cursor() as cursor:
        cursor.execute("DROP SEQUENCE IF EXISTS foo")
