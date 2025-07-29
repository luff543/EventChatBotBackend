# Event Chatbot Backend

This is a FastAPI-based backend service for an event chatbot that helps users search and analyze events.

## Features

- Event search with various filters (location, category, date range, etc.)
- Monthly event analysis for the past 6 months
- Event distribution visualization
- Natural language processing for event recommendations
- OpenAI GPT-4 integration for intelligent responses

## System Requirements

- Python 3.10 or higher
- Anaconda or Miniconda
- OpenAI API key

## Setup

### Using Anaconda (Recommended)

1. Install Anaconda from [Anaconda's official website](https://www.anaconda.com/products/distribution)

2. Create and activate the environment:
```bash
# Clone the repository (if applicable)
git clone <repository-url>
cd event-chatbot

# Create environment from environment.yml
conda env create -f environment.yml

# Activate the environment
conda activate event-chatbot
```

3. Install required packages:
```bash
# Install FastAPI and Uvicorn
pip install fastapi uvicorn

# Install OpenAI
pip install openai

# Install other dependencies
pip install python-dotenv httpx sqlalchemy aiosqlite pandas matplotlib seaborn
pip install langchain
pip install langchain-community
```

4. Verify the installation:
```bash
# Check Python version
python --version  # Should show Python 3.10.x

# Check installed packages
pip list
```

### Using pip (Alternative)

1. Create a virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Unix or MacOS:
source venv/bin/activate
```

2. Install dependencies:
```bash
# Install all required packages
pip install fastapi uvicorn openai python-dotenv httpx sqlalchemy aiosqlite pandas matplotlib seaborn
```

### Configuration

1. Create a `.env` file in the root directory:
```bash
# Windows
echo OPENAI_API_KEY=your_openai_api_key_here > .env
echo EVENTGO_API_BASE=https://localhost:3006 >> .env

# Unix or MacOS
cat << EOF > .env
OPENAI_API_KEY=your_openai_api_key_here
EVENTGO_API_BASE=https://eventgo.widm.csie.ncu.edu.tw:3006
EOF
```

2. Run the server:
```bash
# Development mode with auto-reload
uvicorn main:app --reload

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Chat Endpoints

#### POST /chat
Process chat messages and handle event search requests.

**Request Body:**
```json
{
    "message": "string",
    "session_id": "string (optional)",
    "chat_history": [
        {
            "role": "string",
            "content": "string"
        }
    ],
    "page": "number (optional, default: 1)"
}
```

**Response:**
```json
{
    "message": "string",
    "events": {
        "count": "number",
        "queryTime": "number",
        "events": [
            {
                "id": "string",
                "name": "string",
                "description": "string",
                "location": "string",
                "start_time": "number",
                "end_time": "number",
                "category": "string",
                "venue": {
                    "name": "string",
                    "address": "string",
                    "latitude": "number",
                    "longitude": "number"
                }
            }
        ]
    },
    "search_params": {
        "query": "string",
        "city": "string",
        "category": "string",
        "from": "number",
        "to": "number"
    },
    "pagination": {
        "current_page": "number",
        "events_per_page": "number",
        "total_events": "number",
        "total_pages": "number",
        "current_page_count": "number"
    }
}
```

### Analysis Endpoints

#### GET /analysis/monthly
Get monthly analysis of events for the past 6 months.

**Response:**
```json
{
    "message": "string",
    "data": "array",
    "visualization": "string (base64 encoded image)",
    "trend_analysis": {
        "total_events": "number",
        "average_events": "number",
        "max_month": "object",
        "min_month": "object",
        "monthly_data": "array",
        "time_period": {
            "start": "string",
            "end": "string"
        }
    }
}
```

#### GET /analysis/geographic
Get geographic distribution analysis of events.

**Response:**
```json
{
    "data": "array",
    "visualization": "string (base64 encoded image)"
}
```

#### GET /analysis/report
Generate a comprehensive analysis report.

**Response:**
```json
{
    "report": "string",
    "visualizations": {
        "monthly": "string (base64 encoded image)",
        "geographic": "string (base64 encoded image)"
    }
}
```

### Event Search Endpoints

#### POST /recommend
Get event recommendations based on preferences.

**Request Body:**
```json
{
    "query": "string (optional)",
    "type": "string (optional)",
    "from": "number (optional)",
    "to": "number (optional)",
    "city": "string (optional)",
    "category": "string (optional)",
    "gps": "string (optional)",
    "radius": "number (optional)",
    "num": "number (optional, default: 200)",
    "page": "number (optional, default: 1)",
    "sort": "string (optional, default: start_time)",
    "asc": "boolean (optional, default: true)"
}
```

**Response:**
```json
{
    "count": "number",
    "queryTime": "number",
    "events": "array",
    "pagination": {
        "current_page": "number",
        "events_per_page": "number",
        "total_events": "number",
        "total_pages": "number",
        "current_page_count": "number"
    }
}
```

### Activity Statistics Endpoints

#### GET /activity/histogram
Get activity histogram statistics.

**Query Parameters:**
- `group` (required): Specified group field. Available values: "category", "city"
- `type` (optional): Event types in comma-separated format (e.g., "Web Post,FB Post")
- `query` (optional): Search keyword
- `from` (optional): Start time in milliseconds
- `to` (optional): End time in milliseconds
- `id` (optional): Specific event ID
- `city` (optional): Cities in comma-separated format (e.g., "臺北,宜蘭")
- `category` (optional): Categories in comma-separated format (e.g., "音樂,運動")
- `sort` (optional): Sort key ("value" or "key", default: "value")
- `asc` (optional): Sort ascending (default: false)
- `num` (optional): Maximum number of aggregations (default: 20)

**Response:**
```json
[
    {
        "key": "string",
        "value": "number"
    }
]
```

#### GET /activity/date-histogram
Get activity data aggregated by time intervals.

**Query Parameters:**
- `interval` (required): Time interval for aggregation. Must be one of: "1m", "5m", "15m", "30m", "1h", "2h", "4h", "12h", "1d", "1w", "1M"
- `timezone` (optional): Timezone for aggregation (default: "Asia/Taipei")
- `query` (optional): Search keyword
- `from` (optional): Start time in milliseconds
- `to` (optional): End time in milliseconds
- `id` (optional): Specific event ID
- `city` (optional): Cities in comma-separated format
- `category` (optional): Categories in comma-separated format
- `type` (optional): Event types in comma-separated format
- `num` (optional): Maximum number of buckets (default: 100)

**Response:**
```json
[
    {
        "key": "string (ISO 8601 timestamp)",
        "value": "number"
    }
]
```

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Frontend Integration

The API supports CORS and can be easily integrated with any frontend application. Example frontend integration:

```javascript
// Example chat request
const chat = async (message, sessionId = null) => {
    const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message,
            session_id: sessionId
        })
    });
    return await response.json();
};

// Example usage
const response = await chat("我想找台北的運動活動");
console.log(response);
```

## Development

### Environment Management

1. Update Anaconda environment:
```bash
# Update all packages
conda update --all

# Update specific package
conda update package_name

# Add new package
conda install package_name
```

2. Update pip packages:
```bash
# Update all packages
pip install --upgrade -r requirements.txt

# Update specific package
pip install --upgrade package_name
```

### Adding New Dependencies

1. For Anaconda:
```bash
# Add conda packages
conda install package_name

# Add pip packages
pip install package_name

# Update environment.yml
conda env export > environment.yml
```

2. For pip:
```bash
pip install package_name
pip freeze > requirements.txt
```

### Troubleshooting

1. Environment issues:
```bash
# Remove and recreate environment
conda deactivate
conda env remove -n event-chatbot
conda env create -f environment.yml
```

2. Package conflicts:
```bash
# Check package conflicts
conda list --show-channel-urls

# Resolve conflicts
conda install package_name --force-reinstall
```

3. Database issues:
```bash
# Remove and recreate database
rm event_chatbot.db
# Restart the server to recreate the database
```
