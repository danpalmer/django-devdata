from __future__ import annotations

import datetime

import pytest
from django.db import connections
from django.db.migrations.recorder import MigrationRecorder
from polls.models import Choice, Question
from test_infrastructure import DevdataTestBase
from test_infrastructure.utils import assert_ran_successfully, run_command

from devdata.reset_modes import MODES


class TestPollsBasic(DevdataTestBase):
    def get_original_data(self):
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

    def assert_on_exported_data(self, exported_data):
        orig_questions = self.original_pks("polls.Question")
        exported_questions = self.exported_pks(exported_data, "polls.Question")
        assert orig_questions.issubset(exported_questions)

        orig_choices = self.original_pks("polls.Choice")
        exported_choices = self.exported_pks(exported_data, "polls.Choice")
        assert orig_choices.issubset(exported_choices)

    def assert_on_imported_data(self):
        assert sorted(
            Question.objects.values_list("question_text", flat=True)
        ) == ["Test 1", "Test 2"]
        assert Choice.objects.count() == 3
        assert Question.objects.get(pk=101).choice_set.count() == 2

    @pytest.mark.parametrize(
        "reset_mode",
        [x for x in MODES.keys() if x != "none"],
    )
    def test_import_over_existing_data(
        self,
        reset_mode,
        test_data_dir,
        default_export_data,
        django_db_blocker,
        ensure_migrations_table,
    ):
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
