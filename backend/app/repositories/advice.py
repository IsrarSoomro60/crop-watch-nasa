"""Advice lookup from app/domain/advice.json (keyed by crop, risk and level)."""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from app.core.config import APP_DIR
from app.schemas.crop import CropName, RiskLevel, RiskType
from app.schemas.rotation import AdviceTip

ADVICE_PATH = APP_DIR / "domain" / "advice.json"
MAX_TIPS = 3


class AdviceEntry(BaseModel):
    crop: str  # CropName value or "*"
    risk: RiskType
    levels: list[RiskLevel]
    text_en: str
    text_ur: str | None = None
    ur_reviewed: bool = False
    source: str


class AdviceRepository:
    def __init__(self, path: Path = ADVICE_PATH):
        data = json.loads(path.read_text(encoding="utf-8"))
        self._entries = [AdviceEntry.model_validate(e) for e in data["entries"]]

    def tips(self, crop: CropName, levels: dict[RiskType, RiskLevel | None]) -> list[AdviceTip]:
        """Up to three tips, most severe risks first."""
        ranked = sorted(
            ((risk, level) for risk, level in levels.items() if level in (RiskLevel.MODERATE, RiskLevel.HIGH)),
            key=lambda rl: rl[1] != RiskLevel.HIGH,
        )
        tips: list[AdviceTip] = []
        for risk, level in ranked:
            for e in self._entries:
                if e.risk == risk and level in e.levels and e.crop in (crop.value, "*"):
                    tips.append(AdviceTip(
                        risk=risk, level=level, text_en=e.text_en, text_ur=e.text_ur, ur_reviewed=e.ur_reviewed,
                        source=e.source,
                    ))
        return tips[:MAX_TIPS]


@lru_cache
def get_advice_repository() -> AdviceRepository:
    return AdviceRepository()
