from __future__ import annotations

from pathlib import Path
from typing import Any

import faker
from django.core.serializers.json import Serializer as JSONSerializer
from django.db import models

from .settings import settings
from .utils import to_app_model_label


class PiiAnonymisingSerializer(JSONSerializer):
    def __init__(self, *args: Any, dest: Path, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fake = faker.Faker(locale=settings.faker_locales)
        self.dest = dest

    def get_dump_object(self, obj: models.Model) -> dict[str, Any]:
        data = super().get_dump_object(obj)

        for field, value in data["fields"].items():
            if field in settings.field_anonymisers:
                data["fields"][field] = settings.field_anonymisers[field](
                    obj=obj,
                    field=field,
                    pii_value=value,
                    fake=self.fake,
                    dest=self.dest,
                )

            app_model_label = to_app_model_label(obj.__class__)
            model_anonymisers = settings.model_anonymisers.get(
                app_model_label,
                {},
            )

            if field in model_anonymisers:
                data["fields"][field] = model_anonymisers[field](
                    obj=obj,
                    field=field,
                    pii_value=value,
                    fake=self.fake,
                    dest=self.dest,
                )

        return data
