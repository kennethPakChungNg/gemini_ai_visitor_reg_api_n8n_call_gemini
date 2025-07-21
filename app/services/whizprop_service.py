import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import aiohttp
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class BlockInfo:
    Id: int
    NameChi: str
    NameEng: str
    Seq: int

@dataclass
class FloorInfo:
    Id: int
    BlockId: int
    NameChi: str
    NameEng: str
    Seq: int

@dataclass
class UnitInfo:
    Id: int
    FloorId: int
    NameChi: str
    NameEng: str
    Seq: int

@dataclass
class CategoryInfo:
    Id: int
    NameChi: str
    NameEng: str
    Seq: int

@dataclass
class BuildingSetting:
    block_list: List[BlockInfo]
    floor_list: List[FloorInfo]
    unit_list: List[UnitInfo]
    category_list: List[CategoryInfo]

@dataclass
class WhizPropAuth:
    access_token: str
    expires_at: datetime
    refresh_token: Optional[str] = None

class WhizPropService:
    def __init__(self):
        self.base_url = os.getenv("WHIZPROP_BASE_URL", "").rstrip("/")
        self.device_id = os.getenv("WHIZPROP_DEVICE_ID")
        self.username = os.getenv("WHIZPROP_USERNAME")
        self.password = os.getenv("WHIZPROP_PASSWORD")
        self.auth: Optional[WhizPropAuth] = None
        self._auth_lock = asyncio.Lock()
        
        if not all([self.base_url, self.device_id, self.username, self.password]):
            raise ValueError("Missing required WhizProp configuration")
        
        logger.info(f"WhizPropService initialized with base_url: {self.base_url}")

    async def _is_token_expired(self) -> bool:
        """Check if current token is expired or will expire soon (within 5 minutes)"""
        if not self.auth:
            return True
        
        # Add 5-minute buffer before actual expiration
        buffer_time = timedelta(minutes=5)
        return datetime.now() >= (self.auth.expires_at - buffer_time)

    async def _authenticate(self) -> bool:
        """Authenticate and get access token"""
        auth_url = f"{self.base_url}/Authorization/Login"
        
        auth_data = {
            "deviceId": self.device_id,
            "username": self.username,
            "password": self.password
        }
        
        try:
            logger.info("Attempting to authenticate with WhizProp API...")
            async with aiohttp.ClientSession() as session:
                async with session.post(auth_url, json=auth_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if result.get("status") == 1 and result.get("data"):
                            token_data = result["data"]
                            access_token = token_data.get("AccessToken")
                            expires_in = token_data.get("ExpiresIn", 3600)  # Default 1 hour
                            
                            if access_token:
                                # Calculate expiration time
                                expires_at = datetime.now() + timedelta(seconds=expires_in)
                                
                                self.auth = WhizPropAuth(
                                    access_token=access_token,
                                    expires_at=expires_at,
                                    refresh_token=token_data.get("RefreshToken")
                                )
                                
                                logger.info(f"Authentication successful. Token expires at: {expires_at}")
                                return True
                        
                        logger.error(f"Authentication failed: {result}")
                        return False
                    else:
                        error_text = await response.text()
                        logger.error(f"Authentication request failed with status {response.status}: {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False

    async def _ensure_valid_token(self) -> bool:
        """Ensure we have a valid, non-expired token"""
        async with self._auth_lock:
            if await self._is_token_expired():
                logger.info("Token expired or missing, refreshing...")
                return await self._authenticate()
            
            return True

    async def _make_authenticated_request(self, method: str, url: str, **kwargs) -> Optional[Dict[Any, Any]]:
        """Make an authenticated request with automatic token refresh"""
        max_retries = 2
        
        for attempt in range(max_retries):
            # Ensure we have a valid token
            if not await self._ensure_valid_token():
                logger.error("Failed to obtain valid authentication token")
                return None
            
            headers = kwargs.get("headers", {})
            headers["Authorization"] = f"Bearer {self.auth.access_token}"
            kwargs["headers"] = headers
            
            try:
                async with aiohttp.ClientSession() as session:
                    logger.debug(f"Making {method} request to {url}")
                    async with session.request(method, url, **kwargs) as response:
                        if response.status == 401:
                            # Token expired, force refresh and retry
                            logger.warning("Received 401, forcing token refresh")
                            self.auth = None  # Force re-authentication
                            if attempt < max_retries - 1:
                                continue
                        
                        if response.status == 200:
                            return await response.json()
                        else:
                            error_text = await response.text()
                            logger.error(f"Request failed with status {response.status}: {error_text}")
                            return None
                            
            except Exception as e:
                logger.error(f"Request error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    return None
                
        return None

    async def get_building_setting(self, building_id: int) -> Optional[BuildingSetting]:
        """Get building settings with automatic token refresh"""
        url = f"{self.base_url}/Visitor/GetVisitorBuildingSetting"
        params = {
            "deviceId": self.device_id,
            "BuildingId": building_id
        }
        
        logger.info(f"Fetching building setting for building ID: {building_id}")
        result = await self._make_authenticated_request("GET", url, params=params)
        
        if result and result.get("status") == 1:
            data = result.get("data", {})
            
            # Parse the response data
            building_setting = BuildingSetting(
                block_list=[BlockInfo(**block) for block in data.get("BlockList", [])],
                floor_list=[FloorInfo(**floor) for floor in data.get("FloorList", [])],
                unit_list=[UnitInfo(**unit) for unit in data.get("UnitList", [])],
                category_list=[CategoryInfo(**cat) for cat in data.get("VisitPurposeCategoryList", [])]
            )
            
            logger.info(f"Successfully retrieved building setting for building {building_id} - "
                       f"{len(building_setting.block_list)} blocks, "
                       f"{len(building_setting.floor_list)} floors, "
                       f"{len(building_setting.unit_list)} units")
            return building_setting
        else:
            logger.error(f"Failed to get building setting for building {building_id}: {result}")
            return None 