# Project Overview

This project, named **Vedfolnir**, is a Python-based web application designed to improve web accessibility by automatically generating and managing alt text (image descriptions) for social media posts. It specifically targets federated platforms that use the **ActivityPub** protocol, such as Pixelfed and Mastodon.

The core functionality involves using the **Ollama** AI framework (with the LLaVA model) to generate intelligent image descriptions. It provides a comprehensive web interface for users to review, edit, and approve these AI-generated captions before updating the original social media posts.

## Tech Stack

- **Backend:**
    - **Language:** Python 3.8+
    - **Web Framework:** Flask
    - **Database ORM:** SQLAlchemy
    - **Database Migrations:** Alembic
- **Database:**
    - **Primary:** MySQL
    - **In-Memory Cache & Session Store:** Redis
- **AI / Machine Learning:**
    - **LLM Runtime:** Ollama
    - **Model:** LLaVA (e.g., `llava:7b`)
- **Frontend:**
    - Standard HTML, CSS, and JavaScript.
- **Infrastructure & Deployment:**
    - **Containerization:** Docker
    - **Orchestration:** Docker Compose
    - **Reverse Proxy:** Nginx (optional, included in Docker Compose)
    - **Target Cloud Platform:** AWS Elastic Beanstalk (suggested by `eb_app.py`)

# How to Build and Run

The application can be run either directly on the host machine or using the provided Docker configuration.

### Using Docker (Recommended)

The `docker-compose.yml` file defines all the necessary services (application, MySQL, Redis, Ollama).

1.  **Environment Setup:**
    Create a `.env` file from one of the examples (e.g., `.env.docker.example`) and populate it with the required secrets (database passwords, Flask secret key, etc.). The `README.md` recommends using a script for this:
    ```bash
    python3 scripts/setup/generate_env_secrets.py
    ```

2.  **Build and Run:**
    Execute the following command from the project root:
    ```bash
    docker-compose up --build
    ```
    The application will be available at `http://localhost:5000`.

### Locally (without Docker)

1.  **Prerequisites:**
    - Python 3.8+
    - An running instance of MySQL, Redis, and Ollama.

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment:**
    Create a `.env` file and configure the database URLs, Redis URL, Ollama URL, and other secrets.

4.  **Run the Application:**
    ```bash
    python web_app.py
    ```

# How to Test

The project includes a comprehensive test suite.

1.  **Run all tests:**
    ```bash
    python scripts/testing/run_comprehensive_tests.py
    ```

2.  **Run a specific test suite (e.g., security):**
    ```bash
    python scripts/testing/run_comprehensive_tests.py --suite security
    ```

### Playwright End-to-End Tests

Tests located in `tests/playwright/` are Playwright end-to-end browser tests. These tests interact with the running web application.

To run a specific Playwright test (e.g., `tests/playwright/0824_8_00_job_management_test.py`):

1.  **Ensure the Flask application is running.** You can start it locally using:
    ```bash
    python web_app.py
    ```
    (Note: This will run the Flask app in the foreground. For background execution, consider using `python web_app.py &` or a process manager.)

2.  **Execute the Playwright test script directly:**
    ```bash
    python tests/playwright/0824_8_00_job_management_test.py
    ```
    Replace `0824_8_00_job_management_test.py` with the actual test file name.

These tests are designed to be run as standalone Python scripts and are not integrated with the `run_comprehensive_tests.py` runner.

# Development Conventions

-   **Configuration:** The application is configured entirely through environment variables, which are loaded from a `.env` file into the `Config` object in `config.py`. This is a security best practice that avoids hardcoding secrets.
-   **Modularity:** The Flask application is highly modular, using **Blueprints** to organize routes and functionality. The main `web_app.py` file serves as an entry point that registers numerous blueprints from the `routes/`, `admin/`, and `monitoring/` directories.
-   **Database:** All database models are defined in `models.py` using SQLAlchemy. Database schema changes are managed through migration scripts using **Alembic**.
-   **Session Management:** The project features a sophisticated, custom-built session management system that uses **Redis** for high performance and scalability, replacing the default Flask session mechanism. Key files for this are `redis_session_manager.py` and `session_middleware_v2.py`.
-   **Security:** There is a strong focus on security, with custom middleware for CSRF protection, rate limiting, and enhanced input validation. These features are configurable via environment variables.
