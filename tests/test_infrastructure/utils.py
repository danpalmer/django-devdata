from __future__ import annotations

import os
import subprocess
from typing import Any

from django.conf import settings


def run_command(
    *command: str,
    **kwargs: Any,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["testsite/manage.py", *command],
        cwd="tests",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={
            **os.environ,
            # Override the database name to that from pytest-django so that it
            # matches, as we're running a subprocess here so it's not a part of
            # the pytest environment.
            "TEST_DATABASE_NAME": settings.DATABASES["default"]["NAME"],
        },
        **kwargs,
    )


def assert_ran_successfully(
    process: subprocess.CompletedProcess[bytes],
) -> None:
    assert process.returncode == 0, process.stderr.decode("utf-8")  # type: ignore[union-attr]
