import httpx
import json
import re
from typing import Dict, Any, Optional, Tuple
from app.config.settings import settings
from app.models.whizprop import BuildingData
from app.models.responses import RawExtracted
import logging

logger = logging.getLogger(__name__)


class GeminiServiceError(Exception):
    """Gemini service specific exception."""
    pass


class GeminiService:
    """Service for AI text processing using n8n webhook that calls Gemini via VPN."""
    
    def __init__(self):
        # n8n webhook configuration
        self.n8n_webhook_url = "https://propman.necess.com.hk/webhook/7c694ca5-5e9c-4711-ad30-d4f06648be18"
        
        logger.info(f"Initializing GeminiService with n8n webhook: {self.n8n_webhook_url}")

    async def _make_n8n_request(self, prompt: str, building_data: BuildingData) -> str:
        """Make a request to n8n webhook which calls Gemini via VPN."""
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Prepare payload for n8n webhook
        payload = {
            "text_input": prompt,
            "building_data": {
                "BlockList": [{"Id": b.Id, "NameChi": b.NameChi, "NameEng": b.NameEng} for b in building_data.BlockList],
                "FloorList": [{"Id": f.Id, "BlockId": f.BlockId, "NameChi": f.NameChi, "NameEng": f.NameEng} for f in building_data.FloorList],
                "UnitList": [{"Id": u.Id, "FloorId": u.FloorId, "NameChi": u.NameChi, "NameEng": u.NameEng} for u in building_data.UnitList],
                "VisitCat": [{"Id": v.Id, "NameChi": v.NameChi, "NameEng": v.NameEng} for v in building_data.VisitCat] if building_data.VisitCat else [],
                "VisitSubCat": [{"VisitCatId": vs.VisitCatId, "NameChi": vs.NameChi, "NameEng": vs.NameEng} for vs in building_data.VisitSubCat] if building_data.VisitSubCat else []
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                logger.info(f"Sending request to n8n webhook...")
                response = await client.post(self.n8n_webhook_url, headers=headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"n8n webhook raw response: {result}")
                
                # Check if n8n response indicates success
                if result.get('status') == 'success':
                    # Extract the parsed data from n8n response
                    data = result.get('data', {})
                    
                    # Convert n8n response back to Gemini-like JSON format for compatibility
                    gemini_format = {
                        "visitor_name": data.get('visitor_name'),
                        "block_id": data.get('block_id'),
                        "floor_id": data.get('floor_id'), 
                        "flat_id": data.get('flat_id'),
                        "id_card_prefix": data.get('id_card_prefix'),
                        "main_category": data.get('main_category'),
                        "sub_category": data.get('sub_category'),
                        "confidence": data.get('confidence', 0.8)
                    }
                    
                    # Return as JSON string to match original _make_request behavior
                    return json.dumps(gemini_format)
                    
                elif result.get('status') == 'error':
                    error_msg = result.get('message', 'Unknown error from n8n')
                    logger.error(f"n8n webhook returned error: {error_msg}")
                    raise GeminiServiceError(f"n8n processing failed: {error_msg}")
                else:
                    logger.error(f"Invalid n8n response structure: {result}")
                    raise GeminiServiceError("Invalid response from n8n webhook")
                
            except httpx.HTTPStatusError as e:
                logger.error(f"n8n webhook HTTP error: {e.response.status_code} - {e.response.text}")
                raise GeminiServiceError(f"n8n webhook request failed: {e.response.status_code}")
            except httpx.RequestError as e:
                logger.error(f"n8n webhook request error: {str(e)}")
                raise GeminiServiceError(f"n8n webhook connection failed: {str(e)}")
            except Exception as e:
                logger.error(f"n8n webhook unexpected error: {str(e)}")
                raise GeminiServiceError(f"n8n webhook unexpected error: {str(e)}")

    def _validate_and_convert_id(self, extracted_value: Any, item_list: list, item_type: str) -> Optional[int]:
        """
        Validate and convert name/ID to actual ID.
        """
        logger.info(f"Validating {item_type}: extracted_value='{extracted_value}', type={type(extracted_value)}")
        
        if not extracted_value:
            logger.info(f"No {item_type} value to validate")
            return None
            
        # If it's already a number and exists in the list, return it
        if isinstance(extracted_value, (int, float)):
            extracted_id = int(extracted_value)
            if any(item.Id == extracted_id for item in item_list):
                return extracted_id
        
        # If it's a string that looks like a number
        if isinstance(extracted_value, str) and extracted_value.isdigit():
            extracted_id = int(extracted_value)
            if any(item.Id == extracted_id for item in item_list):
                return extracted_id
        
        # Try to match by name (Chinese or English)
        if isinstance(extracted_value, str):
            extracted_lower = extracted_value.lower()
            
            # First try exact match (most reliable)
            for item in item_list:
                if (extracted_value == item.NameChi or 
                    extracted_value == item.NameEng):
                    logger.info(f"Found exact {item_type} match: {extracted_value} → {item.NameChi} (ID: {item.Id})")
                    return item.Id
            
            # Then try partial matching
            for item in item_list:
                item_name_chi = str(item.NameChi).lower() if item.NameChi else ""
                item_name_eng = str(item.NameEng).lower() if item.NameEng else ""
                
                if (extracted_lower in item_name_chi or 
                    extracted_lower in item_name_eng or
                    item.NameChi in extracted_value or 
                    item.NameEng in extracted_value):
                    logger.info(f"Found partial {item_type} match: {extracted_value} → {item.NameChi} (ID: {item.Id})")
                    return item.Id
        
        # If no match found, return None (don't guess!)
        logger.warning(f"Could not find {item_type} for '{extracted_value}' in available options")
        return None

    def _validate_and_convert_floor_id(self, extracted_value: Any, floor_list: list, block_id: Optional[int]) -> Optional[int]:
        """
        Validate and convert floor name/ID to actual floor ID, considering the block.
        """
        if not extracted_value:
            return None
            
        # If it's already a number and exists in the list, return it
        if isinstance(extracted_value, (int, float)):
            extracted_id = int(extracted_value)
            if any(floor.Id == extracted_id for floor in floor_list):
                return extracted_id
        
        # If it's a string that looks like a number
        if isinstance(extracted_value, str) and extracted_value.isdigit():
            extracted_id = int(extracted_value)
            if any(floor.Id == extracted_id for floor in floor_list):
                return extracted_id
        
        # Try to match by name, preferring floors in the same block
        if isinstance(extracted_value, str):
            extracted_lower = extracted_value.lower()
            
            # First try to find in the same block
            if block_id:
                # Try exact match first in the same block
                for floor in floor_list:
                    if (floor.BlockId == block_id and 
                        (extracted_value == floor.NameChi or extracted_value == floor.NameEng)):
                        logger.info(f"Found exact floor match in block {block_id}: {extracted_value} → {floor.NameChi} (ID: {floor.Id})")
                        return floor.Id
                
                # Then try partial match in the same block
                for floor in floor_list:
                    if floor.BlockId == block_id:
                        floor_name_chi = str(floor.NameChi).lower() if floor.NameChi else ""
                        floor_name_eng = str(floor.NameEng).lower() if floor.NameEng else ""
                        
                        if (extracted_lower in floor_name_chi or 
                            extracted_lower in floor_name_eng or
                            floor.NameChi in extracted_value or 
                            floor.NameEng in extracted_value):
                            logger.info(f"Found partial floor match in block {block_id}: {extracted_value} → {floor.NameChi} (ID: {floor.Id})")
                            return floor.Id
            
            # Then try to find anywhere (exact match first, then partial)
            # Try exact match in any floor
            for floor in floor_list:
                if extracted_value == floor.NameChi or extracted_value == floor.NameEng:
                    logger.info(f"Found exact floor match anywhere: {extracted_value} → {floor.NameChi} (ID: {floor.Id})")
                    return floor.Id
            
            # Try partial match in any floor
            for floor in floor_list:
                floor_name_chi = str(floor.NameChi).lower() if floor.NameChi else ""
                floor_name_eng = str(floor.NameEng).lower() if floor.NameEng else ""
                
                if (extracted_lower in floor_name_chi or 
                    extracted_lower in floor_name_eng or
                    floor.NameChi in extracted_value or 
                    floor.NameEng in extracted_value):
                    logger.info(f"Found partial floor match anywhere: {extracted_value} → {floor.NameChi} (ID: {floor.Id})")
                    return floor.Id
        
        # If no match found, return None (don't guess!)
        logger.warning(f"Could not find floor '{extracted_value}' in the specified block {block_id}")
        return None

    def _validate_and_convert_flat_id(self, extracted_value: Any, unit_list: list, floor_id: Optional[int]) -> Optional[int]:
        """
        Validate and convert flat name/ID to actual flat ID, considering the floor.
        """
        if not extracted_value:
            return None
            
        # If it's already a number and exists in the list, check if it's on the correct floor
        if isinstance(extracted_value, (int, float)):
            extracted_id = int(extracted_value)
            for unit in unit_list:
                if unit.Id == extracted_id:
                    # If we have a floor constraint, make sure the unit is on that floor
                    if floor_id and unit.FloorId != floor_id:
                        logger.warning(f"Unit ID {extracted_id} exists but is on floor {unit.FloorId}, not the expected floor {floor_id}")
                        break  # Don't return this unit, continue with name matching
                    return extracted_id
        
        # If it's a string that looks like a number
        if isinstance(extracted_value, str) and extracted_value.isdigit():
            extracted_id = int(extracted_value)
            for unit in unit_list:
                if unit.Id == extracted_id:
                    # If we have a floor constraint, make sure the unit is on that floor
                    if floor_id and unit.FloorId != floor_id:
                        logger.warning(f"Unit ID {extracted_id} exists but is on floor {unit.FloorId}, not the expected floor {floor_id}")
                        break  # Don't return this unit, continue with name matching
                    return extracted_id
        
        # Try to match by name, preferring units on the same floor
        if isinstance(extracted_value, str):
            extracted_lower = extracted_value.lower()
            
            # First try to find on the same floor
            if floor_id:
                # Debug: show available units on this floor
                units_on_floor = [unit for unit in unit_list if unit.FloorId == floor_id]
                logger.info(f"Units available on floor {floor_id}: {[(unit.NameChi, unit.Id) for unit in units_on_floor]}")
                # Try exact match first on the same floor
                for unit in unit_list:
                    if (unit.FloorId == floor_id and 
                        (extracted_value == unit.NameChi or extracted_value == unit.NameEng)):
                        logger.info(f"Found exact unit match on floor {floor_id}: {extracted_value} → {unit.NameChi} (ID: {unit.Id})")
                        return unit.Id
                
                # Then try partial match on the same floor
                for unit in unit_list:
                    if unit.FloorId == floor_id:
                        unit_name_chi = str(unit.NameChi).lower() if unit.NameChi else ""
                        unit_name_eng = str(unit.NameEng).lower() if unit.NameEng else ""
                        
                        if (extracted_lower in unit_name_chi or 
                            extracted_lower in unit_name_eng or
                            unit.NameChi in extracted_value or 
                            unit.NameEng in extracted_value):
                            logger.info(f"Found partial unit match on floor {floor_id}: {extracted_value} → {unit.NameChi} (ID: {unit.Id})")
                            return unit.Id
            
            # If we have a valid floor_id, DON'T look for units on other floors
            # This prevents incorrect mapping like finding "B室" on floor 2 when we need "B室" on floor 4
            if floor_id:
                logger.warning(f"Could not find unit '{extracted_value}' on the specified floor {floor_id}. Not searching other floors to avoid incorrect mapping.")
                # Return None to force fallback behavior in calling function
                return None
            
            # Only search anywhere if we don't have a specific floor constraint
            # Try exact match in any unit (only if no floor_id constraint)
            for unit in unit_list:
                if extracted_value == unit.NameChi or extracted_value == unit.NameEng:
                    logger.info(f"Found exact unit match anywhere (no floor constraint): {extracted_value} → {unit.NameChi} (ID: {unit.Id}, FloorId: {unit.FloorId})")
                    return unit.Id
            
            # Try partial match in any unit (only if no floor_id constraint)
            for unit in unit_list:
                unit_name_chi = str(unit.NameChi).lower() if unit.NameChi else ""
                unit_name_eng = str(unit.NameEng).lower() if unit.NameEng else ""
                
                if (extracted_lower in unit_name_chi or 
                    extracted_lower in unit_name_eng or
                    unit.NameChi in extracted_value or 
                    unit.NameEng in extracted_value):
                    logger.info(f"Found partial unit match anywhere (no floor constraint): {extracted_value} → {unit.NameChi} (ID: {unit.Id}, FloorId: {unit.FloorId})")
                    return unit.Id
        
        # If no match found, return None (don't guess!)
        logger.warning(f"Could not find unit '{extracted_value}' on the specified floor {floor_id}")
        return None

    def _convert_category_name_to_id(self, category_name: str, visit_categories: list) -> Optional[int]:
        """Convert category name to ID."""
        if not category_name or not visit_categories:
            return None
            
        # Convert to string if it's not already
        category_name = str(category_name)
            
        # Common mappings
        category_mappings = {
            "探訪": 19,
            "visit": 19,
            "visiting": 19,
            "外賣": 20,
            "delivery": 20,
            "送外賣": 20,
            "food delivery": 20
        }
        
        # Check direct mapping first
        for key, cat_id in category_mappings.items():
            if key.lower() in category_name.lower():
                return cat_id
        
        # Try to match with actual category list
        for category in visit_categories:
            if (category.NameChi in category_name or 
                category.NameEng.lower() in category_name.lower() or
                category_name in category.NameChi or
                category_name.lower() in category.NameEng.lower()):
                return category.Id
        
        # Default fallback
        return 20  # Default to delivery

    def _get_validation_suggestions(self, extracted_value: str, item_list: list, item_type: str, parent_constraint: Optional[int] = None) -> list:
        """Get suggestions for invalid apartment components."""
        suggestions = []
        
        if not extracted_value or not item_list:
            return suggestions
        
        # Find similar names (fuzzy matching)
        extracted_lower = extracted_value.lower()
        
        for item in item_list:
            # Skip items that don't match parent constraint (e.g., floors not in the specified block)
            if item_type == "floor" and parent_constraint and hasattr(item, 'BlockId') and item.BlockId != parent_constraint:
                continue
            if item_type == "unit" and parent_constraint and hasattr(item, 'FloorId') and item.FloorId != parent_constraint:
                continue
                
            item_name = str(item.NameChi) if item.NameChi else ""
            
            # Check for similar patterns
            if (len(extracted_value) > 1 and len(item_name) > 1 and 
                (extracted_value[:-1] in item_name or item_name[:-1] in extracted_value or
                 abs(len(extracted_value) - len(item_name)) <= 1)):
                suggestions.append(item_name)
        
        # Remove duplicates and limit to 5 suggestions
        return list(set(suggestions))[:5]

    def _convert_subcategory_to_namechi(self, subcategory: Optional[str], visit_subcategories: list) -> Optional[str]:
        """Convert subcategory to NameChi string."""
        if not subcategory:
            return None
            
        # Convert to string if it's not already
        subcategory = str(subcategory)
            
        # Common mappings for delivery services
        subcategory_mappings = {
            "foodpanda": "FoodPanda",
            "熊猫": "FoodPanda", 
            "panda": "FoodPanda",
            "keeta": "Keeta",
            "美團": "Keeta",
            "meituan": "Keeta"
        }
        
        # Check direct mapping first
        for key, mapped_name in subcategory_mappings.items():
            if key.lower() in subcategory.lower():
                return mapped_name
        
        # Try to match with actual subcategory list (strict validation)
        if visit_subcategories:
            for subcat in visit_subcategories:
                if (subcat.NameChi in subcategory or 
                    subcat.NameEng.lower() in subcategory.lower() or
                    subcategory in subcat.NameChi or
                    subcategory.lower() in subcat.NameEng.lower()):
                    return subcat.NameChi
        
        # Return None if no valid mapping found (don't make up subcategories!)
        logger.warning(f"Invalid subcategory '{subcategory}' not found in valid list, returning None")
        return None

    def _create_visitor_prompt(self, text: str, building_data: BuildingData) -> str:
        """Create a detailed prompt for visitor information extraction with building context."""
        
        # Create building context
        building_context = f"Building has {len(building_data.BlockList)} blocks, {len(building_data.FloorList)} floors, {len(building_data.UnitList)} units."
        
        # Create COMPLETE building data in efficient format
        building_mappings = []
        
        # COMPLETE BLOCK MAPPING - All blocks
        building_mappings.append("=== COMPLETE BLOCK MAPPING ===")
        for block in building_data.BlockList:
            building_mappings.append(f"'{block.NameChi}' → {block.Id}")
        
        # COMPLETE FLOOR MAPPING - Organized by block for efficiency  
        building_mappings.append("\n=== COMPLETE FLOOR MAPPING ===")
        for block in building_data.BlockList:
            block_floors = [f for f in building_data.FloorList if f.BlockId == block.Id]
            if block_floors:
                building_mappings.append(f"Block {block.Id} ({block.NameChi}) floors:")
                for floor in block_floors:
                    building_mappings.append(f"  '{floor.NameChi}' → {floor.Id}")
        
        # COMPLETE UNIT MAPPING - Organized by floor for efficiency
        building_mappings.append("\n=== COMPLETE UNIT MAPPING ===")
        # Group units by floor to make it more readable and efficient
        floor_units = {}
        for unit in building_data.UnitList:
            if unit.FloorId not in floor_units:
                floor_units[unit.FloorId] = []
            floor_units[unit.FloorId].append(unit)
        
        # Show units organized by floor
        for floor_id, units in sorted(floor_units.items()):
            # Find the floor name for context
            floor_info = next((f for f in building_data.FloorList if f.Id == floor_id), None)
            if floor_info:
                building_mappings.append(f"Floor {floor_id} ({floor_info.NameChi} in Block {floor_info.BlockId}) units:")
                for unit in sorted(units, key=lambda u: u.Seq):  # Sort by sequence for readability
                    building_mappings.append(f"  '{unit.NameChi}' → {unit.Id}")
        
        # Categories with subcategories
        categories_text = [
            "探訪 (Visit) → main_category: 19",
            "外賣 (Delivery) → main_category: 20"
        ]
        
        # Add subcategories information
        if building_data.VisitSubCat:
            categories_text.append("\nVALID SUBCATEGORIES:")
            for subcat in building_data.VisitSubCat:
                categories_text.append(f"  For main_category {subcat.VisitCatId}: '{subcat.NameChi}' or '{subcat.NameEng}'")
            categories_text.append("IMPORTANT: sub_category must be EXACTLY one of the NameChi values above, or null if none match")

        prompt = f"""
You are an AI assistant helping to parse visitor registration information from voice-to-text input.

BUILDING INFORMATION:
{building_context}

COMPLETE BUILDING DATA FOR THIS BUILDING:
{chr(10).join(building_mappings)}

HOW TO USE THE BUILDING DATA:
1. Find the EXACT block name in the COMPLETE BLOCK MAPPING section
2. Find the EXACT floor name in the COMPLETE FLOOR MAPPING section for that block
3. Find the EXACT unit name in the COMPLETE UNIT MAPPING section for that floor

VISIT CATEGORIES:
{chr(10).join(categories_text)}

TASK: Parse the following visitor text and extract structured information:

INPUT TEXT: "{text}"

INSTRUCTIONS - EXTRACT EXACTLY WHAT YOU SEE IN THE TEXT:
1. STEP 1 - Extract BLOCK: Find exact pattern like "1座", "2座", "5座" in the text
2. STEP 2 - Extract FLOOR: Find exact pattern like "8樓", "11樓", "12樓", "15樓" in the text
3. STEP 3 - Extract UNIT: Find exact pattern like "A室", "B室", "C室", "D室" in the text
4. Extract visitor name (Chinese/English)
5. Extract first 4 characters/digits of ID card
6. Classify visit purpose into main category and sub-category

CRITICAL: You MUST extract the EXACT characters from the input text, not interpret or convert them!

CRITICAL ID MAPPING RULES (FOLLOW EXACTLY):
STEP 1: Extract "1座" from text → Find block where NameChi="1座" → block_id = that block's Id number (NOT the floor Id!)
STEP 2: Extract "11樓" from text → Find floor where NameChi="11樓" AND BlockId=block_id from step 1 → floor_id = that floor's Id number  
STEP 3: Extract "D室" from text → Find unit where NameChi="D室" AND FloorId=floor_id from step 2 → flat_id = that unit's Id number

⚠️  HIERARCHICAL VALIDATION RULES (CRITICAL):
- Floor MUST belong to the specified block (check BlockId matches)
- Unit MUST belong to the specified floor (check FloorId matches)  
- If "5座管理處" but 管理處 is in block 19, return block_id=4, floor_id=null, flat_id=null
- NEVER mix IDs from different blocks/floors - maintain parent-child relationships!

WARNING: DO NOT CONFUSE BLOCK_ID WITH FLOOR_ID!
- block_id is for "1座", "2座", "3座" etc. 
- floor_id is for "8樓", "10樓", "11樓" etc.
- flat_id is for "A室", "B室", "D室" etc.

EXAMPLE 1 - "去1座11樓D室":
STEP 1: Extract "1座" → Find block with NameChi="1座" → block_id = 1 
STEP 2: Extract "11樓" → Find floor with NameChi="11樓" AND BlockId=1 → floor_id = 4 
STEP 3: Extract "D室" → Find unit with NameChi="D室" AND FloorId=4 → flat_id = 16 
RESULT: block_id=1, floor_id=4, flat_id=16

EXAMPLE 2 - "去1座10樓D室":
STEP 1: Extract "1座" → Find block with NameChi="1座" → block_id = 1 
STEP 2: Extract "10樓" → Find floor with NameChi="10樓" AND BlockId=1 → floor_id = 3 
STEP 3: Extract "D室" → Find unit with NameChi="D室" AND FloorId=3 → flat_id = 12 
RESULT: block_id=1, floor_id=3, flat_id=12

EXAMPLE 3 - "去5座12樓C室":
STEP 1: Extract "5座" → Find block with NameChi="5座" → block_id = 4 
STEP 2: Extract "12樓" → Find floor with NameChi="12樓" AND BlockId=4 → floor_id = 40 
STEP 3: Extract "C室" → Find unit with NameChi="C室" AND FloorId=40 → flat_id = 156 
RESULT: block_id=4, floor_id=40, flat_id=156

EXAMPLE 4 - "去5座管理處" (HIERARCHICAL CONFLICT):
STEP 1: Extract "5座" → Find block with NameChi="5座" → block_id = 4
STEP 2: Extract "管理處" → Find floor with NameChi="管理處" → Found Id=190 BUT BlockId=19 (not 4!)
STEP 3: HIERARCHICAL VIOLATION: 管理處 exists in block 19, not block 4
RESULT: block_id=4, floor_id=null, flat_id=null (don't mix data from different blocks!)

TEXT EXTRACTION RULES:
- If text contains "5座", extract exactly "5座" (not 5, not "座5")
- If text contains "12樓", extract exactly "12樓" (not 12, not "樓12")  
- If text contains "C室", extract exactly "C室" (not C, not "室C")

RESPONSE FORMAT - YOU MUST RETURN VALID JSON ONLY:

CRITICAL EXTRACTION PROCESS (FOLLOW EXACTLY):
1. Read the input text carefully
2. Find EXACT Chinese characters for block (e.g., "5座", "6座")  
3. Find EXACT Chinese characters for floor (e.g., "12樓", "10樓")
4. Find EXACT Chinese characters for unit (e.g., "A室", "C室")
5. Use the COMPLETE BUILDING DATA above to map each extracted string to its database ID
6. For sub_category: ONLY use NameChi values from VALID SUBCATEGORIES above, or null

STEP-BY-STEP MAPPING PROCESS:
- Extract "6座" from text → Look in COMPLETE BLOCK MAPPING → "6座" → 5
- Extract "12樓" from text → Look in COMPLETE FLOOR MAPPING for Block 5 → "12樓" → 51  
- Extract "A室" from text → Look in COMPLETE UNIT MAPPING for Floor 51 → "A室" → 197

SUBCATEGORY RULES:
- If text mentions delivery services, use "FoodPanda" or "Keeta" ONLY
- If text says "送外賣" but no specific service, use null (don't make up subcategories)
- sub_category must be EXACTLY: "FoodPanda", "Keeta", or null

Example output for "去6座12樓A室探朋友":
{{
    "visitor_name": "李先生",
    "block_id": 5,
    "floor_id": 51,
    "flat_id": 197,
    "id_card_prefix": "7542",
    "main_category": 19,
    "sub_category": "探朋友",
    "confidence": 0.95
}}

CRITICAL REQUIREMENTS:
- Return ONLY the JSON object, no other text before or after
- Use actual database IDs from the building information above
- All field names must be exactly as shown in the example
- Numbers should be integers (not strings) for IDs
- confidence should be a decimal between 0 and 1

Your response:
"""
        return prompt

    async def extract_visitor_info(self, text: str, building_data: BuildingData) -> Tuple[Optional[RawExtracted], float]:
        """Extract visitor information from text using building context via n8n webhook."""
        try:
            prompt = self._create_visitor_prompt(text, building_data)
            
            # Get response from n8n webhook (which calls Gemini via VPN)
            response_text = await self._make_n8n_request(prompt, building_data)
            logger.info(f"n8n response: '{response_text}'")
            logger.info(f"Response length: {len(response_text) if response_text else 0} characters")
            
            # Check if response is empty
            if not response_text or not response_text.strip():
                logger.error(f"Empty response from n8n webhook")
                raise GeminiServiceError("Empty response from n8n webhook")
            
            # Try to extract JSON from response - be more flexible for different models
            response_text = response_text.strip()
            
            # First try to parse the entire response as JSON
            try:
                parsed_data = json.loads(response_text)
                logger.info(f"Successfully parsed entire response as JSON: {parsed_data}")
            except json.JSONDecodeError:
                # If that fails, try to extract JSON using regex
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if not json_match:
                    # If no JSON found, log the full response for debugging
                    logger.error(f"No JSON found in response. Full response: '{response_text}'")
                    logger.error(f"Response length: {len(response_text)} characters")
                    logger.error(f"Response type: {type(response_text)}")
                    
                    # Try to find if there's any structured data
                    if "visitor_name" in response_text.lower() or "block_id" in response_text.lower():
                        logger.info("Response contains visitor data but not in JSON format - trying to extract manually")
                        # For now, raise error with more context
                        raise GeminiServiceError(f"Response not in JSON format. Got: '{response_text[:200]}...'")
                    else:
                        raise GeminiServiceError(f"No structured data found in response: '{response_text[:200]}...'")
                
                json_text = json_match.group()
                logger.info(f"Extracted JSON: '{json_text}'")
                
                try:
                    parsed_data = json.loads(json_text)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing error: {str(e)}")
                    logger.error(f"Invalid JSON: {json_text}")
                    raise GeminiServiceError(f"Invalid JSON format: {str(e)}")
            
            # Validate required fields
            required_fields = ['visitor_name', 'block_id', 'floor_id', 'flat_id', 'id_card_prefix', 'main_category']
            for field in required_fields:
                if field not in parsed_data:
                    raise GeminiServiceError(f"Missing required field: {field}")
            
            # Extract confidence (default to 0.8 if not provided)
            confidence = float(parsed_data.get('confidence', 0.8))
            confidence = max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
            
            # Clean up "None" strings that AI might return when it can't identify data
            for field in ['block_id', 'floor_id', 'flat_id']:
                if str(parsed_data.get(field, '')).lower() in ['none', 'null', '']:
                    parsed_data[field] = None
            
            # Validate and convert IDs - collect validation errors instead of guessing  
            logger.info(f"Raw extracted values - block: {parsed_data.get('block_id')}, floor: {parsed_data.get('floor_id')}, flat: {parsed_data.get('flat_id')}")
            
            validation_errors = []
            
            # Validate block (only if AI extracted something)
            block_id = None
            if parsed_data.get('block_id') is not None:
                block_id = self._validate_and_convert_id(parsed_data['block_id'], building_data.BlockList, 'block')
                if block_id is None:
                    suggestions = self._get_validation_suggestions(str(parsed_data['block_id']), building_data.BlockList, 'block')
                    validation_errors.append({
                        "field": "block",
                        "extracted_value": str(parsed_data['block_id']),
                        "issue": "not_found",
                        "suggestions": suggestions
                    })
            logger.info(f"Converted block_id: {block_id}")
            
            # Validate floor (only if block is valid and AI extracted something)
            floor_id = None
            if block_id is not None and parsed_data.get('floor_id') is not None:
                floor_id = self._validate_and_convert_floor_id(parsed_data['floor_id'], building_data.FloorList, block_id)
                if floor_id is None:
                    suggestions = self._get_validation_suggestions(str(parsed_data['floor_id']), building_data.FloorList, 'floor', block_id)
                    validation_errors.append({
                        "field": "floor", 
                        "extracted_value": str(parsed_data['floor_id']),
                        "issue": "not_in_block",
                        "suggestions": suggestions
                    })
                else:
                    # CRITICAL: Verify floor actually belongs to the block  
                    floor_obj = next((f for f in building_data.FloorList if f.Id == floor_id), None)
                    if floor_obj and floor_obj.BlockId != block_id:
                        logger.warning(f"Hierarchical violation: floor_id {floor_id} belongs to block {floor_obj.BlockId}, not block {block_id}")
                        validation_errors.append({
                            "field": "floor",
                            "extracted_value": str(parsed_data['floor_id']),
                            "issue": "hierarchical_violation",
                            "suggestions": []
                        })
                        floor_id = None  # Reset invalid floor
            logger.info(f"Converted floor_id: {floor_id}")
            
            # Validate flat (only if floor is valid and AI extracted something)
            flat_id = None
            if floor_id is not None and parsed_data.get('flat_id') is not None:
                flat_id = self._validate_and_convert_flat_id(parsed_data['flat_id'], building_data.UnitList, floor_id)
                if flat_id is None:
                    suggestions = self._get_validation_suggestions(str(parsed_data['flat_id']), building_data.UnitList, 'unit', floor_id)
                    validation_errors.append({
                        "field": "flat",
                        "extracted_value": str(parsed_data['flat_id']),
                        "issue": "not_on_floor", 
                        "suggestions": suggestions
                    })
                else:
                    # CRITICAL: Verify unit actually belongs to the floor
                    unit_obj = next((u for u in building_data.UnitList if u.Id == flat_id), None)
                    if unit_obj and unit_obj.FloorId != floor_id:
                        logger.warning(f"Hierarchical violation: flat_id {flat_id} belongs to floor {unit_obj.FloorId}, not floor {floor_id}")
                        validation_errors.append({
                            "field": "flat",
                            "extracted_value": str(parsed_data['flat_id']),
                            "issue": "hierarchical_violation",
                            "suggestions": []
                        })
                        flat_id = None  # Reset invalid unit
            logger.info(f"Converted flat_id: {flat_id}")
            
            # If there are validation errors, log them but continue with partial data
            if validation_errors:
                logger.warning(f"Validation errors found, proceeding with partial data: {validation_errors}")
                # Reduce confidence score based on number of validation errors
                confidence = confidence * (1.0 - (len(validation_errors) * 0.2))  # Reduce by 20% per error
                confidence = max(0.1, confidence)  # Minimum 10% confidence
            
            # Debug: Show what was successfully validated
            if flat_id and building_data.UnitList:
                selected_unit = next((unit for unit in building_data.UnitList if unit.Id == flat_id), None)
                if selected_unit:
                    logger.info(f"Successfully validated apartment: {selected_unit.NameChi} (Id: {selected_unit.Id}, FloorId: {selected_unit.FloorId})")
            
            # Convert category name to ID
            main_category_id = self._convert_category_name_to_id(parsed_data['main_category'], building_data.VisitCat)
            
            # Validate and convert sub-category to NameChi string
            sub_category_str = self._convert_subcategory_to_namechi(parsed_data.get('sub_category'), building_data.VisitSubCat) if parsed_data.get('sub_category') else None
            
            # Create RawExtracted object
            raw_extracted = RawExtracted(
                visitor_name=str(parsed_data['visitor_name']),
                block_id=block_id,
                floor_id=floor_id,
                flat_id=flat_id,
                id_card_prefix=str(parsed_data['id_card_prefix']),
                main_category=main_category_id,
                sub_category=sub_category_str
            )
            
            # Log completion status
            apartment_fields_present = sum([1 for field in [block_id, floor_id, flat_id] if field is not None])
            if apartment_fields_present == 3:
                logger.info(f"Successfully extracted COMPLETE visitor info with confidence: {confidence} using n8n webhook")
            elif apartment_fields_present > 0:
                logger.info(f"Successfully extracted PARTIAL visitor info ({apartment_fields_present}/3 apartment fields) with confidence: {confidence} using n8n webhook")
            else:
                logger.info(f"Successfully extracted visitor info (NO apartment data) with confidence: {confidence} using n8n webhook")
            
            return raw_extracted, confidence
            
        except Exception as e:
            logger.error(f"Error extracting visitor info: {str(e)}")
            raise GeminiServiceError(f"Extraction failed: {str(e)}")


# Global service instance - created when first imported
def get_gemini_service():
    """Get a fresh GeminiService instance."""
    return GeminiService()

gemini_service = get_gemini_service() 