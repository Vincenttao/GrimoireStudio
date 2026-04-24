import json
from datetime import datetime

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from backend.database import get_db_connection, get_project_settings
from backend.models import (
    DefaultRenderMixer,
    LLMApiKeys,
    PlatformProfile,
    ProjectSettings,
)

router = APIRouter()


DEFAULT_SETTINGS = ProjectSettings(
    id="single_row_lock",
    llm_api_keys=LLMApiKeys(),
    llm_api_base=None,
    default_render_mixer=DefaultRenderMixer(pov_type="OMNISCIENT", style_template="热血爽文"),
)


def _settings_to_dict(s: ProjectSettings) -> dict:
    d = s.model_dump(mode="json")
    # ensure ISO strings for datetimes
    if isinstance(d.get("last_commit_at"), datetime):
        d["last_commit_at"] = d["last_commit_at"].isoformat()
    return d


@router.get("")
async def get_settings():
    try:
        async with get_db_connection() as conn:
            settings = await get_project_settings(conn)
        return {"settings": _settings_to_dict(settings)}
    except Exception as e:
        logger.exception(f"Unexpected error in get_settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PatchSettingsRequest(BaseModel):
    """
    Partial settings update. All fields optional; only set ones are written.
    """

    llm_model: str | None = None
    llm_api_keys: dict | None = None
    llm_api_base: str | None = None
    max_turns: int | None = None
    tension_threshold: float | None = None
    default_render_mixer: dict | None = None
    # V1.1
    target_platform: PlatformProfile | None = None
    default_target_char_count: int | None = None
    default_max_sent_len: int | None = None
    ending_hook_guard_enabled: bool | None = None
    padding_detector_enabled: bool | None = None


@router.patch("")
async def patch_settings(patch: PatchSettingsRequest):
    try:
        async with get_db_connection() as conn:
            current = await get_project_settings(conn)

            # Apply patch on a copy
            updated = current.model_copy()
            if patch.llm_model is not None:
                updated.llm_model = patch.llm_model
            if patch.llm_api_keys is not None:
                updated.llm_api_keys = LLMApiKeys(**patch.llm_api_keys)
            if patch.llm_api_base is not None:
                updated.llm_api_base = patch.llm_api_base
            if patch.max_turns is not None:
                updated.max_turns = patch.max_turns
            if patch.tension_threshold is not None:
                updated.tension_threshold = patch.tension_threshold
            if patch.default_render_mixer is not None:
                updated.default_render_mixer = DefaultRenderMixer(**patch.default_render_mixer)
            if patch.target_platform is not None:
                updated.target_platform = patch.target_platform
            if patch.default_target_char_count is not None:
                updated.default_target_char_count = patch.default_target_char_count
            if patch.default_max_sent_len is not None:
                updated.default_max_sent_len = patch.default_max_sent_len
            if patch.ending_hook_guard_enabled is not None:
                updated.ending_hook_guard_enabled = patch.ending_hook_guard_enabled
            if patch.padding_detector_enabled is not None:
                updated.padding_detector_enabled = patch.padding_detector_enabled

            await conn.execute(
                """
                INSERT OR REPLACE INTO settings (
                    id, llm_model, model_routing_json, llm_api_keys_json, llm_api_base,
                    max_turns, tension_threshold, default_render_mixer_json,
                    target_platform, default_target_char_count, default_max_sent_len,
                    ending_hook_guard_enabled, padding_detector_enabled,
                    daily_streak_count, last_commit_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "single_row_lock",
                    updated.llm_model,
                    updated.model_routing.model_dump_json() if updated.model_routing else None,
                    json.dumps(updated.llm_api_keys.model_dump()),
                    updated.llm_api_base,
                    updated.max_turns,
                    updated.tension_threshold,
                    json.dumps(updated.default_render_mixer.model_dump()),
                    updated.target_platform.value,
                    updated.default_target_char_count,
                    updated.default_max_sent_len,
                    int(updated.ending_hook_guard_enabled),
                    int(updated.padding_detector_enabled),
                    updated.daily_streak_count,
                    updated.last_commit_at.isoformat() if updated.last_commit_at else None,
                ),
            )
            await conn.commit()
        return {"status": "success", "settings": _settings_to_dict(updated)}
    except Exception as e:
        logger.error(f"Failed to patch settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
