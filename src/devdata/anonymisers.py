import random

from .utils import get_exported_pks_for_model


def faker_anonymise(
    generator, *args, preserve_nulls=False, unique=False, **kwargs
):
    def anonymise(*, pii_value, fake, **_kwargs):
        if preserve_nulls and pii_value is None:
            return None

        faker_generator = getattr(fake.unique if unique else fake, generator)
        return faker_generator(*args, **kwargs)

    return anonymise


def preserve_internal(alternative):
    def anonymise(obj, field, pii_value, **kwargs):
        if getattr(obj, "is_superuser", False) or getattr(
            obj, "is_staff", False
        ):
            return pii_value
        return alternative(obj=obj, field=field, pii_value=pii_value, **kwargs)

    return anonymise


def const(value, preserve_nulls=False):
    def anonymise(*_, pii_value, **_kwargs):
        if preserve_nulls and pii_value is None:
            return None
        return value

    return anonymise


def random_foreign_key(obj, field, dest, **_kwargs):
    related_model = obj._meta.get_field(field).related_model
    exported_pks = get_exported_pks_for_model(dest, related_model)
    return random.choice(exported_pks)
