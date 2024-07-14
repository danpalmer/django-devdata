import pathlib
from typing import Any, Generic, Protocol, TypeVar

import faker

T = TypeVar("T")


class GenericAnonymiser(Generic[T], Protocol):
    def __call__(
        self,
        *,
        obj: Any,
        field: str,
        pii_value: T,
        fake: faker.Faker,
        dest: pathlib.Path,
    ) -> T:
        ...


class Anonymiser(GenericAnonymiser[Any], Protocol):
    pass
