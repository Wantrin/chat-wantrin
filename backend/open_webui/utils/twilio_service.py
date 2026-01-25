"""
Twilio service for making phone calls with AI integration.
"""
import logging
from typing import Optional
from urllib.parse import urljoin

log = logging.getLogger(__name__)


class TwilioService:
    """Service for handling Twilio phone calls and SMS."""
    
    def __init__(self, account_sid: str, auth_token: str, phone_number: str):
        """
        Initialize Twilio service.
        
        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            phone_number: Twilio phone number to use for calls and SMS
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.phone_number = phone_number
        self._client = None
        
    def _get_client(self):
        """Lazy load Twilio client."""
        if self._client is None:
            try:
                from twilio.rest import Client
                self._client = Client(self.account_sid, self.auth_token)
            except ImportError:
                log.error("Twilio library not installed. Install it with: pip install twilio")
                raise ImportError("Twilio library is required. Install it with: pip install twilio")
        return self._client
    
    def make_call(
        self,
        to_phone: str,
        webhook_url: str,
        call_id: str,
        context: Optional[dict] = None,
        enable_media_streams: bool = True,
        media_stream_url: Optional[str] = None
    ) -> Optional[str]:
        """
        Make a phone call using Twilio with optional Media Streams.
        
        Args:
            to_phone: Phone number to call (E.164 format)
            webhook_url: URL for Twilio webhook callbacks
            call_id: Unique call identifier
            context: Additional context data
            enable_media_streams: Enable Media Streams for real-time audio
            media_stream_url: WebSocket URL for Media Streams
            
        Returns:
            Twilio call SID if successful, None otherwise
        """
        try:
            client = self._get_client()
            
            # Build webhook URL with call_id parameter
            webhook_with_params = f"{webhook_url}?call_id={call_id}"
            if context:
                import json
                import base64
                context_str = base64.b64encode(json.dumps(context).encode()).decode()
                webhook_with_params += f"&context={context_str}"
            
            # Prepare call parameters
            call_params = {
                'to': to_phone,
                'from_': self.phone_number,
                'url': webhook_with_params,
                'method': 'POST',
                'status_callback': webhook_url.replace('/voice', '/status') if '/voice' in webhook_url else f"{webhook_url}/status",
                'status_callback_event': ['initiated', 'ringing', 'answered', 'completed'],
                'status_callback_method': 'POST'
            }
            
            # Add Media Streams if enabled
            if enable_media_streams and media_stream_url:
                call_params['stream'] = {
                    'url': media_stream_url,
                    'name': f'call_{call_id}'
                }
            
            # Make the call
            call = client.calls.create(**call_params)
            
            log.info(f"Twilio call initiated: SID={call.sid}, To={to_phone}, From={self.phone_number}, MediaStreams={enable_media_streams}")
            return call.sid
            
        except ImportError:
            log.error("Twilio library not installed")
            return None
        except Exception as e:
            log.exception(f"Failed to make Twilio call: {e}")
            return None
    
    def send_sms(
        self,
        to_phone: str,
        message: str,
        status_callback_url: Optional[str] = None
    ) -> Optional[str]:
        """
        Send an SMS message using Twilio.
        
        Args:
            to_phone: Phone number to send SMS to (E.164 format)
            message: Message content (max 1600 characters for single message)
            status_callback_url: Optional URL for delivery status callbacks
            
        Returns:
            Twilio message SID if successful, None otherwise
        """
        try:
            client = self._get_client()
            
            # Prepare message parameters
            message_params = {
                'to': to_phone,
                'from_': self.phone_number,
                'body': message
            }
            
            # Add status callback if provided
            if status_callback_url:
                message_params['status_callback'] = status_callback_url
                message_params['status_callback_method'] = 'POST'
            
            # Send the SMS
            message = client.messages.create(**message_params)
            
            log.info(f"Twilio SMS sent: SID={message.sid}, To={to_phone}, From={self.phone_number}, Status={message.status}")
            return message.sid
            
        except ImportError:
            log.error("Twilio library not installed")
            return None
        except Exception as e:
            log.exception(f"Failed to send Twilio SMS: {e}")
            return None
    
    def send_sms_bulk(
        self,
        recipients: list[str],
        message: str,
        status_callback_url: Optional[str] = None
    ) -> dict[str, Optional[str]]:
        """
        Send SMS to multiple recipients.
        
        Args:
            recipients: List of phone numbers (E.164 format)
            message: Message content
            status_callback_url: Optional URL for delivery status callbacks
            
        Returns:
            Dictionary mapping phone numbers to message SIDs (or None if failed)
        """
        results = {}
        for phone in recipients:
            results[phone] = self.send_sms(phone, message, status_callback_url)
        return results
    
    def is_configured(self) -> bool:
        """Check if Twilio is properly configured."""
        return bool(self.account_sid and self.auth_token and self.phone_number)
