# Copilot Instructions for Vedfolnir

## Project Architecture & Big Picture
- **Modular, service-oriented design**: Core components include the main bot controller (`main.py`), ActivityPub client/adapters (`activitypub_client.py`, platform adapters), image processor (`image_processor.py`), AI caption generator (`ollama_caption_generator.py`), database manager (`database.py`), and a Flask web app (`web_app.py`).
- **Platform adapter pattern**: All ActivityPub integrations use a factory/adapter approach—see `PlatformAdapterFactory` and `ActivityPubPlatform` base class for extension.
- **Unified session management**: Session logic is consolidated (see `session_manager.py`, `.kiro/specs/session-consolidation/design.md`).
- **Data flow**: Images without alt text are detected, processed by AI, reviewed by humans, and posted back to platforms. See the sequence diagrams in `.kiro/specs/vedfolnir/design.md`.
- **Security**: Enterprise-grade security is enforced everywhere (CSRF, input validation, session/cookie security, rate limiting, audit logging). All POST endpoints require CSRF protection.

## Developer Workflows
- **Setup**: Use `python scripts/setup/generate_env_secrets.py` and `python scripts/setup/verify_env_setup.py` (see `.env.example` for required variables). Never store secrets in code.
- **Run (dev/test)**: For interactive/test scenarios, use:
	```bash
	python web_app.py & sleep 10
	```
	For production, use:
	```bash
	python web_app.py
	```
	See `.kiro/steering/web-app-startup.md` for rationale and process management.
- **Testing**: All tests are run via `python scripts/testing/run_comprehensive_tests.py`. Test files are organized in `/tests` by type (unit, integration, frontend, security, performance, scripts). See `.kiro/steering/testing-guidelines.md` for structure and naming.
- **Mock/test data**: Always use helpers from `tests/test_helpers.py` and scripts in `tests/scripts/` for user/platform setup and cleanup. Never create test users manually.
- **Reset/Cleanup**: Use `python scripts/maintenance/reset_app.py --cleanup` or `--reset-complete` for safe/full resets.

## Project-Specific Conventions
- **Platform logic**: Never hardcode platform IDs/types—always use the adapter/factory pattern.
- **Session logic**: Use only the unified session manager and helpers; avoid direct DB/session manipulation.
- **Security**: All security toggles must be enabled in production. See `docs/SECURITY.md` and `.env.example` for required settings.
- **Testing**: Always clean up test users/platforms in `tearDown()` or after scripts. Use unique identifiers for test data.
- **Documentation**: When documenting startup, always provide both blocking and non-blocking patterns with context. See `.kiro/steering/web-app-startup.md` for standards.

## Integration Points & External Dependencies
- **Ollama/LLaVA**: Requires a running Ollama server with LLaVA model (`OLLAMA_URL`, `OLLAMA_MODEL` in env).
- **ActivityPub**: Platform clients/adapters for Pixelfed, Mastodon, etc. Configured via web UI.
- **Database**: SQLite by default, ready for PostgreSQL. Managed via SQLAlchemy.
- **Security**: All middleware, validation, and audit logging are in `security/` and related modules.

## Examples & Patterns
- **Add a new platform**: Implement a new adapter subclassing `ActivityPubPlatform`, register in `PlatformAdapterFactory`, and test via web UI and mock helpers.
- **Write a test**: Use `create_test_user_with_platforms` and `cleanup_test_user` from `tests/test_helpers.py` for setup/teardown. Place tests in the correct `/tests` subdir.
- **Document startup**: Always show both `python web_app.py & sleep 10` (test/dev) and `python web_app.py` (prod) with context.

## References
- [README.md](../README.md) — project overview, setup, and commands
- [docs/](../docs/) — user, admin, API, and security guides
- [docs/SECURITY.md](../docs/SECURITY.md) — security features and best practices
- [.kiro/specs/vedfolnir/design.md](../.kiro/specs/vedfolnir/design.md) — architecture and data flow
- [.kiro/steering/testing-guidelines.md](../.kiro/steering/testing-guidelines.md) — test structure and conventions
- [.kiro/steering/web-app-startup.md](../.kiro/steering/web-app-startup.md) — startup command patterns and rationale

---
If a pattern or workflow is unclear or missing, check the referenced docs or update this file to help future agents.
