import itertools
import json

import pytest
from django.core import serializers
from django.db import transaction
from utils import assert_ran_successfully, run_command


@pytest.mark.django_db(transaction=True)
class DevdataTestBase:
    # Public API for tests

    def get_original_data(self):
        raise NotImplementedError

    def assert_on_exported_data(self, exported_data):
        pass

    def assert_on_imported_data(self, connection):
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

    # Test structure

    def test(self, test_data_dir):
        with transaction.atomic():
            data = json.dumps(self.get_original_data())
            objects = serializers.deserialize("json", data)
            for object in objects:
                object.save()

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
