from __future__ import annotations

from typing import Any

from test_infrastructure import DevdataTestBase
from turtles.models import Turtle, World


class TestCircularFK(DevdataTestBase):
    def get_original_data(self) -> list[dict[str, Any]]:
        return [
            {
                "model": "turtles.Turtle",
                "strategy": "default",
                "pk": 1,
                "fields": {"standing_on_id": None},
            },
            {
                "model": "turtles.Turtle",
                "strategy": "default",
                "pk": 2,
                "fields": {"standing_on_id": 1},
            },
            {
                "model": "turtles.Turtle",
                "strategy": "default",
                "pk": 3,
                "fields": {"standing_on_id": 2},
            },
            {
                "model": "turtles.Turtle",
                "strategy": "default",
                "pk": 4,
                "fields": {"standing_on_id": 2},
            },
            {
                "model": "turtles.World",
                "strategy": "default",
                "pk": 9,
                "fields": {"riding_on_id": 3},
            },
            {
                "model": "turtles.World",
                "strategy": "default",
                "pk": 13,
                "fields": {"riding_on_id": 4},
            },
        ]

    def assert_on_exported_data(self, exported_data):
        exported_turtle_pks = self.exported_pks(exported_data, "turtles.Turtle")
        assert exported_turtle_pks == set((1, 2, 3, 4))

        exported_workd_pks = self.exported_pks(exported_data, "turtles.World")
        assert exported_workd_pks == set((9, 13))

    def assert_on_imported_data(self):
        assert set(Turtle.objects.values_list("pk", flat=True)) == set(
            (1, 2, 3, 4)
        )
        assert set(World.objects.values_list("pk", flat=True)) == set((9, 13))
