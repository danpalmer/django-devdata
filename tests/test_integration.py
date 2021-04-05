import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from pytest_check import check_func
from testcases import TESTCASES


def run_command(*command, **kwargs):
    return subprocess.run(
        ["testsite/manage.py", *command],
        cwd="tests",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs
    )


@pytest.fixture()
def test_data_dir():
    return Path(__file__).parent / "test-export"


@pytest.fixture(autouse=True)
def cleanup_test_data(test_data_dir):
    yield
    shutil.rmtree(test_data_dir, ignore_errors=True)


def assert_ran_successfully(process: subprocess.Popen):
    assert process.returncode == 0, process.stderr.decode("utf-8")


def test_export_help():
    process = run_command("devdata_export", "--help")
    assert_ran_successfully(process)
    assert process.stdout.startswith(b"usage: manage.py")


def test_import_help():
    process = run_command("devdata_import", "--help")
    assert_ran_successfully(process)
    assert process.stdout.startswith(b"usage: manage.py")


def test_export(test_data_dir):
    # Initialise the test database
    run_command("migrate", "--run-syncdb")

    # First setup the initial data
    all_fixtures = [x for y in TESTCASES for x in y.get_original_data()]
    with tempfile.NamedTemporaryFile("w", encoding="utf-8") as f:
        json.dump(all_fixtures, f)
        f.flush()
        f.seek(0)
        run_command("loaddata", "--format=json", "-", stdin=f)

    # Run the export
    process = run_command("devdata_export", "test-export")
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
                    exported_data[child.name][strategy_file.stem] = json.load(
                        f
                    )

    for test_case in TESTCASES:
        check_func(test_case.assert_on_exported_data(exported_data))
