import faker
from django.conf import settings
from django.core.serializers.json import Serializer as JSONSerializer

from .utils import to_app_model_label


class PiiAnonymisingSerializer(JSONSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fake = faker.Faker(locale=settings.DEVDATA_FAKER_LOCALES)

    def get_dump_object(self, obj):
        data = super().get_dump_object(obj)

        for field, value in data["fields"].items():
            if field in settings.DEVDATA_FIELD_ANONYMISERS:
                data["fields"][field] = settings.DEVDATA_FIELD_ANONYMISERS[
                    field
                ](
                    obj=obj,
                    field=field,
                    pii_value=value,
                    fake=self.fake,
                )

            app_model_label = to_app_model_label(obj.__class__)
            model_anonymisers = settings.DEVDATA_MODEL_ANONYMISERS.get(
                app_model_label,
                {},
            )

            if field in model_anonymisers:
                data["fields"][field] = model_anonymisers[field](
                    obj=obj,
                    field=field,
                    pii_value=value,
                    fake=self.fake,
                )

        return data
