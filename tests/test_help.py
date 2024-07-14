from test_infrastructure import assert_ran_successfully, run_command


def test_export_help() -> None:
    process = run_command("devdata_export", "--help")
    assert_ran_successfully(process)
    assert process.stdout.startswith(b"usage: manage.py")


def test_import_help() -> None:
    process = run_command("devdata_import", "--help")
    assert_ran_successfully(process)
    assert process.stdout.startswith(b"usage: manage.py")
