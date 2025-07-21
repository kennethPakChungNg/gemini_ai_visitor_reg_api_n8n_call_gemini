# Test Suite for AI Visitor Registration API

This folder contains test scripts for the AI Visitor Registration API system.

## Test Files

### 🎯 `run_demo.py`

**Interactive API Demo**

- Comprehensive demonstration of the API functionality
- Tests multiple scenarios with different inputs
- Shows real-time API responses with formatting
- Includes health checks and category testing

**How to run:**

```bash
cd tests
python run_demo.py
```

**Requirements:**

- API server must be running on `http://localhost:8000`
- All environment variables properly configured

---

### 🏢 `test_multiple_buildings.py`

**Multi-Building Regression Test**

- Tests the system across multiple building IDs
- Validates building structure retrieval
- Tests AI parsing with different building configurations
- Includes ID validation against building data
- Comprehensive test reporting

**How to run:**

```bash
cd tests
python test_multiple_buildings.py
```

**What it tests:**

- Building structure validation for multiple buildings
- AI parsing accuracy across different building layouts
- ID mapping validation (blocks, floors, flats)
- Error handling for different building configurations

---

### 🌐 `test_openrouter.py`

**OpenRouter API Integration Test**

- Tests OpenRouter API connection and authentication
- Validates visitor parsing with OpenRouter models
- Compares different free models (Gemini, Qwen)
- Provides setup instructions for OpenRouter

**How to run:**

```bash
cd tests
python test_openrouter.py
```

**What it tests:**

- OpenRouter API connectivity
- Multiple free model performance comparison
- Visitor information extraction accuracy
- Configuration validation

**Models tested:**

- `qwen/qwen3-14b:free` (Recommended - Best balance of speed/accuracy)
- `qwen/qwen3-30b-a3b:free` (Most accurate but slower)
- `qwen/qwen3-4b:free` (Fastest but less accurate)
- `openrouter/optimus-alpha` (Stealth model - good for coding tasks)

---

## Running Tests

### Prerequisites

1. **Start the API server (for API tests):**

   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Ensure environment variables are configured:**

   **For Direct Gemini API:**

   ```bash
   AI_PROVIDER=gemini
   GEMINI_API_KEY=your_gemini_api_key
   ```

   **For OpenRouter (Recommended for deployment):**

   ```bash
   AI_PROVIDER=openrouter
   OPENROUTER_API_KEY=your_openrouter_api_key
   AI_MODEL=google/gemini-2.5-pro-exp-03-25:free
   ```

   **WhizProp Configuration:**

   ```bash
   WHIZPROP_API_KEY=your_api_key
   WHIZPROP_BASE_URL=your_base_url
   ```

### Quick Test Commands

```bash
# Run demo (interactive) - requires API server
python tests/run_demo.py

# Run multi-building tests - requires API server
python tests/test_multiple_buildings.py

# Test OpenRouter integration - direct service test
python tests/test_openrouter.py

# Run from project root
python -m tests.run_demo
python -m tests.test_multiple_buildings
python -m tests.test_openrouter
```

## OpenRouter Setup (Recommended for Deployment)

### Why Use OpenRouter?

- ✅ **No VPN required** for server deployment
- ✅ **Free Gemini models** available (deprecated but working)
- ✅ **Alternative free models** (Qwen series)
- ✅ **Rate limiting** instead of regional blocking
- ✅ **OpenAI-compatible API** for easy integration

### Setup Steps:

1. **Get OpenRouter API key:**

   - Visit https://openrouter.ai/
   - Sign up and get your API key

2. **Configure environment:**

   ```bash
   AI_PROVIDER=openrouter
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   AI_MODEL=google/gemini-2.5-pro-exp-03-25:free
   ```

3. **Test the configuration:**
   ```bash
   python tests/test_openrouter.py
   ```

### Available Free Models:

- **Qwen3 14B (Free)** 🌟 **RECOMMENDED**: `qwen/qwen3-14b:free`

  - Best balance of speed and accuracy for visitor registration
  - Excellent multilingual support (Chinese/English)
  - Good JSON formatting reliability
  - Rate limited: 20 req/min, 50-1000 req/day

- **Qwen3 30B A3B (Free)**: `qwen/qwen3-30b-a3b:free`

  - Highest accuracy with MoE architecture
  - Slower but more capable for complex parsing
  - Rate limited: 20 req/min, 50-1000 req/day

- **Qwen3 4B (Free)**: `qwen/qwen3-4b:free`

  - Fastest response times
  - Good for simple parsing tasks
  - Rate limited: 20 req/min, 50-1000 req/day

- **OpenRouter Stealth Models**:
  - `openrouter/optimus-alpha` - General purpose, coding optimized
  - `openrouter/cypher-alpha` - All-purpose, long context
  - `openrouter/quasar-alpha` - Long-context, coding optimized

## Test Coverage

### Functionality Tested

- ✅ API health checks
- ✅ Building data retrieval
- ✅ AI text parsing (Chinese/English/Mixed)
- ✅ ID validation and mapping
- ✅ Visit category classification
- ✅ Error handling and edge cases
- ✅ Multi-building compatibility
- ✅ OpenRouter integration
- ✅ Multiple AI model support

### Test Scenarios

- Chinese delivery requests (FoodPanda, Keeta)
- English visit requests
- Mixed language inputs
- Different building structures
- Various address formats
- ID card validation
- OpenRouter API connectivity
- Model performance comparison

## Adding New Tests

To add new test cases:

1. **For demo tests:** Edit `TEST_CASES` in `run_demo.py`
2. **For building tests:** Edit `test_cases` in `test_multiple_buildings.py`
3. **For OpenRouter tests:** Edit `test_cases` in `test_openrouter.py`

Example test case:

```python
{
    "name": "Test Description",
    "building_id": 2,
    "text": "李先生送外賣到2座15樓A室，身份證A123"
}
```

## Troubleshooting

### Common Issues

1. **Connection errors:** Check if API server is running (for API tests)
2. **Import errors:** Ensure you're running from correct directory
3. **Authentication errors:** Verify environment variables
4. **Parsing errors:** Check AI provider API key and quota
5. **OpenRouter rate limits:** Switch models or wait for quota reset

### Debug Tips

- Check API logs when tests fail
- Verify building IDs exist in WhizProp system
- Test with simple inputs first
- Check network connectivity for external APIs
- Use `test_openrouter.py` to debug OpenRouter issues
- Try different models if one fails

### OpenRouter Troubleshooting

- **401 Unauthorized:** Check OPENROUTER_API_KEY
- **429 Rate Limited:** Wait or try different model
- **Model not available:** Use alternative free model
- **JSON parsing errors:** Some models may format differently
