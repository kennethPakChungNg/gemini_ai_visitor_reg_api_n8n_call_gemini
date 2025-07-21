from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, Union, List


class ExtractedData(BaseModel):
    """Extracted visitor data with IDs."""
    
    block_id: Optional[int] = Field(None, description="WhizProp block ID")
    floor_id: Optional[int] = Field(None, description="WhizProp floor ID") 
    flat_id: Optional[int] = Field(None, description="WhizProp flat ID")
    visitor_name: Optional[str] = Field(None, description="Visitor name")
    id_card_prefix: Optional[str] = Field(None, description="First 4 digits of ID card")
    main_category: Optional[int] = Field(None, description="Main visit category ID (19 for 探訪, 20 for 外賣)")
    sub_category: Optional[str] = Field(None, description="Sub category NameChi (美團/FoodPanda for 外賣)")


class RawExtracted(BaseModel):
    """Raw extracted information from Gemini AI."""
    
    visitor_name: Optional[str] = None
    block_id: Optional[int] = None
    floor_id: Optional[int] = None
    flat_id: Optional[int] = None
    id_card_prefix: Optional[str] = None
    main_category: Optional[int] = None
    sub_category: Optional[str] = None


class VisitorParseSuccessResponse(BaseModel):
    """Success response model for visitor parsing."""
    
    status: str = Field(default="success", description="Response status")
    data: ExtractedData = Field(..., description="Extracted and validated data")
    confidence: float = Field(..., ge=0, le=1, description="AI confidence score")


class VisitorParseErrorResponse(BaseModel):
    """Error response model for visitor parsing."""
    
    status: str = Field(default="error", description="Response status")
    message: str = Field(..., description="Error message")


# Union type for the actual response
VisitorParseResponse = Union[VisitorParseSuccessResponse, VisitorParseErrorResponse]


class ErrorResponse(BaseModel):
    """General error response model."""
    
    status: str = "error"
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details") 


class VisitorRegistrationRequest(BaseModel):
    building_id: int
    text: str

class VisitorRegistrationResponse(BaseModel):
    status: str
    data: Optional[RawExtracted]
    confidence: Optional[float]
    message: Optional[str] = None

class ValidationError(BaseModel):
    field: str  # "block", "floor", "flat"
    extracted_value: str  # What user said
    issue: str  # "not_found", "not_in_block", "not_on_floor"
    suggestions: List[str] = []  # Possible alternatives

class VisitorValidationResponse(BaseModel):
    status: str  # "success", "validation_error", "error" 
    data: Optional[RawExtracted]
    confidence: Optional[float]
    validation_errors: List[ValidationError] = []
    message: Optional[str] = None 