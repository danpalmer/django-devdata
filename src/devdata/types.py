import pathlib
from typing import Any, Protocol, TypeVar

import faker

T = TypeVar("T")


class Anonymiser(Protocol):
    def __call__(
        self,
        obj: Any,
        field: str,
        pii_value: T,
        fake: faker.Faker,
        dest: pathlib.Path,
    ) -> T:
        ...
