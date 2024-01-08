from typing import Any, Dict, Optional

import faker

fake = faker.Factory.create()


def make_photo_data(
    pk: int, strategy: Optional[str], **fields: Any
) -> Dict[str, Any]:
    return {
        "model": "photofeed.Photo",
        "strategy": strategy,
        "pk": pk,
        "fields": {
            "lat": 1,
            "lng": 1,
            "image_url": "https://",
            "title": "Test",
            "created": "2021-01-01T09:56:01.003Z",
            **fields,
        },
    }


def make_user_data(
    pk: int, strategy: Optional[str], **fields: Any
) -> Dict[str, Any]:
    return {
        "model": "auth.User",
        "strategy": strategy,
        "pk": pk,
        "fields": {
            "username": fake.user_name(),  # type: ignore[attr-defined]
            **fields,
        },
    }
