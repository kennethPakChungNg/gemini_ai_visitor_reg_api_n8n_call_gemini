import httpx
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from app.config.settings import settings
from app.models.whizprop import WhizPropResponse, BuildingData
import logging

logger = logging.getLogger(__name__)


@dataclass
class AuthToken:
    access_token: str
    expires_at: datetime
    refresh_token: Optional[str] = None


class WhizPropAPIError(Exception):
    """WhizProp API specific exception."""
    pass


class WhizPropClient:
    """Client for WhizProp CS API integration with dynamic token management."""
    
    def __init__(self):
        self.base_url = settings.effective_base_url
        
        # Only need API key from environment (doesn't expire)
        self.api_key = settings.effective_api_key
        
        # Username/password for automatic authentication (optional)
        self.username = settings.whizprop_username
        self.password = settings.whizprop_password
        
        # Dynamic token management (no static tokens from .env)
        self._device_id: Optional[str] = settings.effective_device_id
        self._auth_token: Optional[AuthToken] = None
        self._auth_lock = asyncio.Lock()
        
        # Determine authentication capabilities
        self.can_get_tokens = bool(self.api_key)
        self.can_auto_login = bool(self.username and self.password)
        
        if not self.can_get_tokens:
            raise ValueError("API key is required for token management")
        
        logger.info(f"WhizProp client initialized with dynamic token management")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"Device ID: {self._device_id or 'Will retrieve dynamically'}")
        logger.info(f"API Key configured: {bool(self.api_key)}")
        logger.info(f"Can get tokens: {self.can_get_tokens}")
        logger.info(f"Can auto-login: {self.can_auto_login}")
    
    async def _is_token_expired(self) -> bool:
        """Check if current token is expired or will expire soon (within 5 minutes)"""
        if not self._auth_token:
            return True
        
        # Add 5-minute buffer before actual expiration
        buffer_time = timedelta(minutes=5)
        return datetime.now() >= (self._auth_token.expires_at - buffer_time)
    
    async def _get_fresh_token(self) -> bool:
        """Get a fresh token using RequestSessionToken endpoint"""
        device_id = await self.get_device_id()
        token_url = f"{self.base_url.rstrip('/')}/Account/RequestSessionToken"
        
        params = {
            "deviceId": device_id
        }
        
        headers = {
            "Apikey": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            logger.info("Getting fresh token using RequestSessionToken endpoint...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(token_url, headers=headers, params=params)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get("status") == 1 and result.get("data"):
                        token_data = result["data"]
                        access_token = token_data.get("access_token")
                        expires_in = token_data.get("expires_in", 7200)  # Default 2 hours
                        refresh_token = token_data.get("refresh_token")
                        
                        if access_token:
                            # Calculate expiration time
                            expires_at = datetime.now() + timedelta(seconds=expires_in)
                            
                            self._auth_token = AuthToken(
                                access_token=access_token,
                                expires_at=expires_at,
                                refresh_token=refresh_token
                            )
                            
                            logger.info(f"Fresh token obtained successfully. Expires at: {expires_at}")
                            return True
                    
                    logger.error(f"Failed to get fresh token: {result}")
                    return False
                else:
                    error_text = response.text
                    logger.error(f"Token request failed with status {response.status_code}: {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error getting fresh token: {str(e)}")
            return False
    
    async def _authenticate_with_credentials(self) -> bool:
        """Authenticate using username/password if available"""
        if not self.can_auto_login:
            return False
        
        auth_url = f"{self.base_url.rstrip('/')}/Authorization/Login"
        
        auth_data = {
            "deviceId": await self.get_device_id(),
            "username": self.username,
            "password": self.password
        }
        
        try:
            logger.info("Authenticating with username/password...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(auth_url, json=auth_data)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get("status") == 1 and result.get("data"):
                        token_data = result["data"]
                        access_token = token_data.get("AccessToken")
                        expires_in = token_data.get("ExpiresIn", 3600)  # Default 1 hour
                        
                        if access_token:
                            expires_at = datetime.now() + timedelta(seconds=expires_in)
                            
                            self._auth_token = AuthToken(
                                access_token=access_token,
                                expires_at=expires_at,
                                refresh_token=token_data.get("RefreshToken")
                            )
                            
                            logger.info(f"Authentication successful. Token expires at: {expires_at}")
                            return True
                    
                    logger.error(f"Authentication failed: {result}")
                    return False
                else:
                    error_text = response.text
                    logger.error(f"Authentication request failed with status {response.status_code}: {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    async def _ensure_valid_token(self) -> bool:
        """Ensure we have a valid, non-expired token"""
        async with self._auth_lock:
            if await self._is_token_expired():
                logger.info("Token expired or missing, getting fresh token...")
                
                # Try to get fresh token using API key first
                if await self._get_fresh_token():
                    return True
                
                # Fall back to credential-based authentication if available
                if self.can_auto_login:
                    logger.info("Trying credential-based authentication as fallback...")
                    if await self._authenticate_with_credentials():
                        return True
                
                logger.error("All token acquisition methods failed")
                return False
            
            return True
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get request headers with valid access token"""
        
        # Ensure we have a valid token
        if not await self._ensure_valid_token():
            raise WhizPropAPIError("Failed to obtain valid authentication token")
        
        # Use the current access token
        if self._auth_token:
            return {
                "Apikey": self.api_key,
                "Access_token": self._auth_token.access_token,
                "Content-Type": "application/json"
            }
        else:
            raise WhizPropAPIError("No valid authentication token available")
    
    async def _make_request(self, endpoint: str, method: str = "GET", params: Optional[Dict] = None, max_retries: int = 3) -> Dict[str, Any]:
        """Make HTTP request to WhizProp API with automatic token refresh on failures."""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        last_error = None
        
        for attempt in range(max_retries):
            try:
                headers = await self._get_headers()
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    if method.upper() == "GET":
                        response = await client.get(url, headers=headers, params=params or {})
                    elif method.upper() == "POST":
                        response = await client.post(url, headers=headers, params=params or {})
                    else:
                        raise WhizPropAPIError(f"Unsupported HTTP method: {method}")
                    
                    # Handle authentication failures
                    if response.status_code == 401:
                        error_text = response.text
                        logger.warning(f"Received 401 Unauthorized on attempt {attempt + 1}: {error_text}")
                        
                        # Force token refresh and retry
                        if attempt < max_retries - 1:
                            logger.info("Forcing token refresh due to 401")
                            self._auth_token = None  # Force fresh token
                            continue
                        else:
                            raise WhizPropAPIError("Authentication failed after multiple attempts")
                    
                    if response.status_code == 200:
                        return response.json()
                    else:
                        error_text = response.text
                        last_error = f"HTTP {response.status_code}: {error_text}"
                        logger.error(f"Request failed with status {response.status_code}: {error_text}")
                        
                        # Don't retry for non-auth errors
                        if response.status_code != 401:
                            raise WhizPropAPIError(last_error)
                            
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP error: {e.response.status_code}"
                logger.error(f"WhizProp API HTTP error: {e.response.status_code} - {e.response.text}")
            except httpx.RequestError as e:
                last_error = f"Request error: {str(e)}"
                logger.error(f"WhizProp API request error: {str(e)}")
            except WhizPropAPIError:
                # Re-raise WhizPropAPIError as-is
                raise
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.error(f"WhizProp API unexpected error: {str(e)}")
        
        raise WhizPropAPIError(f"Max retries exceeded. Last error: {last_error}")
    
    async def _make_unauthenticated_request(self, endpoint: str, method: str = "GET", params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request without access token (for getting device ID)."""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        headers = {
            "Apikey": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers, params=params or {})
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, params=params or {})
                else:
                    raise WhizPropAPIError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"WhizProp API HTTP error: {e.response.status_code} - {e.response.text}")
            raise WhizPropAPIError(f"API request failed: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"WhizProp API request error: {str(e)}")
            raise WhizPropAPIError(f"Request failed: {str(e)}")
        except Exception as e:
            logger.error(f"WhizProp API unexpected error: {str(e)}")
            raise WhizPropAPIError(f"Unexpected error: {str(e)}")
    
    async def get_device_id(self) -> str:
        """Get or retrieve device ID for API authentication."""
        
        # If device_id is configured in settings, use it
        if self._device_id:
            return self._device_id
        
        # Otherwise, retrieve device ID from API
        try:
            response_data = await self._make_unauthenticated_request(
                "Account/GetLandingInfo",
                method="POST",
                params={
                    "NotificationProvider": "2",
                    "Lang": "1", 
                    "Reg_id": "Simulator",
                    "Appver": "1",
                    "Osver": "Simulator",
                    "MobileModel": "Simulator",
                    "ShowNotification": "1",
                    "DeviceId": ""
                }
            )
            
            if response_data.get("status") == 1:
                self._device_id = response_data["data"]["deviceId"]
                logger.info(f"Retrieved device ID: {self._device_id}")
                return self._device_id
            else:
                raise WhizPropAPIError(f"Failed to get device ID: {response_data.get('errMsg', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error getting device ID: {str(e)}")
            raise WhizPropAPIError(f"Device ID retrieval failed: {str(e)}")
    
    async def get_building_settings(self, building_id: int) -> BuildingData:
        """Get building settings including blocks, floors, and flats."""
        try:
            device_id = await self.get_device_id()
            
            response_data = await self._make_request(
                "Visitor/GetVisitorBuildingSetting",
                method="POST",
                params={
                    "deviceId": device_id,
                    "BuildingId": building_id
                }
            )
            
            # Parse response using Pydantic model
            whizprop_response = WhizPropResponse(**response_data)
            
            if whizprop_response.status == 1:
                logger.info(f"Successfully retrieved building settings for building {building_id} - "
                           f"{len(whizprop_response.data.BlockList)} blocks, "
                           f"{len(whizprop_response.data.FloorList)} floors, "
                           f"{len(whizprop_response.data.UnitList)} units")
                return whizprop_response.data
            else:
                raise WhizPropAPIError(f"Building settings request failed: {whizprop_response.errMsg}")
                
        except Exception as e:
            logger.error(f"Error getting building settings: {str(e)}")
            if isinstance(e, WhizPropAPIError):
                raise
            raise WhizPropAPIError(f"Building settings retrieval failed: {str(e)}")
    
    async def find_block_by_name(self, building_data: BuildingData, block_name: str) -> Optional[int]:
        """Find block ID by Chinese or English name."""
        block_name_clean = block_name.strip().upper()
        
        for block in building_data.BlockList:
            if (block_name_clean in block.NameChi.upper() or 
                block_name_clean in block.NameEng.upper() or
                block_name_clean == str(block.Seq)):
                return block.Id
        return None
    
    async def find_floor_by_name(self, building_data: BuildingData, block_id: int, floor_name: str) -> Optional[int]:
        """Find floor ID by name within a specific block."""
        floor_name_clean = floor_name.strip().upper()
        
        for floor in building_data.FloorList:
            if floor.BlockId == block_id:
                if (floor_name_clean in floor.NameChi.upper() or 
                    floor_name_clean in floor.NameEng.upper() or
                    floor_name_clean == str(floor.Seq)):
                    return floor.Id
        return None
    
    async def find_flat_by_name(self, building_data: BuildingData, floor_id: int, flat_name: str) -> Optional[int]:
        """Find flat ID by name within a specific floor."""
        flat_name_clean = flat_name.strip().upper()
        
        for flat in building_data.UnitList:
            if flat.FloorId == floor_id:
                if (flat_name_clean in flat.NameChi.upper() or 
                    flat_name_clean in flat.NameEng.upper()):
                    return flat.Id
        return None


# Global instance
whizprop_client = WhizPropClient() 