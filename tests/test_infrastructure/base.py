from __future__ import annotations

import collections
import itertools
import json
from pathlib import Path
from typing import Any, Dict, Iterable

import pytest
from django.core import serializers
from django.db import connections, transaction

from devdata.reset_modes import MODES
from devdata.utils import to_app_model_label, to_model

from .utils import assert_ran_successfully, run_command

TestObject = Dict[str, Any]


@pytest.mark.django_db(transaction=True)
class DevdataTestBase:
    # Public API for tests

    def get_original_data(self) -> list[TestObject]:
        raise NotImplementedError

    def assert_on_exported_data(self, exported_data):
        pass

    def assert_on_imported_data(self):
        pass

    # Utils

    def original_pks(self, model):
        return set(
            x["pk"]
            for x in self.get_original_data()
            if x["model"].lower() == model.lower()
        )

    def exported_pks(self, exported_data, model, strategy=None):
        strategies = exported_data[model]
        if strategy is not None:
            exported = strategies[strategy]
        else:
            exported = itertools.chain(*strategies.values())
        return set(x["pk"] for x in exported)

    def _filter_exported(
        self,
        lookup: dict[str, set[Any]],
        objects: list[TestObject],
    ) -> Iterable[TestObject]:
        obj = objects[0]  # Same model so we just use the first for structure
        model_name = obj["model"]
        model = to_model(model_name)

        assert model, model_name

        fk_fields = [
            (x.attname, to_app_model_label(x.related_model))
            for x in model._meta.fields
            if x.related_model
        ]
        if not fk_fields:
            yield from objects
            return

        for obj in objects:
            for field, model in fk_fields:
                if (
                    obj["fields"][field] is None
                    or obj["fields"][field] in lookup[model]
                ):
                    yield obj

    def dump_data_for_import(
        self,
        original_data: list[TestObject],
        test_data_dir: Path,
    ) -> None:
        # Write out data to the filesystem as if it had been exported
        data: dict[str, dict[str, list[TestObject]]]
        data = collections.defaultdict(
            lambda: collections.defaultdict(list),
        )
        exported_pks: dict[str, set[Any]] = collections.defaultdict(set)
        for obj in original_data:
            if obj["strategy"] is None:
                continue
            exported_pks[obj["model"]].add(obj["pk"])
            data[obj["model"]][obj["strategy"]].append(obj)

        for model, strategies in data.items():
            for strategy, objects in strategies.items():
                path = test_data_dir / model / f"{strategy}.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(
                        list(self._filter_exported(exported_pks, objects)),
                    ),
                )

        # Ensure we have migrations history to import to validate that the
        # import of such data actually works.
        (test_data_dir / "migrations.json").write_text(
            json.dumps(
                [
                    {
                        "app": "auth",
                        "name": "0001_initial",
                        "applied": "2023-01-01T12:00:00.000Z",
                    },
                ],
            ),
        )

    # Test structure

    def test_export(self, test_data_dir, ensure_migrations_table):
        with transaction.atomic():
            data = json.dumps(self.get_original_data())
            objects = serializers.deserialize("json", data)
            for obj in objects:
                obj.save()

        # Run the export
        process = run_command(
            "devdata_export",
            test_data_dir.name,
        )
        assert_ran_successfully(process)

        # Read in the exported data
        exported_data = {}
        for child in test_data_dir.iterdir():
            if child.name == "migrations.json":
                with child.open() as f:
                    exported_data["migrations"] = json.load(f)
            else:
                exported_data[child.name] = {}
                if child.is_dir():
                    for strategy_file in child.iterdir():
                        with strategy_file.open() as f:
                            exported_data[child.name][
                                strategy_file.stem
                            ] = json.load(f)

        self.assert_on_exported_data(exported_data)

    @pytest.mark.parametrize("reset_mode", MODES.keys())
    def test_import(
        self,
        reset_mode,
        test_data_dir,
        default_export_data,
        django_db_blocker,
        ensure_migrations_table,
    ):
        self.dump_data_for_import(self.get_original_data(), test_data_dir)

        # Ensure all database connections are closed before we attempt to import
        # as this will need to drop the database.
        for connection in connections.all():
            connection.close()

        # Run the import
        process = run_command(
            "devdata_import",
            test_data_dir.name,
            "--no-input",
            f"--reset-mode={reset_mode}",
        )
        assert_ran_successfully(process)

        # Unblock the database so that we can resume accessing it. This will be
        # a different actual database on disk at this point, as the import will
        # have recreated it. We do this before assertions so that we've
        # restored database access for later tests if needed.
        with django_db_blocker.unblock():
            self.assert_on_imported_data()
