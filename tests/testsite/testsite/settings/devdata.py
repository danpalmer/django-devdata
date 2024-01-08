"""
devdata settings for tests.
"""

from __future__ import annotations

from typing import Any

from devdata.strategies import (
    ExactQuerySetStrategy,
    LatestSampleQuerySetStrategy,
    QuerySetStrategy,
    RandomSampleQuerySetStrategy,
)
from devdata.types import Anonymiser

from ..custom_strategies import InternalUsersStrategy

DEVDATA_FIELD_ANONYMISERS: dict[str, Anonymiser] = {}
DEVDATA_MODEL_ANONYMISERS: dict[str, dict[str, Anonymiser]] = {}

DEVDATA_DEFAULT_STRATEGY = QuerySetStrategy(name="default")

DEVDATA_FAKER_LOCALES = ["en_GB", "de"]

DEVDATA_STRATEGIES = {
    ###
    # Important: If updating behaviour here, remember to update
    # `test_infrastructure.base.ALL_TEST_STRATEGIES` which defines which
    # exported files are created for tests.
    ###
    # Admin/Groups system is left to the default, we don't use these for
    # tests.
    # admin.LogEntry
    # auth.Group_permissions
    # auth.Group
    # auth.User_groups
    # auth.User_user_permissions
    ###
    # Content Types can be slightly tricky, we need to be careful to replace any
    # default Django provided entries with our own that have the correct PKs.
    # Same goes for Permission.
    "contenttypes.ContentType": [
        (
            "devdata.strategies.DeleteFirstQuerySetStrategy",
            {"name": "replaced"},
        ),
    ],
    "auth.Permission": [
        (
            "devdata.strategies.DeleteFirstQuerySetStrategy",
            {"name": "replaced"},
        ),
    ],
    ###
    # Do not export sessions, there's little benefit to these, there may be lots
    # of them, and they pose a security risk if not correctly anonymised.
    "sessions.Session": [],
    ###
    # Polls is a very basic import/export example. We leave these to the default
    # strategy.
    # polls.Question
    # polls.Choice
    ###
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

DEVDATA_EXTRA_STRATEGIES: list[tuple[str, dict[str, Any]]] = [
    ("devdata.extras.PostgresSequences", {}),
]
