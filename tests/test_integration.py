import subprocess


def test_export_help():
    process = subprocess.run(['testsite/manage.py','devdata_export','--help'], cwd='tests', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.returncode == 0
    assert process.stdout.startswith(b'usage: manage.py')


def test_import_help():
    process = subprocess.run(['testsite/manage.py','devdata_import','--help'], cwd='tests', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.returncode == 0
    assert process.stdout.startswith(b'usage: manage.py')
