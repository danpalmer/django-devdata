from __future__ import annotations

from collections.abc import Collection, Iterable
from pathlib import Path
from typing import Any, Callable, TypeVar

from django.core import serializers
from django.core.serializers.base import DeserializedObject
from django.db import models

from .pii_anonymisation import PiiAnonymisingSerializer
from .utils import (
    get_exported_pks_for_model,
    is_empty_iterator,
    to_app_model_label,
    to_model,
)

TModel = TypeVar("TModel", bound=models.Model)
Logger = Callable[[str], None]


class Strategy:
    """
    Base strategy defining how to get data for a given model into a fresh
    database.
    """

    name: str
    depends_on: tuple[str, ...] = ()

    def __init__(self) -> None:
        pass

    def import_data(
        self,
        django_dbname: str,
        src: Path,
        model: models.Model,
    ) -> None:
        """Load data into newly created database."""
        raise NotImplementedError


class Exportable:
    """
    A strategy that uses exported data from some source, typically a production
    database.
    """

    seen_names: set[tuple[str, str]] = set()

    def __init__(self, *args: Any, name: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.name = name

    def export_data(
        self,
        django_dbname: str,
        dest: Path,
        model: models.Model,
        no_update: bool = False,
        log: Logger = lambda x: None,
    ) -> None:
        """
        Export the data to a directory on disk. `no_update` indicates not to
        update if there is any data already existing locally.
        """
        pass

    def data_file(self, dest: Path, app_model_label: str) -> Path:
        return dest / app_model_label / "{}.json".format(self.name)

    def ensure_dir_exists(self, dest: Path, app_model_label: str) -> None:
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

    def __init__(
        self,
        *args: Any,
        anonymise: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.anonymise = anonymise

    def get_restricted_pks(
        self,
        dest: Path,
        model: models.Model,
    ) -> dict[str, list[str]]:
        restricted_pks = {}

        for field in model._meta.fields:
            if not field.related_model:
                continue

            if field.related_model == model:
                continue

            app_model_label = to_app_model_label(field.related_model)
            restricted_pks[app_model_label] = get_exported_pks_for_model(
                dest,
                field.related_model,
            )

        return restricted_pks

    def get_queryset(
        self,
        django_dbname: str,
        dest: Path,
        model: TModel,
    ) -> models.QuerySet[TModel]:
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
        django_dbname: str,
        dest: Path,
        model: models.Model,
        no_update: bool = False,
        log: Logger = lambda x: None,
    ) -> None:
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

    def import_data(
        self,
        django_dbname: str,
        src: Path,
        model: models.Model,
    ) -> None:
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

    def import_objects(
        self,
        django_dbname: str,
        src: Path,
        model: models.Model,
        objects: Iterable[DeserializedObject],
    ) -> None:
        qs = model.objects.using(django_dbname)
        existing_pks = set(qs.values_list("pk", flat=True))
        qs.bulk_create(
            [x.object for x in objects if x.object.pk not in existing_pks]
        )


class ExactQuerySetStrategy(QuerySetStrategy):
    """Import specific rows from a table using a QuerySet filtered to given PKs."""

    def __init__(self, *args: Any, pks: Collection[Any], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.pks = pks

    def get_queryset(
        self,
        django_dbname: str,
        dest: Path,
        model: TModel,
    ) -> models.QuerySet[TModel]:
        return (
            super()
            .get_queryset(django_dbname, dest, model)
            .filter(pk__in=self.pks)
        )


class RandomSampleQuerySetStrategy(QuerySetStrategy):
    """Imports a random sample from a QuerySet."""

    def __init__(self, *args: Any, count: int, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.count = count

    def get_queryset(
        self,
        django_dbname: str,
        dest: Path,
        model: TModel,
    ) -> models.QuerySet[TModel]:
        return (
            super()
            .get_queryset(django_dbname, dest, model)
            .order_by("?")[: self.count]
        )


class LatestSampleQuerySetStrategy(QuerySetStrategy):
    """Imports the latest items from a QuerySet."""

    def __init__(
        self,
        *args: Any,
        count: int,
        order_by: str = "-id",
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.count = count
        self.order_by = order_by

    def get_queryset(
        self,
        django_dbname: str,
        dest: Path,
        model: TModel,
    ) -> models.QuerySet[TModel]:
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

    def get_reverse_filter(
        self,
        dest: Path,
        model: models.Model,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def get_queryset(
        self,
        django_dbname: str,
        dest: Path,
        model: TModel,
    ) -> models.QuerySet[TModel]:
        qs = super().get_queryset(django_dbname, dest, model)
        return qs.filter(**self.get_reverse_filter(dest, model))


class DeleteFirstQuerySetStrategy(QuerySetStrategy):
    def import_objects(
        self,
        django_dbname: str,
        src: Path,
        model: models.Model,
        objects: Iterable[DeserializedObject],
    ) -> None:
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

    def import_data(
        self,
        django_dbname: str,
        src: Path,
        model: models.Model,
    ) -> None:
        pass


class FailingStrategy(Exportable, Strategy):
    def export_data(self, *args: object, **kwargs: object) -> None:
        raise ValueError("This strategy always fails.")
