class BasicPollTest(DevdataTestCase):
    def get_original_data(self):
        return [
            {
                "model": "polls.Question",
                "pk": 1,
                "fields": {
                    "question_text": "Test 1",
                    "pub_date": "2021-01-20T16:06:57.948Z",
                },
            },
            {
                "model": "polls.Choice",
                "pk": 1,
                "fields": {
                    "question": 1,
                    "choice_text": "choice 1",
                    "votes": 0,
                },
            },
            {
                "model": "polls.Choice",
                "pk": 2,
                "fields": {
                    "question": 1,
                    "choice_text": "choice 1",
                    "votes": 5,
                },
            },
            {
                "model": "polls.Question",
                "pk": 2,
                "fields": {
                    "question_text": "Test 2",
                    "pub_date": "2021-01-20T16:06:57.948Z",
                },
            },
            {
                "model": "polls.Choice",
                "pk": 3,
                "fields": {
                    "question": 2,
                    "choice_text": "choice 1",
                    "votes": 999,
                },
            },
        ]

    def assert_on_exported_data(self, exported_data):
        assert self._original_pks("polls.Question").issubset(
            self._exported_pks(exported_data, "polls.Question")
        )
        assert self._original_pks("polls.Choice").issubset(
            self._exported_pks(exported_data, "polls.Choice")
        )

    def assert_on_imported_data(self, connection):
        pass
