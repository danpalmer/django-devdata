from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest
from django.db import connections
from django.db.migrations.recorder import MigrationRecorder
from polls.models import Choice, Question
from pytest_django import DjangoDbBlocker
from test_infrastructure import DevdataTestBase, ExportedData, TestObject
from test_infrastructure.utils import assert_ran_successfully, run_command

from devdata.reset_modes import MODES, Reset


class TestPollsBasic(DevdataTestBase):
    def get_original_data(self) -> list[TestObject]:
        return [
            {
                "model": "polls.Question",
                "strategy": "default",
                "pk": 101,
                "fields": {
                    "question_text": "Test 1",
                    "pub_date": "2021-01-20T16:06:57.948Z",
                },
            },
            {
                "model": "polls.Choice",
                "strategy": "default",
                "pk": 101,
                "fields": {
                    "question_id": 101,
                    "choice_text": "choice 1",
                    "votes": 0,
                },
            },
            {
                "model": "polls.Choice",
                "strategy": "default",
                "pk": 102,
                "fields": {
                    "question_id": 101,
                    "choice_text": "choice 1",
                    "votes": 5,
                },
            },
            {
                "model": "polls.Question",
                "strategy": "default",
                "pk": 102,
                "fields": {
                    "question_text": "Test 2",
                    "pub_date": "2021-01-20T16:06:57.948Z",
                },
            },
            {
                "model": "polls.Choice",
                "strategy": "default",
                "pk": 103,
                "fields": {
                    "question_id": 102,
                    "choice_text": "choice 1",
                    "votes": 999,
                },
            },
        ]

    def assert_on_exported_data(self, exported_data: ExportedData) -> None:
        orig_questions = self.original_pks("polls.Question")
        exported_questions = self.exported_pks(exported_data, "polls.Question")
        assert orig_questions.issubset(exported_questions)

        orig_choices = self.original_pks("polls.Choice")
        exported_choices = self.exported_pks(exported_data, "polls.Choice")
        assert orig_choices.issubset(exported_choices)

    def assert_on_imported_data(self) -> None:
        assert sorted(
            Question.objects.values_list("question_text", flat=True),
        ) == ["Test 1", "Test 2"]
        assert Choice.objects.count() == 3
        assert Question.objects.get(pk=101).choice_set.count() == 2

    @pytest.mark.parametrize(
        "reset_mode",
        [x for x in MODES.keys() if x != "none"],
    )
    def test_import_over_existing_data(
        self,
        reset_mode: Reset,
        test_data_dir: Path,
        default_export_data: None,
        django_db_blocker: DjangoDbBlocker,
        ensure_migrations_table: None,
    ) -> None:
        self.dump_data_for_import(self.get_original_data(), test_data_dir)

        question = Question.objects.create(
            question_text="Do you like jam?",
            pub_date=datetime.datetime.now(datetime.timezone.utc),
        )
        Choice.objects.create(
            question=question,
            choice_text="Yes",
            votes=2,
        )
        Choice.objects.create(
            pk=103,  # conflicts with data to be imported
            question=question,
            choice_text="No",
            votes=2,
        )

        recorder = MigrationRecorder(connections["default"])
        recorder.record_applied("fake-app", "0001-fake-migration")
        assert recorder.applied_migrations().keys() == {
            ("fake-app", "0001-fake-migration"),
        }

        # Ensure all database connections are closed before we attempt to import
        # as this will need to drop the database.
        for connection in connections.all():
            connection.close()

        # Run the import
        process = run_command(
            "devdata_import",
            test_data_dir.name,
            "--no-input",
            f"--reset-mode={reset_mode}",
        )
        assert_ran_successfully(process)

        # Unblock the database so that we can resume accessing it. This will be
        # a different actual database on disk at this point, as the import will
        # have recreated it. We do this before assertions so that we've
        # restored database access for later tests if needed.
        with django_db_blocker.unblock():
            self.assert_on_imported_data()

        recorder = MigrationRecorder(connections["default"])
        assert recorder.applied_migrations().keys() == {
            ("auth", "0001_initial"),
        }

    def test_import_over_existing_data_reset_mode_none(
        self,
        test_data_dir: Path,
        default_export_data: None,
        django_db_blocker: DjangoDbBlocker,
        ensure_migrations_table: None,
    ) -> None:
        self.dump_data_for_import(self.get_original_data(), test_data_dir)

        # A slightly extended migration history to explore conflicts & overwriting
        (test_data_dir / "migrations.json").write_text(
            json.dumps(
                [
                    {
                        "app": "auth",
                        "name": "0001_initial",
                        "applied": "2023-01-01T12:00:00.000Z",
                    },
                    {
                        "app": "exported_only",
                        "name": "0001_initial",
                        "applied": "2023-01-01T12:00:00.000Z",
                    },
                ],
            ),
        )

        question = Question.objects.create(
            question_text="Do you like jam?",
            pub_date=datetime.datetime.now(datetime.timezone.utc),
        )
        Choice.objects.create(
            question=question,
            choice_text="Yes",
            votes=2,
        )
        Choice.objects.create(
            pk=103,  # conflicts with data to be imported
            question=question,
            choice_text="No",
            votes=2,
        )

        recorder = MigrationRecorder(connections["default"])
        recorder.record_applied("fake-app", "0001-fake-migration")
        recorder.record_applied("auth", "0001_initial")
        assert sorted(recorder.migration_qs.values_list("app", "name")) == [
            ("auth", "0001_initial"),
            ("fake-app", "0001-fake-migration"),
        ]

        # Ensure all database connections are closed before we attempt to import
        # as this will need to drop the database.
        for connection in connections.all():
            connection.close()

        # Run the import
        process = run_command(
            "devdata_import",
            test_data_dir.name,
            "--no-input",
            "--reset-mode=none",
        )
        assert_ran_successfully(process)

        # Unblock the database so that we can resume accessing it. This will be
        # a different actual database on disk at this point, as the import will
        # have recreated it. We do this before assertions so that we've
        # restored database access for later tests if needed.
        with django_db_blocker.unblock():
            assert sorted(
                Question.objects.values_list("question_text", flat=True),
            ) == ["Do you like jam?", "Test 1", "Test 2"]
            assert Choice.objects.count() == 4
            assert Question.objects.get(pk=101).choice_set.count() == 2

        recorder = MigrationRecorder(connections["default"])
        assert sorted(recorder.migration_qs.values_list("app", "name")) == [
            # Note: we end up with `auth.0001_initial` in the migrations table
            # twice as the model has no unique constraint and this is pretty
            # much what the user asked for -- that we import the new data over
            # the top.
            ("auth", "0001_initial"),
            ("auth", "0001_initial"),
            ("exported_only", "0001_initial"),
            ("fake-app", "0001-fake-migration"),
        ]
