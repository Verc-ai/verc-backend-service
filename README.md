# Verc Backend Service

Production-ready Django backend service for Verc, refactored from TypeScript/Express.

## Overview

This is a Django-based backend service that provides:
- REST API endpoints for authentication, sessions, conversations
- Twilio integration for call handling and transcription
- AI services integration (OpenAI, Anthropic, AssemblyAI)
- Google Cloud Tasks for async processing
- Multi-tenant support with organization isolation
- Real-time capabilities via Django Channels

## Tech Stack

- **Framework**: Django 5.0 with Django REST Framework
- **Async Support**: Django Channels with ASGI (Daphne/Uvicorn)
- **Database**: PostgreSQL (via Supabase)
- **Task Queue**: Google Cloud Tasks
- **Deployment**: Google Cloud Run
- **Python**: 3.12+ (latest stable: 3.12.x)

## Project Structure

```
backend-service/
├── apps/                    # Django applications
│   ├── core/               # Shared utilities, middleware, services
│   ├── auth/               # Authentication endpoints
│   ├── twilio/             # Twilio webhook handlers
│   ├── ai/                 # AI service integrations
│   ├── sessions/           # Session management
│   ├── conversations/      # Conversation simulation
│   ├── admin/              # Admin endpoints
│   ├── feature_flags/      # Feature flag management
│   └── tasks/              # Cloud Tasks handlers
├── config/                 # Django configuration
│   ├── settings/           # Environment-specific settings
│   │   ├── base.py         # Base settings
│   │   ├── development.py  # Development settings
│   │   ├── staging.py      # Staging settings
│   │   ├── production.py   # Production settings
│   │   └── test.py         # Test settings
│   ├── urls.py             # URL routing
│   ├── wsgi.py             # WSGI application
│   └── asgi.py             # ASGI application (async)
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── manage.py               # Django management script
├── Dockerfile              # Production Docker image
└── README.md              # This file
```

## Getting Started

### Prerequisites

- Python 3.12 or higher
- PostgreSQL (or Supabase)
- Redis (for Channels/WebSocket support)
- Virtual environment (recommended)

### Local Development Setup

1. **Clone and navigate to the project:**
   ```bash
   cd backend-service
   ```

2. **Create virtual environment:**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server:**
   ```bash
   python manage.py runserver
   ```

   The server will run on `http://localhost:8080` (or the port specified in `API_PORT`).

### Testing

Run tests with pytest:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=apps --cov-report=html
```

### Code Quality

Format code with black:
```bash
black .
```

Lint with ruff:
```bash
ruff check .
```

Type checking with mypy:
```bash
mypy .
```

## Environment Variables

See `.env.example` for all available environment variables. Key variables:

- `DJANGO_ENV`: Environment (development, staging, production, test)
- `SECRET_KEY`: Django secret key (required)
- `DATABASE_URL`: PostgreSQL connection string
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key
- `TWILIO_ACCOUNT_SID`: Twilio account SID
- `TWILIO_AUTH_TOKEN`: Twilio auth token
- `OPENAI_API_KEY`: OpenAI API key
- `GCP_PROJECT_ID`: Google Cloud project ID

## API Endpoints

### Health Check
- `GET /health` - Service health status

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/signup` - User signup
- `POST /api/auth/logout` - User logout

### Twilio Webhooks
- `POST /api/twilio/voice` - Incoming call handler
- `POST /api/twilio/call-status` - Call status updates
- `POST /api/twilio/recording` - Recording available
- `POST /api/twilio/transcripts` - Real-time transcripts
- `POST /api/twilio/transcription-status` - Transcription status
- `POST /api/twilio/make-call` - Initiate outbound call
- `POST /api/twilio/hangup/<call_sid>` - Hangup call

### Sessions
- `GET /api/sessions/` - List sessions
- `GET /api/sessions/<id>/` - Get session details

### Conversations
- `POST /api/conversation/simulate` - Simulate conversation from audio

### Cloud Tasks
- `POST /api/tasks/transcribe-audio` - Transcribe audio file
- `POST /api/tasks/generate-ai-analysis` - Generate AI analysis

## Deployment to Google Cloud Run

### Build and Push Docker Image

1. **Build the image:**
   ```bash
   docker build -t gcr.io/YOUR_PROJECT_ID/verc-backend:latest .
   ```

2. **Push to Artifact Registry:**
   ```bash
   docker push gcr.io/YOUR_PROJECT_ID/verc-backend:latest
   ```

### Deploy with Terraform

The infrastructure is managed via Terraform. See `infra/` directory in the parent repository.

### Environment Variables in Cloud Run

Set environment variables via Terraform or Google Cloud Console. Secrets should be stored in Google Secret Manager and referenced in Cloud Run configuration.

## Architecture Decisions

### Async Support

- Django Channels for WebSocket support
- ASGI application (Daphne/Uvicorn) for async request handling
- Async views where needed for I/O-bound operations

### Database

- PostgreSQL via Supabase
- Connection pooling configured for production
- Migrations managed via Django

### Task Processing

- Google Cloud Tasks for async job processing
- OIDC authentication for secure task invocation
- Automatic retry and error handling

### Multi-Tenancy

- Organization-based isolation
- Tenant middleware extracts org_id from requests
- Database queries filtered by organization

### Logging

- Structured JSON logging for Cloud Logging
- Trace IDs for distributed tracing
- Log levels configurable per environment

## Development Guidelines

1. **Code Quality**: Follow PEP 8, use black for formatting, ruff for linting
2. **Type Hints**: Use type hints for better code documentation
3. **Async**: Use async/await for I/O-bound operations
4. **Testing**: Write tests for all new features
5. **Documentation**: Document complex logic and API endpoints

## Migration from TypeScript

This Django service is a refactor of the TypeScript/Express backend. Key mappings:

- Express routes → Django views (DRF)
- Express middleware → Django middleware
- TypeScript services → Python services in `apps/*/services/`
- Supabase client → `apps.core.services.supabase`
- Twilio service → `apps.twilio.services`
- AI providers → `apps.ai.providers`

## License

Proprietary - Verc

