from typing import Set, Tuple

from django.core import serializers
from django.db import models

from .pii_anonymisation import PiiAnonymisingSerializer
from .utils import (
    get_exported_pks_for_model,
    is_empty_iterator,
    to_app_model_label,
    to_model,
)


class Strategy:
    """
    Base strategy defining how to get data for a given model into a fresh
    database.
    """

    depends_on = ()  # type: Tuple[str, ...]

    def __init__(self):
        pass

    def import_data(self, django_dbname, src, model):
        """Load data into newly created database."""
        raise NotImplementedError


class Exportable:
    """
    A strategy that uses exported data from some source, typically a production
    database.
    """

    seen_names = set()  # type: Set[Tuple[str, str]]

    def __init__(self, *args, name, **kwargs):
        super().__init__(*args, **kwargs)

        self.name = name

    def export_data(
        self,
        django_dbname,
        dest,
        model,
        no_update=False,
        log=lambda x: None,
    ):
        """
        Export the data to a directory on disk. `no_update` indicates not to
        update if there is any data already existing locally.
        """
        pass

    def data_file(self, dest, app_model_label):
        return dest / app_model_label / "{}.json".format(self.name)

    def ensure_dir_exists(self, dest, app_model_label):
        unique_key = (app_model_label, self.name)
        if unique_key in self.seen_names:
            raise ValueError(
                "Exportable strategy names must be unique per model so that "
                "exports do not collide.",
            )
        self.seen_names.add(unique_key)

        model_dir = dest / app_model_label
        model_dir.mkdir(parents=True, exist_ok=True)


class QuerySetStrategy(Exportable, Strategy):
    """Import a table using an unfiltered QuerySet."""

    use_natural_foreign_keys = False
    use_natural_primary_keys = False

    json_indent = 2

    def __init__(self, *args, anonymise=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.anonymise = anonymise

    def get_restricted_pks(self, dest, model):
        restricted_pks = {}

        for field in model._meta.fields:
            if not field.related_model:
                continue

            app_model_label = to_app_model_label(field.related_model)
            restricted_pks[app_model_label] = get_exported_pks_for_model(
                dest,
                field.related_model,
            )

        return restricted_pks

    def get_queryset(self, django_dbname, dest, model):
        queryset = model.objects.using(django_dbname)

        for app_model_label, restrict_pks in self.get_restricted_pks(
            dest,
            model,
        ).items():
            restrict_model = to_model(app_model_label)

            # We filter to all fields that relate to the restricted model. This
            # will usually be just one field, but in cases where it's multiple
            # to preserve FK integrity we must restrict all of them.
            fk_fields = [
                x
                for x in model._meta.fields
                if x.related_model == restrict_model
                if x.related_model != model
            ]

            queryset = queryset.filter(
                *[
                    models.Q(
                        **{x.attname: None},
                    )
                    | models.Q(
                        **{"{}__in".format(x.attname): restrict_pks},
                    )
                    for x in fk_fields
                ]
            )

        return queryset

    def export_data(
        self,
        django_dbname,
        dest,
        model,
        no_update=False,
        log=lambda x: None,
    ):
        app_model_label = to_app_model_label(model)
        data_file = self.data_file(dest, app_model_label)

        if no_update and data_file.exists():
            return

        self.ensure_dir_exists(dest, app_model_label)

        queryset = self.get_queryset(django_dbname, dest, model)

        serializer = (
            PiiAnonymisingSerializer(dest=dest)
            if self.anonymise
            else serializers.get_serializer("json")
        )

        with data_file.open("w") as output:
            iterator, queryset_is_empty = is_empty_iterator(queryset.iterator())
            if queryset_is_empty:
                log(
                    "Warning! '{}' exporter for {} selected no data.".format(
                        self.name,
                        app_model_label,
                    )
                )

            serializer.serialize(
                iterator,
                indent=self.json_indent,
                use_natural_foreign_keys=self.use_natural_foreign_keys,
                use_natural_primary_keys=self.use_natural_primary_keys,
                stream=output,
            )

    def import_data(self, django_dbname, src, model):
        app_model_label = to_app_model_label(model)

        try:
            with self.data_file(src, app_model_label).open() as f:
                objects = serializers.deserialize(
                    "json", f, using=django_dbname
                )
                self.import_objects(django_dbname, src, model, objects)
        except Exception:
            print("Failed to import {} ({})".format(app_model_label, self.name))
            raise

    def import_objects(self, django_dbname, src, model, objects):
        qs = model.objects.using(django_dbname)
        existing_pks = set(qs.values_list("pk", flat=True))
        qs.bulk_create(
            [x.object for x in objects if x.object.pk not in existing_pks]
        )


class ExactQuerySetStrategy(QuerySetStrategy):
    """Import specific rows from a table using a QuerySet filtered to given PKs."""

    def __init__(self, *args, pks, **kwargs):
        super().__init__(*args, **kwargs)
        self.pks = pks

    def get_queryset(self, django_dbname, dest, model):
        return (
            super()
            .get_queryset(django_dbname, dest, model)
            .filter(pk__in=self.pks)
        )


class RandomSampleQuerySetStrategy(QuerySetStrategy):
    """Imports a random sample from a QuerySet."""

    def __init__(self, *args, count, **kwargs):
        super().__init__(*args, **kwargs)

        self.count = count

    def get_queryset(self, django_dbname, dest, model):
        return (
            super()
            .get_queryset(django_dbname, dest, model)
            .order_by("?")[: self.count]
        )


class LatestSampleQuerySetStrategy(QuerySetStrategy):
    """Imports the latest items from a QuerySet."""

    def __init__(self, *args, count, order_by="-id", **kwargs):
        super().__init__(*args, **kwargs)

        self.count = count
        self.order_by = order_by

    def get_queryset(self, django_dbname, dest, model):
        qs = super().get_queryset(django_dbname, dest, model)
        return qs.order_by(self.order_by)[: self.count]


class ModelReverseRelationshipQuerySetStrategy(QuerySetStrategy):
    """
    Base class for inverse relationship queryset exporting.
    Useful for relationships that go the wrong way to work with
    normal dependency analysis. Example:

        class Order(Model):
            user = ForeignKey(User)
            charge = ForeignKey(Charge)

        class Charge(Model):
            ...

    Requires a dependent model, such as `User`, and defines an additional
    explicit dependency on that model locally. Reads in those IDs, passes them
    to the exporting process, where they are available to `get_queryset`.
    """

    def get_reverse_filter(self, dest, model):
        raise NotImplementedError

    def get_queryset(self, django_dbname, dest, model):
        qs = super().get_queryset(django_dbname, dest, model)
        return qs.filter(**self.get_reverse_filter(dest, model))


class DeleteFirstQuerySetStrategy(QuerySetStrategy):
    def import_objects(self, django_dbname, src, model, objects):
        qs = model.objects.using(django_dbname)
        qs.all().delete()
        super().import_objects(django_dbname, src, model, objects)


class FactoryStrategy(Strategy):
    """
    Use the provided factory/factories to create data for this model (and any
    related) models.
    """

    def __init__(self, *args, factories, **kwargs):
        super().__init__(*args, **kwargs)
        self.factories = factories

    def import_data(self, django_dbname, src, model):
        pass


class FailingStrategy(Exportable, Strategy):
    def export_data(self, *args, **kwargs):
        raise ValueError("This strategy always fails.")
