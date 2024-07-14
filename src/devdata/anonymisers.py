import pathlib
import random
from typing import Any, TypeVar

import faker
from django.db import models

from .types import Anonymiser, GenericAnonymiser
from .utils import get_exported_pks_for_model

T = TypeVar("T")


def faker_anonymise(
    generator: str,
    *args: Any,
    preserve_nulls: bool = False,
    unique: bool = False,
    **kwargs: Any,
) -> Anonymiser:
    def anonymise(*, pii_value: T, fake: faker.Faker, **_kwargs: object) -> T:
        if preserve_nulls and pii_value is None:
            return None

        faker_generator = getattr(fake.unique if unique else fake, generator)
        return faker_generator(*args, **kwargs)

    return anonymise


def preserve_internal(
    alternative: GenericAnonymiser[T],
) -> GenericAnonymiser[T]:
    def anonymise(
        obj: models.Model,
        field: str,
        pii_value: T,
        **kwargs: Any,
    ) -> T:
        if getattr(obj, "is_superuser", False) or getattr(
            obj, "is_staff", False
        ):
            return pii_value
        return alternative(obj=obj, field=field, pii_value=pii_value, **kwargs)

    return anonymise


def const(value: T, preserve_nulls: bool = False) -> GenericAnonymiser[T]:
    def anonymise(*_: object, pii_value: T, **_kwargs: object) -> T:
        if preserve_nulls and pii_value is None:
            return None
        return value

    return anonymise


def random_foreign_key(
    obj: models.Model,
    field: str,
    dest: pathlib.Path,
    **_kwargs: object,
) -> Any:
    related_model = obj._meta.get_field(field).related_model
    exported_pks = get_exported_pks_for_model(dest, related_model)
    return random.choice(exported_pks)
