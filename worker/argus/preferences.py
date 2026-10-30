"""Where Argus's everyday (routine) model calls run, chosen in the app (D-77): Meta's API with Muse Spark, or Muse
Spark Open, Meta's open-weight model, served by Baseten. Verdicts (Muse Wonder) and segmentation (SAM 3.1) stay on
Meta's API whatever the switch says. Keys come from the environment only; the switch never sees or stores them."""

from __future__ import annotations

from typing import Literal

from argus.config import Settings
from argus.storage.db import Database
from argus.storage.repos import get_preference

Provider = Literal["meta", "baseten"]
PROVIDERS: tuple[Provider, ...] = ("meta", "baseten")
ROUTINE_PROVIDER = "routine_provider"
KEY_FOR: dict[str, str] = {"meta": "MODEL_API_KEY", "baseten": "BASETEN_API_KEY"}


def available(settings: Settings, provider: str) -> bool:
    if provider == "meta":
        return settings.model_api_key is not None
    if provider == "baseten":
        return settings.baseten_api_key is not None
    return False


def active_provider(db: Database, settings: Settings) -> Provider:
    """The saved choice, else the environment's default; Meta when the chosen provider has no key."""
    choice = get_preference(db, ROUTINE_PROVIDER) or settings.routine_provider
    return "baseten" if choice == "baseten" and available(settings, "baseten") else "meta"


def options(settings: Settings) -> list[dict]:
    return [
        {
            "id": "meta",
            "label": "Meta API",
            "model": settings.routine_model,
            "open_weight": False,
            "available": available(settings, "meta"),
        },
        {
            "id": "baseten",
            "label": "Baseten",
            "model": settings.open_model,
            "open_weight": True,
            "available": available(settings, "baseten"),
        },
    ]
