"""
This file specifies the main testcases for our integration tests. These are not
pytest tests themselves, but rather encode some setup and later assertion for
inclusion in the integration tests.
"""


class DevdataTestCase:
    def get_original_data(self):
        raise NotImplementedError

    def assert_on_exported_data(self, exported_data):
        pass

    def assert_on_imported_data(self, connection):
        pass


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
        pass

    def assert_on_imported_data(self, connection):
        pass


TESTCASES = [
    BasicPollTest(),
]
