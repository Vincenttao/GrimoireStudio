from fastapi import APIRouter, Depends, HTTPException
import json
from backend.models import ProjectSettings, LLMApiKeys, DefaultRenderMixer
from backend.database import get_db_connection

router = APIRouter()

DEFAULT_SETTINGS = ProjectSettings(
    id="single_row_lock",
    llm_api_keys=LLMApiKeys(),
    llm_api_base=None,
    default_render_mixer=DefaultRenderMixer(
        pov_type="OMNISCIENT",
        style_template="Standard"
    )
)

from loguru import logger

@router.get("")
async def get_settings():
    try:
        async with get_db_connection() as conn:
            row = await conn.execute("SELECT * FROM settings WHERE id = 'single_row_lock'")
            res = await row.fetchone()
            if not res:
                logger.info("No settings found in DB, returning defaults.")
                return {"settings": DEFAULT_SETTINGS.model_dump()}
            
            data = dict(res)
            
            # Safe JSON parsing
            try:
                llm_api_keys = json.loads(data.get("llm_api_keys_json", "{}"))
            except Exception:
                logger.warning("Failed to parse llm_api_keys_json, using defaults.")
                llm_api_keys = DEFAULT_SETTINGS.llm_api_keys.model_dump()

            try:
                default_render_mixer = json.loads(data.get("default_render_mixer_json", "{}"))
            except Exception:
                logger.warning("Failed to parse default_render_mixer_json, using defaults.")
                default_render_mixer = DEFAULT_SETTINGS.default_render_mixer.model_dump()

            return {
                "settings": {
                    "id": data.get("id"),
                    "llm_model": data.get("llm_model") or "gpt-4",
                    "llm_api_keys": llm_api_keys,
                    "llm_api_base": data.get("llm_api_base"),
                    "max_turns": data.get("max_turns") if data.get("max_turns") is not None else 12,
                    "tension_threshold": data.get("tension_threshold") if data.get("tension_threshold") is not None else 0.8,
                    "default_render_mixer": default_render_mixer
                }
            }
    except Exception as e:
        logger.exception(f"Unexpected error in get_settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("")
async def patch_settings(settings: ProjectSettings):
    try:
        async with get_db_connection() as conn:
            await conn.execute(
                '''
                INSERT OR REPLACE INTO settings 
                (id, llm_model, llm_api_keys_json, llm_api_base, max_turns, tension_threshold, default_render_mixer_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    "single_row_lock",
                    settings.llm_model,
                    json.dumps(settings.llm_api_keys.model_dump()),
                    settings.llm_api_base,
                    settings.max_turns,
                    settings.tension_threshold,
                    json.dumps(settings.default_render_mixer.model_dump())
                )
            )
            await conn.commit()
        return {"status": "success", "settings": settings.model_dump()}
    except Exception as e:
        logger.error(f"Failed to patch settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
