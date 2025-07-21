from pydantic import BaseModel, Field
from typing import Optional


class VisitorParseRequest(BaseModel):
    """Request model for visitor information parsing."""
    
    building_id: int = Field(..., description="WhizProp building ID", example=2)
    text: str = Field(..., min_length=1, max_length=1000, description="Voice-to-text input containing visitor information", example="我叫李先生，送外賣到2座15樓A室，身份證A123")
    
    class Config:
        json_schema_extra = {
            "example": {
                "building_id": 2,
                "text": "我叫李先生，送外賣到2座15樓A室，身份證A123"
            }
        } 