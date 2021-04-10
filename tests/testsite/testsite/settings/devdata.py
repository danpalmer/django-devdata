"""
devdata settings for tests.
"""

from devdata.strategies import (
    ExactQuerySetStrategy,
    LatestSampleQuerySetStrategy,
    QuerySetStrategy,
    RandomSampleQuerySetStrategy,
)

from ..custom_strategies import InternalUsersStrategy

DEVDATA_FIELD_ANONYMISERS = {}
DEVDATA_MODEL_ANONYMISERS = {}

DEVDATA_FAKER_LOCALES = ["en_GB", "de"]

DEVDATA_STRATEGIES = {
    "admin.LogEntry": [
        QuerySetStrategy(name="default"),
    ],
    "auth.Permission": [
        QuerySetStrategy(name="default"),
    ],
    "auth.Group_permissions": [
        QuerySetStrategy(name="default"),
    ],
    "auth.Group": [
        QuerySetStrategy(name="default"),
    ],
    "auth.User_groups": [
        QuerySetStrategy(name="default"),
    ],
    "auth.User_user_permissions": [
        QuerySetStrategy(name="default"),
    ],
    "contenttypes.ContentType": [
        QuerySetStrategy(name="default"),
    ],
    "sessions.Session": [
        QuerySetStrategy(name="default"),
    ],
    # Polls is a very basic import/export example.
    "polls.Question": [
        QuerySetStrategy(name="default"),
    ],
    "polls.Choice": [
        QuerySetStrategy(name="default"),
    ],
    # Photofeed is used to demonstrate restricted exports and anonymising of
    # user data. In particular, we customise the users exported to restrict the
    # photos and likes exported.
    "photofeed.Photo": [
        QuerySetStrategy(name="default"),
    ],
    "photofeed.Like": [
        LatestSampleQuerySetStrategy(
            name="latest", count=2, order_by="-created"
        ),
    ],
    "photofeed.View": [
        RandomSampleQuerySetStrategy(name="latest", count=2),
    ],
    "auth.User": [
        InternalUsersStrategy(name="internal"),
        ExactQuerySetStrategy(name="test_users", pks=(100, 101, 102)),
    ],
}
