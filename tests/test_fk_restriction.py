from __future__ import annotations

from django.contrib.auth.models import User
from test_infrastructure import (
    DevdataTestBase,
    ExportedData,
    TestObject,
    make_photo_data,
    make_user_data,
)


class TestFKRestriction(DevdataTestBase):
    def get_original_data(self) -> list[TestObject]:
        return [
            # Internal user (included)
            make_user_data(101, "internal", is_superuser=True),
            make_photo_data(201, "default", user_id=101),
            make_photo_data(202, "default", user_id=101),
            # Non-internal, but PK included for export
            make_user_data(102, "test_users"),
            make_photo_data(203, "default", user_id=102),
            make_photo_data(204, "default", user_id=102),
            # Excluded user
            make_user_data(103, None),
            make_photo_data(205, "default", user_id=103),
            make_photo_data(206, "default", user_id=103),
        ]

    def assert_on_exported_data(self, exported_data: ExportedData) -> None:
        exported_user_pks = self.exported_pks(exported_data, "auth.User")
        assert exported_user_pks == set((101, 102))

        exported_photo_pks = self.exported_pks(exported_data, "photofeed.Photo")
        assert exported_photo_pks == set((201, 202, 203, 204))

    def assert_on_imported_data(self) -> None:
        assert not User.objects.filter(pk=103).exists()
        assert set(
            User.objects.get(pk=101).photo_set.values_list("pk", flat=True),
        ) == set((201, 202))
