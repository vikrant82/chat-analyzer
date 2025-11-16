# Chat Analyzer Project Overview

## Purpose
A web application for AI-powered analysis of chat histories from multiple platforms (Telegram, Webex, and Reddit). Users can log in, select chats/posts within a date range, and receive AI-powered summaries or ask specific questions. The application also supports bot integrations for invoking analysis directly from chat clients.

## Key Features
- **Multi-Platform Support**: Telegram, Webex, and Reddit integration
- **Multi-Session Management**: Stay logged into all services simultaneously
- **Unified Chat Experience**: Continuous AI conversations with context preservation
- **Threaded Conversations**: Preserves native threading for all platforms
- **Configurable Image Analysis**: Global enable/disable with file size controls
- **Bot Integration**: Webex and Telegram bots for in-chat analysis
- **Real-time Streaming**: Word-by-word AI responses
- **Intelligent Caching**: Dramatically speeds up historical data analysis
- **Performance Optimizations**: Parallel image downloads and date range fetching
- **Flexible Exports**: Text, PDF, HTML, and ZIP formats with images
- **Bot Management UI**: Register, view, and delete bots

## Tech Stack
- **Language**: Python 3.9+
- **Framework**: FastAPI + Uvicorn
- **Key Libraries**:
  - `telethon` - Telegram client
  - `asyncpraw` - Reddit client  
  - `httpx` - Webex/HTTP client
  - `google-generativeai` - Google AI LLM
  - `fpdf2` - PDF generation
  - `Pillow` - Image processing
  - `pydantic` - Data validation

## Current Status
- **Test Coverage**: ~5-10% (minimal - only auth_service and partial chat_service)
- **Production Ready**: Yes, deployed via Docker
- **Active Features**: Multi-platform chat analysis, bot integrations, parallel downloads, intelligent caching
- **Version Management**: Automated GitHub releases integrated with Docker builds (see `release_process` memory)
- **Current Version**: 1.1 (displayed in UI footer with clickable GitHub link)
- **Known Issues**: Minimal test coverage, needs comprehensive testing for critical paths

## Project Type
Web application with REST API backend and JavaScript frontend, deployed via Docker or direct Python execution.