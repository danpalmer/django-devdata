from base import DevdataTestBase


class TestPollsBasic(DevdataTestBase):
    def get_original_data(self):
        return [
            {
                "model": "polls.Question",
                "pk": 101,
                "fields": {
                    "question_text": "Test 1",
                    "pub_date": "2021-01-20T16:06:57.948Z",
                },
            },
            {
                "model": "polls.Choice",
                "pk": 101,
                "fields": {
                    "question": 101,
                    "choice_text": "choice 1",
                    "votes": 0,
                },
            },
            {
                "model": "polls.Choice",
                "pk": 102,
                "fields": {
                    "question": 101,
                    "choice_text": "choice 1",
                    "votes": 5,
                },
            },
            {
                "model": "polls.Question",
                "pk": 102,
                "fields": {
                    "question_text": "Test 2",
                    "pub_date": "2021-01-20T16:06:57.948Z",
                },
            },
            {
                "model": "polls.Choice",
                "pk": 103,
                "fields": {
                    "question": 102,
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

    def assert_on_imported_data(self, connection):
        pass
