"""
Demo script to test the AI Visitor Registration API
"""
import asyncio
import httpx
import json
import sys
import os
from typing import Dict, Any

# Add parent directory to path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Demo configuration
BASE_URL = "http://localhost:8000"
TEST_CASES = [
    {
        "name": "Chinese Delivery (FoodPanda)",
        "building_id": 2,
        "text": "我叫李先生，送外賣到2座15樓A室，身份證A123，是熊猫外賣"
    },
    {
        "name": "Chinese Delivery (Keeta)", 
        "building_id": 2,
        "text": "陳小姐，美團外賣，3座12樓B室，ID card H456"
    },
    {
        "name": "English Visit",
        "building_id": 2,
        "text": "John Smith visiting Block 1, 10th floor, Flat C, ID card B789"
    },
    {
        "name": "Mixed Language Delivery",
        "building_id": 2,
        "text": "張先生 delivery food to Block 5, 20樓 Flat D, 身份證 C321, FoodPanda"
    },
    {
        "name": "Building ID 1 Test",
        "building_id": 1,
        "text": "我叫李先生，送外賣到1座1樓B室，身份證A123，是熊猫外賣"
    }
]

async def test_api_endpoint(endpoint: str, method: str = "GET", data: Dict[Any, Any] = None) -> Dict[str, Any]:
    """Test an API endpoint and return the result."""
    
    url = f"{BASE_URL}/api/v1{endpoint}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if method.upper() == "POST":
                response = await client.post(url, json=data)
            else:
                response = await client.get(url)
            
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
            }
            
        except httpx.ConnectError:
            return {
                "success": False,
                "error": "connection_failed",
                "data": f"Could not connect to {BASE_URL}. Make sure the API server is running."
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "timeout",
                "data": "Request timed out after 30 seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "error": "unknown",
                "data": f"Unexpected error: {str(e)}"
            }

async def run_demo():
    """Run the demo with all test cases."""
    
    print("🤖 AI Visitor Registration API Demo")
    print("=" * 50)
    
    # Test 1: Health Check
    print("\n1. 🏥 Health Check")
    health_result = await test_api_endpoint("/health")
    
    if health_result["success"]:
        print(f"   ✅ API is healthy (Status: {health_result['status_code']})")
        print(f"   📋 Response: {health_result['data']}")
    else:
        print(f"   ❌ Health check failed: {health_result['data']}")
        return
    
    # Test 2: Categories
    print("\n2. 📂 Get Categories")
    categories_result = await test_api_endpoint("/categories")
    
    if categories_result["success"]:
        if categories_result["status_code"] == 200:
            print(f"   ✅ Categories retrieved successfully")
            categories_data = categories_result["data"]
            print(f"   📊 Categories: {json.dumps(categories_data, ensure_ascii=False, indent=6)}")
        else:
            print(f"   ⚠️  Categories endpoint returned status {categories_result['status_code']}")
    else:
        print(f"   ❌ Categories failed: {categories_result['data']}")
    
    # Test 3: Visitor Parsing
    print("\n3. 🧠 AI Visitor Information Parsing")
    print("   Testing multiple scenarios...")
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n   Test Case {i}: {test_case['name']}")
        print(f"   Input: {test_case['text']}")
        print("   🤖 Processing with AI... (this may take 5-10 seconds)")
        
        parse_result = await test_api_endpoint(
            "/parse-visitor",
            method="POST",
            data={
                "building_id": test_case["building_id"],
                "text": test_case["text"]
            }
        )
        
        if parse_result["success"]:
            result_data = parse_result["data"]
            print(f"   ✅ Status: {result_data['status']}")
            
            if result_data["status"] == "success":
                data = result_data.get("data", {})
                print(f"   📊 Confidence: {result_data.get('confidence', 0):.2f}")
                print(f"   👤 Visitor: {data.get('visitor_name', 'N/A')}")
                print(f"   🏢 Location: Block {data.get('block_id', 'N/A')}, Floor {data.get('floor_id', 'N/A')}, Flat {data.get('flat_id', 'N/A')}")
                print(f"   🎯 Category: {data.get('main_category', 'N/A')}")
                if data.get("sub_category"):
                    print(f"   📱 Sub-category: {data.get('sub_category')}")
                print(f"   🆔 ID: {data.get('id_card_prefix', 'N/A')}")
                
                # Show the actual JSON response that gets returned to the API caller
                print(f"\n   📋 **JSON Response to API Caller:**")
                print(f"   ```json")
                print(f"   {json.dumps(result_data, indent=4, ensure_ascii=False)}")
                print(f"   ```")
            else:
                print(f"   ❌ Error: {result_data.get('message', 'Unknown error')}")
        else:
            print(f"   ❌ Request failed: {parse_result['data']}")
    
    print("\n" + "=" * 50)
    print("🎉 Demo completed!")
    
    print("\n📖 API Documentation:")
    print(f"   Interactive docs: {BASE_URL}/docs")
    print(f"   OpenAPI schema: {BASE_URL}/openapi.json")

if __name__ == "__main__":
    print("🚀 Starting AI Visitor Registration API Demo...")
    print("Make sure the API server is running on http://localhost:8000")
    print("Run: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    
    try:
        input()
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n👋 Demo cancelled by user")
    except Exception as e:
        print(f"\n💥 Demo failed: {str(e)}") 