from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any, Callable

from django.db import connections

Logger = Callable[[str], None]


class ExtraImport:
    """
    Base extra defining how to get data into a fresh database.
    """

    name: str
    depends_on: tuple[str, ...] = ()

    def __init__(self) -> None:
        pass

    def import_data(self, django_dbname: str, src: Path) -> None:
        """Load data into newly created database."""
        raise NotImplementedError


class ExtraExport:
    """
    Base extra defining how to get data out of an existing database.
    """

    seen_names: set[str] = set()

    def __init__(self, *args: Any, name: str, **kwargs: Any) -> None:
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


class PostgresSequences(ExtraExport, ExtraImport):
    """
    Export & import Postgres sequences.

    This provides support for reproducing sequences of the same type and at the
    same value in an imported database.

    During import any existing sequence of the same name is silently removed and
    replaced. This simplifies the interaction with each of the possible reset
    modes and approximately matches how `loaddata` treats importing rows with
    matching primary keys.
    """

    def __init__(
        self,
        *args: Any,
        name: str = "postgres-sequences",
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, name=name, **kwargs)

    def export_data(
        self,
        django_dbname: str,
        dest: Path,
        no_update: bool = False,
        log: Logger = lambda x: None,
    ) -> None:
        data_file = self.data_file(dest)

        if no_update and data_file.exists():
            return

        columns = (
            "sequencename",
            "data_type",
            "start_value",
            "min_value",
            "max_value",
            "increment_by",
            "cycle",
            "cache_size",
            "last_value",
        )

        with connections[django_dbname].cursor() as cursor:
            cursor.execute(
                """
                    SELECT
                        {columns}
                    FROM
                        pg_sequences
                    WHERE
                        sequencename NOT IN (
                            SELECT
                                seq.relname
                            FROM
                                pg_class AS seq
                            LEFT JOIN
                                pg_depend
                            ON
                                seq.relfilenode = pg_depend.objid
                            JOIN
                                pg_attribute AS attr
                            ON
                                attr.attnum = pg_depend.refobjsubid
                                AND attr.attrelid = pg_depend.refobjid
                            WHERE
                                seq.relkind = 'S'
                        );
                """.format(
                    columns=", ".join(columns),
                ),
            )
            sequences_state = [
                dict(zip(columns, row)) for row in cursor.fetchall()
            ]

            # Cope with the 'last_value' having not been populated in this
            # session. The following query is (I think) only supported in
            # Postgres 11.2+, however since Postgres 10 is about to be EOL
            # (November 2022) it doesn't seem worth the effort to support older
            # versions.
            for sequence_state in sequences_state:
                if sequence_state["last_value"] is None:
                    name = sequence_state["sequencename"]
                    cursor.execute(f"SELECT last_value FROM {name}")
                    (sequence_state["last_value"],) = cursor.fetchone()

        with data_file.open("w") as f:
            json.dump(sequences_state, f, indent=4)

    def import_data(self, django_dbname: str, src: Path) -> None:
        with self.data_file(src).open() as f:
            sequences = json.load(f)

        def check_simple_value(mapping: dict[str, str], *, key: str) -> str:
            value = mapping[key]
            if not value.replace("_", "").isalnum():
                raise ValueError(f"{key} is not alphanumeric")
            return value

        with connections[django_dbname].cursor() as cursor:
            for sequence in sequences:
                # Sequence name & data type need to be inline (i.e: can't be
                # passed as data), so provide some safety here.
                name = check_simple_value(sequence, key="sequencename")
                data_type = check_simple_value(sequence, key="data_type")

                # Support reset modes which don't drop the database. At some
                # point it might be nice to be able to hook into the reset mode
                # to remove sequences too, however that's likely complicated and
                # it's easy enough to handle here.
                #
                # Sequences don't nicely fit into one of just schema or data,
                # they're somewhat inherently both. Given that Django's
                # "loaddata" over-writes existing rows in tables, it seems
                # reasonable to do something similar for sequences -- even if
                # that means we actually drop the sequence and fully re-create
                # it.
                cursor.execute(f"DROP SEQUENCE IF EXISTS {name}")

                query = textwrap.dedent(
                    f"""
                    CREATE SEQUENCE {name}
                    AS {data_type}
                    INCREMENT BY %s
                    MINVALUE %s
                    MAXVALUE %s
                    START %s
                    CACHE %s
                """
                )
                params = [
                    sequence["increment_by"],
                    sequence["min_value"],
                    sequence["max_value"],
                    sequence["last_value"],
                    sequence["cache_size"],
                ]

                if sequence["cycle"]:
                    query += "CYCLE "
                else:
                    query += "NO CYCLE "

                cursor.execute(query, params)

                # Move on from the last value (which has already been used)
                cursor.execute("SELECT nextval(%s)", [name])
