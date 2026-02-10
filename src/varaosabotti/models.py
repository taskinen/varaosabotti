from dataclasses import dataclass
from enum import Enum


class CategoryStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass(frozen=True)
class Category:
    name: str
    title: str
    href: str
    status: CategoryStatus
    group: str | None = None
    parent: str | None = None
