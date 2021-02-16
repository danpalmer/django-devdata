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


def random_foreign_key(obj, field, **_kwargs):
    rel = obj._meta.fields[field].related_model.objects.order_by("?").get()
    return rel.pk
