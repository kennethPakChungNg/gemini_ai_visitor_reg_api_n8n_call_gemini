from fastapi import APIRouter, HTTPException, status
from app.models.requests import VisitorParseRequest
from app.models.responses import VisitorParseResponse, VisitorParseSuccessResponse, VisitorParseErrorResponse, ErrorResponse
from app.services.parser_service import visitor_parser
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/parse-visitor",
    response_model=VisitorParseResponse,
    status_code=status.HTTP_200_OK,
    summary="Parse visitor information from text",
    description="""
    Parse visitor registration information from voice-to-text input using AI.
    
    This endpoint:
    1. Retrieves building structure data from WhizProp API
    2. Uses Gemini AI to extract visitor information from text
    3. Validates and maps extracted data to building structure IDs
    4. Returns structured visitor data with confidence score
    
    Categories:
    - 探訪 (Visit): General visits with no subcategories
    - 外賣 (Delivery): Food delivery with subcategories (FoodPanda, Keeta)
    """,
    responses={
        200: {"description": "Successfully parsed visitor information"},
        400: {"description": "Invalid request data"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)
async def parse_visitor(request: VisitorParseRequest):
    """Parse visitor information from text input."""
    try:
        logger.info(f"Received parse request for building {request.building_id}")
        
        # Validate input
        if not request.text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text input cannot be empty"
            )
        
        if request.building_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Building ID must be positive"
            )
        
        # Parse visitor information
        result = await visitor_parser.parse_visitor_info(request.building_id, request.text)
        
        # Handle error responses
        if isinstance(result, VisitorParseErrorResponse):
            logger.error(f"Parsing failed: {result.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message
            )
        
        logger.info(f"Successfully parsed visitor info with confidence: {result.confidence}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in parse_visitor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health check",
    description="Check if the API is running properly",
    responses={
        200: {"description": "Service is healthy"}
    }
)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "AI Visitor Registration API",
        "version": "1.0.0"
    }


@router.get(
    "/categories",
    summary="Get visit categories",
    description="Retrieve available main and sub categories for visitor purposes",
    responses={
        200: {"description": "Successfully retrieved categories"}
    }
)
async def get_categories():
    """Get available visit categories."""
    return {
        "main_categories": [
            {
                "name_chi": "探訪",
                "name_eng": "Visit",
                "has_subcategories": False,
                "subcategories": []
            },
            {
                "name_chi": "外賣", 
                "name_eng": "Delivery",
                "has_subcategories": True,
                "subcategories": [
                    {"name_chi": "熊猫", "name_eng": "FoodPanda"},
                    {"name_chi": "美團", "name_eng": "Keeta"}
                ]
            }
        ]
    } 