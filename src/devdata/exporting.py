import contextlib
import io
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, Iterator, NamedTuple

SEPARATOR_BYTE = b"\x00"
BLOCK_SIZE = 4096

ExportRequest = NamedTuple(
    "ExportRequest",
    (
        ("app_model_label", str),
        ("strategy_class", str),
        ("strategy_kwargs", Dict[str, Any]),
        ("database", str),
    ),
)


def read_requests(fh: io.BytesIO) -> Iterator[ExportRequest]:
    buffer = bytes()
    while True:
        buffer += fh.read1(BLOCK_SIZE)

        left, separator, right = buffer.partition(SEPARATOR_BYTE)
        if separator:
            command_dict = json.loads(left.decode("utf-8"))
            yield ExportRequest(**command_dict)
            buffer = right


@contextlib.contextmanager
def response_writer(fh: io.BytesIO) -> Iterator[io.BytesIO]:
    yield fh
    fh.write(SEPARATOR_BYTE)
    fh.flush()
    print("written response")


class ExportFailed(Exception):
    def __init__(self, exitcode: int):
        self.exitcode = exitcode

    def __repr__(self):
        return "ExportFailed(exitcode={})".format(self.exitcode)


class Exporter:
    def __init__(self, command: str):
        self.command = command
        self._process = None
        self.buffer = bytes()

    def __enter__(self) -> "Exporter":
        self._process = subprocess.Popen(
            self.command.split(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        self._process.__enter__()
        return self

    def __exit__(self, *args, **kwargs):
        self._process.__exit__(*args, **kwargs)

    def export(
        self,
        *,
        app_model_label: str,
        strategy_class: str,
        strategy_kwargs: Dict[str, Any],
        database: str,
        output_path: Path
    ) -> int:
        export_request = ExportRequest(
            app_model_label=app_model_label,
            strategy_class=strategy_class,
            strategy_kwargs=strategy_kwargs,
            database=database,
        )

        written = 0

        with TemporaryDirectory() as tempdir:
            request_data = json.dumps(export_request._asdict()).encode("utf-8")
            self._process.stdin.write(request_data)
            self._process.stdin.write(SEPARATOR_BYTE)
            self._process.stdin.flush()

            temp_file_path = Path(tempdir) / output_path.name
            with temp_file_path.open("wb") as output:
                while True:
                    if self._process.poll() is not None:
                        raise ExportFailed(self._process.returncode)

                    self.buffer += self._process.stdout.read1(BLOCK_SIZE)
                    data, separator, rest = self.buffer.partition(
                        SEPARATOR_BYTE
                    )
                    written += output.write(data)
                    self.buffer = rest
                    if separator:
                        break

            temp_file_path.rename(output_path)

        return written
