from django.db import models

from devdata.strategies import QuerySetStrategy


class InternalUsersStrategy(QuerySetStrategy):
    def get_queryset(self, django_dbname, dest, model):
        return (
            super()
            .get_queryset(django_dbname, dest, model)
            .filter(models.Q(is_staff=True) | models.Q(is_superuser=True))
        )
