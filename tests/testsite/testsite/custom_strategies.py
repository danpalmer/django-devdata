from pathlib import Path
from typing import TypeVar

from django.db import models

from devdata.strategies import QuerySetStrategy

TModel = TypeVar("TModel", bound=models.Model)


class InternalUsersStrategy(QuerySetStrategy):
    def get_queryset(
        self,
        django_dbname: str,
        dest: Path,
        model: TModel,
    ) -> models.QuerySet[TModel]:
        return (
            super()
            .get_queryset(django_dbname, dest, model)
            .filter(models.Q(is_staff=True) | models.Q(is_superuser=True))
        )
