# AI Visitor Registration API

An AI-powered API that uses Google Gemini 2.0 Flash to parse voice-to-text input and extract visitor registration information, integrating with WhizProp CS API for validation.

## Features

- **AI-Powered Text Parsing**: Uses Gemini 2.0 Flash for intelligent information extraction
- **Building Structure Validation**: Integrates with WhizProp CS API for real-time validation
- **Bilingual Support**: Handles both Chinese and English inputs
- **Confidence Scoring**: Provides confidence ratings for extracted data
- **RESTful API**: Clean, well-documented REST endpoints
- **Automatic Categorization**: Determines visit purpose (探訪/外賣) with subcategories

## Architecture

```
Voice Input → Mobile App → Your API → Gemini AI → WhizProp Validation → JSON Response
```

## Installation

1. **Clone and navigate to the project**:

   ```bash
   cd gemini_ai_visitor_reg_api
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   Copy `.env.example` to `.env` and update with your credentials:

   ```bash
   cp .env.example .env
   ```

4. **Run the application**:
   ```bash
   python -m app.main
   ```
   Or with uvicorn:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## API Usage

### Main Endpoint

**POST** `/api/v1/parse-visitor`

```json
{
  "building_id": 2,
  "text": "我叫李先生，送外賣到2座15樓A室，身份證A123"
}
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "block_id": 2,
    "floor_id": 18,
    "flat_id": 225,
    "visitor_name": "李先生",
    "id_card_prefix": "A123",
    "main_category": 20,
    "sub_category": "FoodPanda"
  },
  "confidence": 0.92
}
```

### Other Endpoints

- **GET** `/api/v1/health` - Health check
- **GET** `/api/v1/categories` - Get available categories
- **GET** `/docs` - Interactive API documentation

## Categories

### Main Categories

- **探訪 (Visit)**: General visits with no subcategories
- **外賣 (Delivery)**: Food delivery with subcategories

### Sub Categories (外賣 only)

- **FoodPanda (熊猫)**
- **Keeta (美團)**

## Configuration

### Environment Variables

| Variable                | Description           | Required |
| ----------------------- | --------------------- | -------- |
| `GEMINI_API_KEY`        | Google Gemini API key | Yes      |
| `WHIZPROP_API_KEY`      | WhizProp CS API key   | Yes      |
| `WHIZPROP_ACCESS_TOKEN` | WhizProp access token | Yes      |
| `WHIZPROP_BASE_URL`     | WhizProp API base URL | Yes      |
| `DEBUG`                 | Enable debug mode     | No       |

### WhizProp Integration

The API integrates with WhizProp CS API to:

1. Authenticate and get device ID
2. Retrieve building structure (blocks, floors, flats)
3. Validate extracted location data
4. Map location names to internal IDs

## Testing

Run tests with pytest:

```bash
pytest tests/
```

### Test Examples

```python
# Test basic parsing
response = await client.post("/api/v1/parse-visitor", json={
    "building_id": 2,
    "text": "我叫李先生，送外賣到2座15樓A室，身份證A123"
})
assert response.status_code == 200
assert response.json()["status"] == "success"
```

## Error Handling

The API provides detailed error responses:

```json
{
  "status": "error",
  "message": "Building data retrieval failed: Invalid building ID",
  "details": "..."
}
```

Common error scenarios:

- Invalid building ID
- WhizProp API unavailable
- Gemini API errors
- Invalid text input

## Performance

- **Response Time**: < 2 seconds typical
- **Confidence**: 95%+ for well-formatted inputs
- **Supported Languages**: Chinese (Traditional/Simplified), English
- **Concurrent Requests**: Async architecture supports high concurrency

## Development

### Project Structure

```
gemini_ai_visitor_reg_api/
├── app/
│   ├── api/          # API routes
│   ├── config/       # Configuration
│   ├── models/       # Pydantic models
│   ├── services/     # Business logic
│   └── main.py       # FastAPI app
├── tests/            # Test files
├── requirements.txt  # Dependencies
└── README.md
```

### Adding New Features

1. **New Categories**: Update `app/models/whizprop.py`
2. **New Validation**: Extend `app/services/parser_service.py`
3. **New Endpoints**: Add to `app/api/routes.py`

## Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations

- Set `DEBUG=false`
- Configure CORS appropriately
- Use production WSGI server
- Implement rate limiting
- Add authentication if needed
- Monitor API usage and performance

## Support

For issues or questions:

1. Check the API documentation at `/docs`
2. Review logs for error details
3. Verify environment configuration
4. Test with sample data

## License

[Your License Here]
 