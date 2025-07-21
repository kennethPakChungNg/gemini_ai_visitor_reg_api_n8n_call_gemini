from pydantic import BaseModel
from typing import List, Optional


class Block(BaseModel):
    """WhizProp Block model."""
    Id: int
    NameChi: str
    NameEng: str
    Seq: int


class Floor(BaseModel):
    """WhizProp Floor model."""
    Id: int
    BlockId: int
    NameChi: str
    NameEng: str
    Seq: int


class Flat(BaseModel):
    """WhizProp Flat model."""
    Id: int
    FloorId: int
    NameChi: str
    NameEng: str
    Seq: int


class VisitCategory(BaseModel):
    """WhizProp Visit Category model."""
    Id: int
    NameChi: str
    NameEng: str
    Seq: int


class VisitSubCategory(BaseModel):
    """WhizProp Visit Sub Category model."""
    VisitCatId: int
    NameChi: str
    NameEng: str
    Seq: int


class BuildingData(BaseModel):
    """WhizProp Building Setting response model."""
    PrintEntryPass: bool
    BlockList: List[Block]
    FloorList: List[Floor]
    UnitList: List[Flat]  # API returns UnitList, not FlatList
    VisitCat: Optional[List[VisitCategory]] = []
    VisitSubCat: Optional[List[VisitSubCategory]] = []
    AuthorizationTimeList: Optional[List] = []
    PrinterList: Optional[List] = []
    PrintRemarkList: Optional[List] = []


class WhizPropResponse(BaseModel):
    """WhizProp API response wrapper."""
    status: int
    errMsg: str
    data: BuildingData


class VisitCategory(BaseModel):
    """Visit category structure."""
    name_chi: str
    name_eng: str
    has_subcategories: bool = False


class SubCategory(BaseModel):
    """Sub category structure."""
    name_chi: str
    name_eng: str
    parent_category: str


# Predefined categories
MAIN_CATEGORIES = {
    "探訪": VisitCategory(name_chi="探訪", name_eng="Visit", has_subcategories=False),
    "外賣": VisitCategory(name_chi="外賣", name_eng="Delivery", has_subcategories=True)
}

SUB_CATEGORIES = {
    "FoodPanda": SubCategory(name_chi="熊猫", name_eng="FoodPanda", parent_category="外賣"),
    "Keeta": SubCategory(name_chi="美團", name_eng="Keeta", parent_category="外賣")
} 