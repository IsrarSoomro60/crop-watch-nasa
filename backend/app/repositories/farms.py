"""In-memory farm store for the prototype. Swap for a database when needed."""

from uuid import uuid4

from app.schemas.farm import Farm, FarmCreate


class InMemoryFarmRepository:
    def __init__(self) -> None:
        self._farms: dict[str, Farm] = {}

    def create(self, data: FarmCreate) -> Farm:
        farm = Farm(id=uuid4().hex, **data.model_dump())
        self._farms[farm.id] = farm
        return farm

    def get(self, farm_id: str) -> Farm | None:
        return self._farms.get(farm_id)

    def list(self) -> list[Farm]:
        return list(self._farms.values())


farm_repository = InMemoryFarmRepository()
