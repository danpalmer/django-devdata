import os
import subprocess

from django.conf import settings


def run_command(*command, extra_env=None, **kwargs):
    env = None
    if extra_env is not None:
        env = os.environ.copy()
        env.update(extra_env)
    return subprocess.run(
        ["testsite/manage.py", *command],
        cwd="tests",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={
            **os.environ,
            "TEST_DATABASE_NAME": settings.DATABASES["default"]["NAME"],
        },
        **kwargs
    )


def assert_ran_successfully(process: subprocess.Popen):
    assert process.returncode == 0, process.stderr.decode("utf-8")
