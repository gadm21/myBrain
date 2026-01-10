# Thoth: An AI-Agent Backend API

This is the Backend for the chatbot (named Thoth) on my personal website: https://www.gadgad.me/. It is currently running on the Railway.  
The core of this AI-Agent is an OpenAI LLM accessed through API. 
Thoth features cross-query long-term memory and function calling (for sending SMS messages). 

## API Documentation

Once the server is running, you can access:

- **Interactive API Docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative API Docs (ReDoc)**: http://localhost:8000/redoc

## Environment Variables

See [.env.example](.env.example) for all available configuration options.

## Project Structure

```
backend/
├── server/               # Main application package
│   ├── __init__.py
│   ├── main.py           # FastAPI app initialization
│   ├── routes.py         # API endpoints
│   ├── auth.py           # Authentication utilities
│   ├── db.py             # Database models and session
│   ├── schemas.py        # Pydantic models
│   └── utils.py          # Helper functions
├── aiagent/             # AI-related functionality
│   ├── handler/         # Request handlers
│   ├── memory/          # Memory management
│   └── tools/           # AI tools and utilities
├── tests/               # Test files
├── .env.example         # Example environment variables
├── requirements.txt     # Python dependencies
└── README.md           # This file
```


