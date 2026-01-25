import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user
from open_webui.constants import ERROR_MESSAGES

log = logging.getLogger(__name__)

router = APIRouter()


############################
# Gemini API Configuration
############################


@router.get("/config")
async def get_gemini_config(request: Request, user=Depends(get_verified_user)):
    """
    Get Gemini API configuration.
    """
    # AppConfig.__getattr__ returns the .value directly, not the PersistentConfig object
    # So we can access it directly
    try:
        api_key = getattr(request.app.state.config, "GEMINI_API_KEY", "") or ""
        log.debug(f"Retrieved GEMINI_API_KEY from config, length: {len(api_key) if api_key else 0}")
    except AttributeError as e:
        log.warning(f"AttributeError getting GEMINI_API_KEY: {e}")
        api_key = ""
    except Exception as e:
        log.error(f"Error getting GEMINI_API_KEY: {e}")
        api_key = ""
    
    try:
        base_url = (
            getattr(request.app.state.config, "GEMINI_API_BASE_URL", "")
            or "https://generativelanguage.googleapis.com"
        )
    except AttributeError:
        base_url = "https://generativelanguage.googleapis.com"
    
    result = {
        "GEMINI_API_KEY": api_key,
        "GEMINI_API_BASE_URL": base_url,
    }
    log.debug(f"Returning Gemini config: key_length={len(api_key) if api_key else 0}, base_url={base_url}")
    return result


class GeminiConfigForm(BaseModel):
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_API_BASE_URL: Optional[str] = None


@router.post("/config/update")
async def update_gemini_config(
    request: Request,
    form_data: GeminiConfigForm,
    user=Depends(get_verified_user),
):
    """
    Update Gemini API configuration.
    Only admins can update the configuration.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED
        )

    try:
        # Update config in app state (this will automatically save via PersistentConfig)
        # The AppConfig.__setattr__ will automatically call .save() on the PersistentConfig object
        if form_data.GEMINI_API_KEY is not None:
            log.info(f"Updating GEMINI_API_KEY (length: {len(form_data.GEMINI_API_KEY) if form_data.GEMINI_API_KEY else 0})")
            request.app.state.config.GEMINI_API_KEY = form_data.GEMINI_API_KEY
        if form_data.GEMINI_API_BASE_URL is not None:
            log.info(f"Updating GEMINI_API_BASE_URL to: {form_data.GEMINI_API_BASE_URL}")
            request.app.state.config.GEMINI_API_BASE_URL = form_data.GEMINI_API_BASE_URL

        # AppConfig.__getattr__ returns the .value directly
        try:
            gemini_key = getattr(request.app.state.config, "GEMINI_API_KEY", "") or ""
        except AttributeError:
            gemini_key = ""
        
        try:
            gemini_base_url = (
                getattr(request.app.state.config, "GEMINI_API_BASE_URL", "")
                or "https://generativelanguage.googleapis.com"
            )
        except AttributeError:
            gemini_base_url = "https://generativelanguage.googleapis.com"
        
        log.info(f"Gemini config updated - Key length: {len(gemini_key)}, Base URL: {gemini_base_url}")

        return {
            "GEMINI_API_KEY": gemini_key,
            "GEMINI_API_BASE_URL": gemini_base_url,
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/key")
async def get_gemini_key(request: Request, user=Depends(get_verified_user)):
    """
    Get Gemini API key (returns empty if not configured).
    """
    # AppConfig.__getattr__ returns the .value directly
    try:
        key = getattr(request.app.state.config, "GEMINI_API_KEY", "") or ""
    except AttributeError:
        key = ""
    
    return {"GEMINI_API_KEY": key}
