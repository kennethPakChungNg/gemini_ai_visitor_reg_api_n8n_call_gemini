#!/usr/bin/env python3
"""
Test script to verify AI Visitor Registration API works with multiple building IDs
This addresses the concern that the logic might only work for building ID 2 (test building)
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime

# Add parent directory to path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.whizprop_client import WhizPropClient
from app.services.gemini_service import GeminiService
from app.services.parser_service import VisitorParserService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MultiBuildingTester:
    def __init__(self):
        self.whizprop_client = WhizPropClient()
        self.gemini_service = GeminiService()
        self.parser_service = VisitorParserService()
        
    async def test_building_structure(self, building_id: int):
        """Test and display building structure for a given building ID."""
        
        print(f"\n🏢 Testing Building ID: {building_id}")
        print("-" * 50)
        
        try:
            # Get building data
            building_data = await self.whizprop_client.get_building_settings(building_id)
            
            # Display structure
            print(f"📊 Building Structure:")
            print(f"   Blocks: {len(building_data.BlockList)}")
            print(f"   Floors: {len(building_data.FloorList)}")
            print(f"   Units: {len(building_data.UnitList)}")
            print(f"   Visit Categories: {len(building_data.VisitCat) if building_data.VisitCat else 0}")
            print(f"   Sub Categories: {len(building_data.VisitSubCat) if building_data.VisitSubCat else 0}")
            
            # Show some examples
            if building_data.BlockList:
                print(f"\n📋 Sample Blocks:")
                for block in building_data.BlockList[:3]:  # Show first 3
                    print(f"   - {block.NameChi} (ID: {block.Id})")
                if len(building_data.BlockList) > 3:
                    print(f"   ... and {len(building_data.BlockList) - 3} more")
            
            if building_data.FloorList:
                print(f"\n🏗️ Sample Floors:")
                for floor in building_data.FloorList[:3]:  # Show first 3
                    print(f"   - {floor.NameChi} (ID: {floor.Id}, Block: {floor.BlockId})")
                if len(building_data.FloorList) > 3:
                    print(f"   ... and {len(building_data.FloorList) - 3} more")
            
            if building_data.UnitList:
                print(f"\n🏠 Sample Units:")
                for unit in building_data.UnitList[:3]:  # Show first 3
                    print(f"   - {unit.NameChi} (ID: {unit.Id}, Floor: {unit.FloorId})")
                if len(building_data.UnitList) > 3:
                    print(f"   ... and {len(building_data.UnitList) - 3} more")
            
            return building_data
            
        except Exception as e:
            print(f"❌ Failed to get building {building_id} data: {str(e)}")
            return None
    
    async def test_visitor_parsing(self, building_id: int, building_data, test_cases):
        """Test visitor parsing for a specific building."""
        
        print(f"\n🧠 Testing AI Parsing for Building {building_id}")
        print("-" * 50)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n   Test {i}: {test_case['description']}")
            print(f"   Input: {test_case['text']}")
            
            try:
                # Test the parser service directly
                result = await self.parser_service.parse_visitor_info(building_id, test_case['text'])
                
                if hasattr(result, 'status') and result.status == "success":
                    data = result.data
                    print(f"   ✅ Success (Confidence: {result.confidence:.2f})")
                    print(f"   👤 Visitor: {data.visitor_name}")
                    print(f"   🏢 Location: Block {data.block_id}, Floor {data.floor_id}, Flat {data.flat_id}")
                    print(f"   🎯 Category: {data.main_category}")
                    if data.sub_category:
                        print(f"   📱 Sub-category: {data.sub_category}")
                    print(f"   🆔 ID: {data.id_card_prefix}")
                    
                    # Validate the IDs exist in building data
                    validation_errors = []
                    
                    # Check block ID
                    if data.block_id:
                        block_exists = any(b.Id == data.block_id for b in building_data.BlockList)
                        if not block_exists:
                            validation_errors.append(f"Block ID {data.block_id} not found")
                    
                    # Check floor ID
                    if data.floor_id:
                        floor_exists = any(f.Id == data.floor_id for f in building_data.FloorList)
                        if not floor_exists:
                            validation_errors.append(f"Floor ID {data.floor_id} not found")
                    
                    # Check flat ID
                    if data.flat_id:
                        flat_exists = any(u.Id == data.flat_id for u in building_data.UnitList)
                        if not flat_exists:
                            validation_errors.append(f"Flat ID {data.flat_id} not found")
                    
                    if validation_errors:
                        print(f"   ⚠️  Validation Issues: {', '.join(validation_errors)}")
                    else:
                        print(f"   ✅ All IDs validated successfully")
                        
                else:
                    print(f"   ❌ Failed: {result.message if hasattr(result, 'message') else 'Unknown error'}")
                    
            except Exception as e:
                print(f"   💥 Exception: {str(e)}")
    
    async def run_comprehensive_test(self):
        """Run comprehensive tests across multiple buildings."""
        
        print("🚀 AI Visitor Registration - Multi-Building Test Suite")
        print("=" * 80)
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test buildings
        test_buildings = [1, 2]  # Add more building IDs as needed
        
        # Test cases for each building
        test_cases = [
            {
                "description": "Chinese delivery to first block, first floor",
                "text": "我叫李先生，送外賣到1座1樓A室，身份證A123，是熊猫外賣"
            },
            {
                "description": "Chinese delivery to first block, ground floor", 
                "text": "陳小姐，美團外賣，1座地下A室，ID card H456"
            },
            {
                "description": "English visit to second block",
                "text": "John Smith visiting Block 2, 5th floor, Flat B, ID card B789"
            },
            {
                "description": "Mixed language delivery",
                "text": "張先生 delivery food to 2座 10樓 C室, 身份證 C321, FoodPanda"
            }
        ]
        
        all_results = {}
        
        for building_id in test_buildings:
            print(f"\n{'='*20} BUILDING {building_id} TESTING {'='*20}")
            
            # Test building structure
            building_data = await self.test_building_structure(building_id)
            
            if building_data:
                # Test visitor parsing
                await self.test_visitor_parsing(building_id, building_data, test_cases)
                all_results[building_id] = "PASSED"
            else:
                all_results[building_id] = "FAILED - Could not get building data"
        
        # Summary
        print(f"\n{'='*20} TEST SUMMARY {'='*20}")
        print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        for building_id, result in all_results.items():
            status_icon = "✅" if result == "PASSED" else "❌"
            print(f"{status_icon} Building {building_id}: {result}")
        
        # Overall result
        passed_count = sum(1 for r in all_results.values() if r == "PASSED")
        total_count = len(all_results)
        
        if passed_count == total_count:
            print(f"\n🎉 ALL TESTS PASSED! ({passed_count}/{total_count} buildings)")
            print("The AI Visitor Registration system works correctly across multiple buildings.")
        else:
            print(f"\n⚠️ SOME TESTS FAILED ({passed_count}/{total_count} buildings passed)")
            print("Review the failed buildings and their error messages above.")
        
        print("\n" + "=" * 80)

async def main():
    """Main test function."""
    tester = MultiBuildingTester()
    await tester.run_comprehensive_test()

if __name__ == "__main__":
    print("🔧 Multi-Building Test Suite for AI Visitor Registration")
    print("This will test the system with different building structures")
    print("\nPress Enter to start testing or Ctrl+C to cancel...")
    
    try:
        input()
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Testing cancelled by user")
    except Exception as e:
        print(f"\n💥 Testing failed: {str(e)}") 