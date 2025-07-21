from typing import Optional
from app.services.whizprop_client import whizprop_client, WhizPropAPIError
from app.services.gemini_service import gemini_service, GeminiServiceError
from app.models.responses import VisitorParseSuccessResponse, VisitorParseErrorResponse, ExtractedData, RawExtracted, ErrorResponse
from app.models.whizprop import BuildingData
import logging

logger = logging.getLogger(__name__)


class VisitorParserService:
    """Main service for parsing visitor information."""
    
    async def parse_visitor_info(self, building_id: int, text: str):
        """Parse visitor information from text input."""
        try:
            # Step 1: Get building data from WhizProp
            logger.info(f"Parsing visitor info for building {building_id}")
            building_data = await whizprop_client.get_building_settings(building_id)
            
            # Step 2: Extract information using Gemini AI
            raw_extracted, confidence = await gemini_service.extract_visitor_info(text, building_data)
            
            # Step 3: Validate and map to IDs
            extracted_data = await self._validate_and_map_data(raw_extracted, building_data, text)
            
            # Step 4: Use categories from Gemini extraction
            extracted_data.main_category = raw_extracted.main_category
            extracted_data.sub_category = raw_extracted.sub_category
            
            # Return success response
            return VisitorParseSuccessResponse(
                data=extracted_data,
                confidence=confidence
            )
            
        except WhizPropAPIError as e:
            logger.error(f"WhizProp API error: {str(e)}")
            return VisitorParseErrorResponse(
                message=f"Building data retrieval failed: {str(e)}"
            )
        except GeminiServiceError as e:
            logger.error(f"Gemini service error: {str(e)}")
            return VisitorParseErrorResponse(
                message=f"Text parsing failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error in visitor parsing: {str(e)}")
            return VisitorParseErrorResponse(
                message=f"Parsing failed: {str(e)}"
            )
    
    async def _validate_and_map_data(self, raw_extracted: RawExtracted, building_data: BuildingData, original_text: str) -> ExtractedData:
        """Create ExtractedData from validated RawExtracted data."""
        
        # Since GeminiService already validates and converts IDs, we can directly map
        extracted_data = ExtractedData(
            visitor_name=raw_extracted.visitor_name,
            block_id=raw_extracted.block_id,
            floor_id=raw_extracted.floor_id,
            flat_id=raw_extracted.flat_id,
            id_card_prefix=raw_extracted.id_card_prefix,
            main_category=raw_extracted.main_category,
            sub_category=raw_extracted.sub_category
        )
        
        logger.info(f"Parsed location '{original_text[:50]}...' -> Block: {extracted_data.block_id}, Floor: {extracted_data.floor_id}, Flat: {extracted_data.flat_id}")
        
        return extracted_data
    

# Global instance
visitor_parser = VisitorParserService() 