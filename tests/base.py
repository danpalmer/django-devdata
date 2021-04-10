import collections
import itertools
import json
from typing import Any, Dict, Iterable, Set

import pytest
from django.core import serializers
from django.db import transaction
from utils import assert_ran_successfully, run_command

from devdata.utils import to_app_model_label, to_model

TestObject = Dict[str, Any]

ALL_TEST_STRATEGIES = (
    ("admin.LogEntry", "default"),
    ("auth.Permission", "default"),
    ("auth.Group_permissions", "default"),
    ("auth.Group", "default"),
    ("auth.User_groups", "default"),
    ("auth.User_user_permissions", "default"),
    ("contenttypes.ContentType", "default"),
    ("sessions.Session", "default"),
    ("polls.Question", "default"),
    ("polls.Choice", "default"),
    ("photofeed.Photo", "default"),
    ("photofeed.Like", "latest"),
    ("photofeed.View", "random"),
    ("auth.User", "internal"),
    ("auth.User", "test_users"),
)


@pytest.mark.django_db(transaction=True)
class DevdataTestBase:
    # Public API for tests

    def get_original_data(self):
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
        self, lookup: Dict[str, Set], objects: Iterable[TestObject]
    ) -> Iterable[TestObject]:
        obj = objects[0]  # Same model so we just use the first for structure
        model_name = obj["model"]
        model = to_model(model_name)

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
                if obj["fields"][field] in lookup[model]:
                    yield obj

    # Test structure

    def test_export(self, test_data_dir):
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
                for strategy_file in child.iterdir():
                    with strategy_file.open() as f:
                        exported_data[child.name][
                            strategy_file.stem
                        ] = json.load(f)

        self.assert_on_exported_data(exported_data)

    def test_import(self, test_data_dir, django_db_blocker):
        # Block database access so that until we're asserting on the state at
        # the end, nothing from pytest will be accessing it.
        django_db_blocker.block()

        # Write out defaults of empty exports for everything first, not all
        # tests will use all models.
        empty_model = json.dumps([])
        for model, strategy in ALL_TEST_STRATEGIES:
            path = test_data_dir / model / f"{strategy}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(empty_model)

        # Write out data to the filesystem as if it had been exported
        data = collections.defaultdict(
            lambda: collections.defaultdict(list)
        )  # type: Dict[str, Dict[str, TestObject]]
        exported_pks = collections.defaultdict(set)  # type: Dict[str, Set]
        for obj in self.get_original_data():
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
                        list(self._filter_exported(exported_pks, objects))
                    )
                )

        (test_data_dir / "migrations.json").write_text(empty_model)

        # TODO: wait for connections to drop

        # Run the import
        process = run_command(
            "devdata_import",
            test_data_dir.name,
            "--no-input",
        )

        # Unblock the database so that we can resume accessing it. This will be
        # a different actual database on disk at this point, as the import will
        # have recreated it. We do this before assertions so that we've
        # restored database access for later tests if needed.
        django_db_blocker.unblock()

        assert_ran_successfully(process)
        self.assert_on_imported_data()
