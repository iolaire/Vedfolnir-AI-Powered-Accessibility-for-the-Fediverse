# Project Structure

## Copyright Compliance
**CRITICAL**: All source code files MUST include copyright headers. See `.kiro/steering/copyright-license.md`.

## Core Components

### Application Core
- `main.py`: Bot entry point and orchestration
- `config.py`: Configuration management with MySQL support
- `models.py`: SQLAlchemy data models
- `database.py`: MySQL connection and operations with pooling
- `web_app.py`: Flask web application

### ActivityPub Integration
- `activitypub_client.py`: Platform API client
- `post_service.py`: Post operations
- `platform_adapter_factory.py`: Platform-specific adapters

### Image Processing & AI
- `image_processor.py`: Image handling and optimization
- `ollama_caption_generator.py`: AI caption generation with LLaVA
- `caption_quality_assessment.py`: Caption validation

### Session Management (Redis Primary)
- `redis_session_manager.py`: Primary Redis session backend
- `session_config.py`: Session configuration
- `session_cookie_manager.py`: Flask cookie handling
- `unified_session_manager.py`: Database fallback

### Security System
- `security/core/`: CSRF, rate limiting, encryption
- `security/validation/`: Input validation and sanitization
- `security/monitoring/`: Security logging and monitoring

### Web Interface
- `routes/`: Route handlers (user, admin, platform management)
- `admin/`: Administrative functionality
- `templates/`: HTML templates
- `static/`: CSS, JavaScript assets

### Services & Utilities
- `services/`: Business logic (user, platform, email services)
- `utils.py`: Utility functions
- `scripts/`: Setup, maintenance, migration, testing utilities

## Directory Structure
```
├── .devcontainer/          # Development container
├── .kiro/                  # Kiro specifications
├── static/                 # Main app assets
├── admin/static/           # Admin assets
├── storage/                # Data storage
│   ├── backups/           # Application/DB backups
│   ├── images/            # Downloaded images
│   └── temp/              # Temporary files
├── templates/             # Main templates
├── admin/templates/       # Admin templates
├── tests/                 # All test files
├── scripts/               # Utility scripts
├── docs/                  # Documentation
├── logs/                  # Application logs
├── security/              # Security modules
├── routes/                # Flask routes
└── services/              # Business logic
```

## Data Flow
1. User authentication → Session creation (Redis)
2. Platform management → API connections
3. Post retrieval → Image processing → AI caption generation
4. Data persistence (MySQL) → Human review → Caption publishing
5. Security monitoring & performance tracking

## File Organization Rules

### Documentation (`docs/`)
Organize by category: admin, deployment, frontend, implementation, integration, maintenance, migration, monitoring, performance, security, services, storage, testing, websocket, web-caption-generation.

### Tests (`tests/`)
Organize by functionality: admin, frontend, integration, migration, monitoring, performance, user, websocket, web_caption_generation, reports.

### Scripts (`scripts/`)
Organize by purpose: debug, examples, utilities, setup, maintenance, testing, mysql_migration.

### File Naming
- **Test Files**: `test_*.py`
- **Debug Scripts**: `debug_*.py`
- **Demo Scripts**: `demo_*.py`
- **Validation**: `validate_*.py` or `verify_*.py`

### Git History
Always use `git mv` to preserve history when moving files.

## Development Patterns
- **Configuration**: Environment variables with secure credential management
- **Database**: SQLAlchemy ORM with MySQL pooling
- **Error Handling**: Comprehensive logging and graceful recovery
- **API Interaction**: Async HTTP with retry mechanisms
- **Web Interface**: Flask with CSRF protection and input validation
- **Security**: Enterprise-grade with encryption and audit logging
- **Testing**: Comprehensive unittest framework
- **Performance**: Built-in monitoring and optimization
