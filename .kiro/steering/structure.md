# Project Structure

## Copyright and License Compliance

**CRITICAL**: All source code files in this project MUST include copyright and license headers. When creating or modifying any source code file, ensure it includes the proper header at the top using the correct comment syntax. See `.kiro/steering/copyright-license.md` for detailed requirements.

## Core Components

### Main Application
- `main.py`: Entry point for the bot, handles command-line arguments and orchestrates the processing flow
- `config.py`: Configuration management using environment variables
- `models.py`: SQLAlchemy data models for database entities
- `database.py`: Database connection and operations management

### ActivityPub Integration
- `activitypub_client.py`: Client for interacting with Pixelfed/ActivityPub API
- `post_service.py`: Service for handling post-related operations

### Image Processing
- `image_processor.py`: Handles image downloading, storage, and optimization
- `ollama_caption_generator.py`: Generates image captions using Ollama with LLaVA model

### Web Interface
- `web_app.py`: Flask web application for reviewing and managing captions
- `templates/`: HTML templates for the web interface
- `static/`: Static assets (CSS, JavaScript) for the web interface

### Utilities
- `utils.py` / `utils_new.py`: Utility functions and helpers
- `add_batch_id_column.py`: Database migration script
- `check_db.py`: Database inspection utility

## Directory Structure
- `.devcontainer/`: Development container configuration
- `.kiro/`: Kiro specifications and steering files
- `static/`: Static web assets
  - `css/`: Stylesheets
  - `js/`: JavaScript files
- `storage/`: Data storage
  - `database/`: SQLite database files
  - `images/`: Downloaded and processed images
- `templates/`: HTML templates for Flask
- `tests/`: Test files and test utilities
  - All test files should be placed here with naming convention `test_*.py`
- `__pycache__/`: Python bytecode cache (not tracked in version control)

## Data Flow
1. The bot retrieves posts from Pixelfed via the ActivityPub API
2. Images without alt text are identified and downloaded
3. The Ollama LLaVA model generates captions for these images
4. Generated captions are stored in the database
5. Human reviewers approve, edit, or reject captions via the web interface
6. Approved captions are posted back to Pixelfed via the API

## Development Patterns
- **Configuration**: Environment variables with dotenv
- **Database Access**: SQLAlchemy ORM with session management
- **Error Handling**: Comprehensive logging and graceful error recovery
- **API Interaction**: Async HTTP requests with retry mechanisms
- **Web Interface**: Flask with Jinja2 templates