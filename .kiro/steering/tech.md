# Technical Stack

## Copyright Requirement
**MANDATORY**: All source code files MUST include copyright headers. See `.kiro/steering/copyright-license.md`.

## Development Practices

### Test-Driven Development (MANDATORY)
**Requirement**: Strict TDD with Red-Green-Refactor cycle.
- Write failing test first
- Write minimal code to pass
- Refactor while keeping tests green
- Complete test suite MUST pass before task completion

## Core Technologies
- **Language**: Python 3.8+
- **Web Framework**: Flask 2.0+
- **Database**: MySQL/MariaDB with SQLAlchemy ORM
- **Session Management**: Redis primary, database fallback
- **AI Model**: Ollama with LLaVA for image captions
- **HTTP Client**: httpx for async requests
- **Security**: Enterprise-grade CSRF, input validation, rate limiting

## Session Management Architecture

**Primary**: Redis session storage with Flask cookies for session ID
**Fallback**: Database sessions for audit and recovery

### Redis Session Components
- **RedisSessionManager**: Primary session operations
- **Flask Session Interface**: Custom session handling
- **Session Middleware**: Request lifecycle integration
- **Database Audit**: Compliance and recovery trails

### Database Session Patterns (Current Best Practice)
```python
# Recommended: Direct db_manager usage
@app.route('/route')
@login_required
def function():
    with db_manager.get_session() as session:
        result = session.query(Model).filter_by(user_id=current_user.id).all()
        return render_template('template.html', data=result)

# Service layer pattern
class Service:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_data(self):
        with self.db_manager.get_session() as session:
            return session.query(Model).all()
```

### Redis Configuration
```bash
# Redis Settings
REDIS_URL=redis://localhost:6379/0
REDIS_SESSION_PREFIX=vedfolnir:session:
REDIS_SESSION_TIMEOUT=7200

# Flask Cookies
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=Lax

# Database Fallback
DB_SESSION_FALLBACK=true
DB_SESSION_SYNC=true
```

## Key Dependencies
- **pymysql**: MySQL connector
- **requests/httpx**: HTTP clients
- **Pillow**: Image processing
- **SQLAlchemy**: Database ORM
- **Flask**: Web framework
- **redis**: Session storage
- **cryptography**: Platform credential encryption

## Environment Configuration

### Database (MySQL)
```bash
DATABASE_URL=mysql+pymysql://user:password@localhost/vedfolnir?charset=utf8mb4
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
```

### Security
```bash
FLASK_SECRET_KEY=<generated-key>
PLATFORM_ENCRYPTION_KEY=<fernet-key>
SECURITY_CSRF_ENABLED=true
SECURITY_RATE_LIMITING_ENABLED=true
```

### AI/ML
```bash
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llava:7b
CAPTION_MAX_LENGTH=500
```

## Common Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Setup MySQL database
mysql -u root -p
CREATE DATABASE vedfolnir CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'vedfolnir_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir_user'@'localhost';

# Generate environment and admin user
python scripts/setup/generate_env_secrets.py
python scripts/setup/verify_env_setup.py
```

### Running
```bash
# Bot processing
python main.py --users username1 username2

# Web interface (non-blocking for testing)
python web_app.py & sleep 10

# Web interface (blocking for production)
python web_app.py
```

### Database Management
```bash
# Check status
python scripts/maintenance/reset_app.py --status

# Cleanup
python scripts/maintenance/reset_app.py --cleanup

# MySQL migration (from SQLite)
python scripts/mysql_migration/migrate_to_mysql.py --backup
```

## Recent Major Updates

### MySQL Migration (2025)
- Complete SQLite → MySQL/MariaDB migration
- Performance improvements with connection pooling
- Enterprise features and optimization
- Migration tools with backup/verification

### Security Enhancements (2025)
- 100% security score implementation
- CSRF protection, input validation, rate limiting
- Audit logging and encrypted credentials

### Redis Session Management (2025)
- High-performance Redis session storage
- Database fallback for reliability
- Real-time cross-tab synchronization
- Performance monitoring and health checks

## Caption Configuration
```bash
CAPTION_MAX_LENGTH=500                    # Maximum length
CAPTION_OPTIMAL_MIN_LENGTH=150            # Minimum optimal
CAPTION_OPTIMAL_MAX_LENGTH=450           # Maximum optimal
```

## Enhanced Image Classification
```bash
USE_ENHANCED_CLASSIFICATION=true
CLASSIFICATION_CONFIDENCE_THRESHOLD=0.7
LLAVA_CLASSIFICATION_TEMPERATURE=0.1
```

**Pipeline**: Computer Vision → Scene Analysis → LLaVA Model → Hybrid Decision

## Testing Framework

**Framework**: Python `unittest` (NOT pytest)

```bash
# Run specific tests
python -m unittest tests.test_configuration_examples -v

# Run all tests
python -m unittest discover tests

# Use test runner
python run_tests.py --suite safe --verbose    # No config required
python run_tests.py --suite all --verbose     # Full config required
```

### Mock User Management
```python
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

class TestFeature(unittest.TestCase):
    def setUp(self):
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager, username="test_user", role=UserRole.REVIEWER
        )
    
    def tearDown(self):
        cleanup_test_user(self.user_helper)
```

### Testing Guidelines
- Use `unittest` framework exclusively
- Test files: `test_*.py` in `tests/` directory
- Mock external dependencies and database connections
- Always use standardized mock user helpers
- Include descriptive docstrings and proper cleanup
