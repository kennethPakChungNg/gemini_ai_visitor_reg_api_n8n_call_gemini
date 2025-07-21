#!/usr/bin/env python3
"""
Test script for OpenRouter integration with AI Visitor Registration API
"""
import asyncio
import json
import logging
import sys
import os
from datetime import datetime

# Add parent directory to path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.gemini_service import GeminiService
from app.services.whizprop_client import WhizPropClient
from app.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_openrouter_connection():
    """Test basic OpenRouter API connection."""
    
    print("🔗 Testing OpenRouter Connection")
    print("-" * 50)
    
    try:
        gemini_service = GeminiService()
        
        print(f"📋 Configuration:")
        print(f"   Provider: {gemini_service.provider}")
        print(f"   Model: {gemini_service.model}")
        print(f"   Base URL: {gemini_service.base_url}")
        print(f"   API Key: {gemini_service.api_key[:20]}..." if gemini_service.api_key else "❌ No API Key")
        
        if not gemini_service.api_key:
            print("❌ OpenRouter API key not configured!")
            print("💡 Set OPENROUTER_API_KEY in your .env file")
            return False
        
        # Test simple prompt
        test_prompt = "What is 2+2? Respond with just the number."
        print(f"\n🧪 Testing simple prompt: '{test_prompt}'")
        
        response = await gemini_service._make_request(test_prompt)
        print(f"✅ Response: {response[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenRouter connection failed: {str(e)}")
        return False

async def test_visitor_parsing():
    """Test visitor information parsing with OpenRouter."""
    
    print("\n🧠 Testing Visitor Parsing with OpenRouter")
    print("-" * 50)
    
    try:
        # Initialize services
        gemini_service = GeminiService()
        whizprop_client = WhizPropClient()
        
        # Get building data
        print("📊 Getting building data...")
        building_data = await whizprop_client.get_building_settings(2)  # Test with building 2
        
        print(f"   Building 2: {len(building_data.BlockList)} blocks, {len(building_data.FloorList)} floors, {len(building_data.UnitList)} units")
        
        # Test cases
        test_cases = [
            "我叫李先生，送外賣到2座15樓A室，身份證A123，是熊猫外賣",
            "John Smith visiting Block 1, 10th floor, Flat B, ID card B789",
            "陳小姐，美團外賣，3座12樓C室，ID card H456"
        ]
        
        for i, test_text in enumerate(test_cases, 1):
            print(f"\n   Test Case {i}: {test_text}")
            
            try:
                raw_extracted, confidence = await gemini_service.extract_visitor_info(test_text, building_data)
                
                print(f"   ✅ Success (Confidence: {confidence:.2f})")
                print(f"   👤 Visitor: {raw_extracted.visitor_name}")
                print(f"   🏢 Location: Block {raw_extracted.block_id}, Floor {raw_extracted.floor_id}, Flat {raw_extracted.flat_id}")
                print(f"   🎯 Category: {raw_extracted.main_category}")
                print(f"   📱 Sub-category: {raw_extracted.sub_category}")
                print(f"   🆔 ID: {raw_extracted.id_card_prefix}")
                
            except Exception as e:
                print(f"   ❌ Parsing failed: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Visitor parsing test failed: {str(e)}")
        return False

async def test_model_comparison():
    """Test different OpenRouter models to compare performance."""
    
    print("\n⚖️ Testing Different OpenRouter Models")
    print("-" * 50)
    
    # Models to test
    models_to_test = [
        "qwen/qwen3-14b:free",          # Recommended - Best balance of speed/accuracy
        "qwen/qwen3-30b-a3b:free",      # Most accurate but slower  
        "qwen/qwen3-4b:free",           # Fastest but less accurate
        "openrouter/optimus-alpha"      # Stealth model - good for coding tasks
    ]
    
    test_prompt = """Parse this visitor text and extract information in JSON format:
"李先生送外賣到2座15樓A室，身份證A123"

Return JSON with: visitor_name, location, id_card_prefix, purpose"""
    
    for model in models_to_test:
        print(f"\n🤖 Testing model: {model}")
        
        try:
            # Temporarily create service with specific model
            original_model = settings.ai_model
            settings.ai_model = model
            
            gemini_service = GeminiService()
            response = await gemini_service._make_request(test_prompt)
            
            print(f"   ✅ Response: {response[:150]}...")
            
            # Restore original model
            settings.ai_model = original_model
            
        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")
            settings.ai_model = original_model

async def main():
    """Main test function."""
    
    print("🚀 OpenRouter Integration Test Suite")
    print("=" * 60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check configuration
    print(f"\n📋 Current Configuration:")
    print(f"   AI Provider: {settings.ai_provider}")
    print(f"   AI Model: {settings.ai_model}")
    print(f"   OpenRouter API Key: {'✅ Configured' if settings.openrouter_api_key else '❌ Missing'}")
    print(f"   WhizProp API Key: {'✅ Configured' if settings.whizprop_api_key else '❌ Missing'}")
    
    if settings.ai_provider != "openrouter":
        print("\n⚠️  AI_PROVIDER is not set to 'openrouter'")
        print("💡 Set AI_PROVIDER=openrouter in your .env file")
        return
    
    # Run tests
    tests = [
        ("OpenRouter Connection", test_openrouter_connection),
        ("Visitor Parsing", test_visitor_parsing),
        ("Model Comparison", test_model_comparison)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name.upper()} {'='*20}")
        try:
            result = await test_func()
            results[test_name] = "PASSED" if result else "FAILED"
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
            results[test_name] = "ERROR"
    
    # Summary
    print(f"\n{'='*20} TEST SUMMARY {'='*20}")
    print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    for test_name, result in results.items():
        status_icon = "✅" if result == "PASSED" else "❌"
        print(f"{status_icon} {test_name}: {result}")
    
    # Overall result
    passed_count = sum(1 for r in results.values() if r == "PASSED")
    total_count = len(results)
    
    if passed_count == total_count:
        print(f"\n🎉 ALL TESTS PASSED! ({passed_count}/{total_count})")
        print("OpenRouter integration is working correctly!")
    else:
        print(f"\n⚠️ SOME TESTS FAILED ({passed_count}/{total_count} passed)")
        print("Check the error messages above for troubleshooting.")
    
    print(f"\n💡 **Setup Instructions:**")
    print(f"1. Get OpenRouter API key: https://openrouter.ai/")
    print(f"2. Add to .env: OPENROUTER_API_KEY=your_key_here")
    print(f"3. Set AI_PROVIDER=openrouter")
    print(f"4. Choose model: AI_MODEL=qwen/qwen3-14b:free (recommended)")
    print(f"   Alternatives: qwen/qwen3-30b-a3b:free (more accurate, slower)")
    print(f"                qwen/qwen3-4b:free (faster, less accurate)")

if __name__ == "__main__":
    print("🔧 OpenRouter Integration Test Suite")
    print("This will test the OpenRouter API integration")
    print("\nPress Enter to start testing or Ctrl+C to cancel...")
    
    try:
        input()
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Testing cancelled by user")
    except Exception as e:
        print(f"\n💥 Testing failed: {str(e)}") 