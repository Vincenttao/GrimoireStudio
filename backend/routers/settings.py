from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def get_settings():
    return {"settings": {}}

@router.patch("")
async def patch_settings():
    return {"status": "patched"}
