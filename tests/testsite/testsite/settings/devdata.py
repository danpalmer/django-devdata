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
        ("devdata.strategies.QuerySetStrategy", {"name": "default"}),
    ],
    "auth.Permission": [
        ("devdata.strategies.QuerySetStrategy", {"name": "default"}),
    ],
    "auth.Group_permissions": [
        ("devdata.strategies.QuerySetStrategy", {"name": "default"}),
    ],
    "auth.Group": [
        ("devdata.strategies.QuerySetStrategy", {"name": "default"}),
    ],
    "auth.User_groups": [
        ("devdata.strategies.QuerySetStrategy", {"name": "default"}),
    ],
    "auth.User_user_permissions": [
        ("devdata.strategies.QuerySetStrategy", {"name": "default"}),
    ],
    "contenttypes.ContentType": [
        ("devdata.strategies.QuerySetStrategy", {"name": "default"}),
    ],
    "sessions.Session": [
        ("devdata.strategies.QuerySetStrategy", {"name": "default"}),
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
        RandomSampleQuerySetStrategy(name="random", count=2),
    ],
    "auth.User": [
        InternalUsersStrategy(name="internal"),
        ExactQuerySetStrategy(name="test_users", pks=(102,)),
    ],
}
