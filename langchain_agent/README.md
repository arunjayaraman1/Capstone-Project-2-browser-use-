# Amazon Cart Automation - FastAPI + Streamlit

This project provides a web interface for automating Amazon.in cart operations using Browser-Use.

## Setup

### 1. Install Dependencies

FastAPI and Uvicorn are already included in the project dependencies. You only need to install Streamlit:

```bash
# Install Streamlit
uv pip install streamlit
```

Note: `requests` is already included in the project dependencies.

### 2. Set Environment Variables

Make sure you have your OpenAI API key set:

```bash
export OPENAI_API_KEY=your_key_here
```

Or create a `.env` file:
```
OPENAI_API_KEY=your_key_here
```

## Running the Application

### Option 1: Run Backend and Frontend Separately

**Terminal 1 - Start FastAPI Backend:**
```bash
cd langchain_agent
python api.py
```

The API will be available at `http://localhost:8000`

**Terminal 2 - Start Streamlit UI:**
```bash
cd langchain_agent
streamlit run ui.py
```

The UI will be available at `http://localhost:8501`

### Option 2: Use the Startup Script

```bash
cd langchain_agent
chmod +x start.sh
./start.sh
```

## API Endpoints

### Health Check
```
GET /health
```

### Add to Cart
```
POST /add-to-cart
Body: {
  "items": ["laptop", "mouse", "keyboard"]
}
```

## Usage

1. Start the FastAPI backend (`python api.py`)
2. Start the Streamlit UI (`streamlit run ui.py`)
3. Open your browser to `http://localhost:8501`
4. Enter product names (comma-separated)
5. Click "Add to Cart"
6. Wait for the automation to complete
7. View the results

## Notes

- The browser will open in non-headless mode so you can see what's happening
- Make sure you have a stable internet connection
- The process may take a few minutes depending on the number of items
