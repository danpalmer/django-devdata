from base import DevdataTestBase
from polls.models import Choice, Question


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
        assert Question.objects.count() == 2
        assert Choice.objects.count() == 3
        assert Question.objects.get(pk=101).choice_set.count() == 2
