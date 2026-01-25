import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user, get_admin_user
from open_webui.constants import ERROR_MESSAGES

log = logging.getLogger(__name__)

router = APIRouter()


############################
# Twilio Configuration
############################


@router.get("/config")
async def get_twilio_config(request: Request, user=Depends(get_verified_user)):
    """
    Get Twilio configuration.
    """
    try:
        account_sid = getattr(request.app.state.config, "TWILIO_ACCOUNT_SID", "") or ""
        auth_token = getattr(request.app.state.config, "TWILIO_AUTH_TOKEN", "") or ""
        phone_number = getattr(request.app.state.config, "TWILIO_PHONE_NUMBER", "") or ""
        enable_twilio = getattr(request.app.state.config, "ENABLE_TWILIO", False)
    except AttributeError as e:
        log.warning(f"AttributeError getting Twilio config: {e}")
        account_sid = ""
        auth_token = ""
        phone_number = ""
        enable_twilio = False
    except Exception as e:
        log.error(f"Error getting Twilio config: {e}")
        account_sid = ""
        auth_token = ""
        phone_number = ""
        enable_twilio = False
    
    result = {
        "TWILIO_ACCOUNT_SID": account_sid,
        "TWILIO_AUTH_TOKEN": auth_token,
        "TWILIO_PHONE_NUMBER": phone_number,
        "ENABLE_TWILIO": enable_twilio,
    }
    log.debug(f"Returning Twilio config: account_sid_length={len(account_sid) if account_sid else 0}, enable={enable_twilio}")
    return result


class TwilioConfigForm(BaseModel):
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    ENABLE_TWILIO: Optional[bool] = None


@router.post("/config/update")
async def update_twilio_config(
    request: Request,
    form_data: TwilioConfigForm,
    user=Depends(get_admin_user),
):
    """
    Update Twilio configuration.
    Only admins can update the configuration.
    """
    try:
        # Update config in app state (this will automatically save via PersistentConfig)
        if form_data.TWILIO_ACCOUNT_SID is not None:
            log.info(f"Updating TWILIO_ACCOUNT_SID (length: {len(form_data.TWILIO_ACCOUNT_SID) if form_data.TWILIO_ACCOUNT_SID else 0})")
            request.app.state.config.TWILIO_ACCOUNT_SID = form_data.TWILIO_ACCOUNT_SID
        
        if form_data.TWILIO_AUTH_TOKEN is not None:
            log.info(f"Updating TWILIO_AUTH_TOKEN (length: {len(form_data.TWILIO_AUTH_TOKEN) if form_data.TWILIO_AUTH_TOKEN else 0})")
            request.app.state.config.TWILIO_AUTH_TOKEN = form_data.TWILIO_AUTH_TOKEN
        
        if form_data.TWILIO_PHONE_NUMBER is not None:
            log.info(f"Updating TWILIO_PHONE_NUMBER to: {form_data.TWILIO_PHONE_NUMBER}")
            request.app.state.config.TWILIO_PHONE_NUMBER = form_data.TWILIO_PHONE_NUMBER
        
        if form_data.ENABLE_TWILIO is not None:
            log.info(f"Updating ENABLE_TWILIO to: {form_data.ENABLE_TWILIO}")
            request.app.state.config.ENABLE_TWILIO = form_data.ENABLE_TWILIO

        # Get updated values
        try:
            account_sid = getattr(request.app.state.config, "TWILIO_ACCOUNT_SID", "") or ""
        except AttributeError:
            account_sid = ""
        
        try:
            auth_token = getattr(request.app.state.config, "TWILIO_AUTH_TOKEN", "") or ""
        except AttributeError:
            auth_token = ""
        
        try:
            phone_number = getattr(request.app.state.config, "TWILIO_PHONE_NUMBER", "") or ""
        except AttributeError:
            phone_number = ""
        
        try:
            enable_twilio = getattr(request.app.state.config, "ENABLE_TWILIO", False)
        except AttributeError:
            enable_twilio = False
        
        log.info(f"Twilio config updated - Account SID length: {len(account_sid)}, Phone: {phone_number}, Enable: {enable_twilio}")

        return {
            "TWILIO_ACCOUNT_SID": account_sid,
            "TWILIO_AUTH_TOKEN": auth_token,
            "TWILIO_PHONE_NUMBER": phone_number,
            "ENABLE_TWILIO": enable_twilio,
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )
