"""
devdata settings for tests.
"""

from devdata.strategies import QuerySetStrategy

from .django import BASE_DIR

DEVDATA_LOCAL_DIR = BASE_DIR / ".." / "test-export"

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
    "auth.User": [
        QuerySetStrategy(name="default"),
    ],
    "contenttypes.ContentType": [
        QuerySetStrategy(name="default"),
    ],
    "sessions.Session": [
        QuerySetStrategy(name="default"),
    ],
    "polls.Question": [
        QuerySetStrategy(name="default"),
    ],
    "polls.Choice": [
        QuerySetStrategy(name="default"),
    ],
}
