import json
import textwrap
from pathlib import Path
from typing import Callable, Dict, Set, Tuple

from django.db import connections

Logger = Callable[[object], None]


class ExtraImport:
    """
    Base extra defining how to get data into a fresh database.
    """

    depends_on = ()  # type: Tuple[str, ...]

    def __init__(self) -> None:
        pass

    def import_data(self, django_dbname: str, src: Path) -> None:
        """Load data into newly created database."""
        raise NotImplementedError


class ExtraExport:
    """
    Base extra defining how to get data out of an existing .
    """

    seen_names = set()  # type: Set[Tuple[str, str]]

    def __init__(self, *args, name, **kwargs):
        super().__init__(*args, **kwargs)

        self.name = name

    def export_data(
        self,
        django_dbname: str,
        dest: Path,
        no_update: bool = False,
        log: Logger = lambda x: None,
    ) -> None:
        """
        Export the data to a directory on disk. `no_update` indicates not to
        update if there is any data already existing locally.
        """
        pass

    def data_file(self, dest: Path) -> Path:
        return dest / f"{self.name}.json"

    def ensure_dir_exists(self, dest: Path) -> None:
        unique_key = self.name
        if unique_key in self.seen_names:
            raise ValueError(
                "Exportable strategy names must be unique per model so that "
                "exports do not collide.",
            )
        self.seen_names.add(unique_key)

        dest.mkdir(parents=True, exist_ok=True)
