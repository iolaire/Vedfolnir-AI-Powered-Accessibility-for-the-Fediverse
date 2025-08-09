# Requirements Document

## Introduction

This feature involves reverting the security-related environment variables back to the .env file approach for simplicity while maintaining proper documentation and security best practices. The goal is to move AUTH_ADMIN_USERNAME, AUTH_ADMIN_EMAIL, AUTH_ADMIN_PASSWORD, FLASK_SECRET_KEY, and PLATFORM_ENCRYPTION_KEY back to .env/.env.example files and ensure clear documentation exists for generating and managing these sensitive values.

## Requirements

### Requirement 1

**User Story:** As a developer setting up the Vedfolnir application, I want all authentication and security settings to be managed through the .env file, so that I have a simple and consistent configuration approach.

#### Acceptance Criteria

1. WHEN the application starts THEN it SHALL load AUTH_ADMIN_USERNAME, AUTH_ADMIN_EMAIL, AUTH_ADMIN_PASSWORD, FLASK_SECRET_KEY, and PLATFORM_ENCRYPTION_KEY from the .env file
2. WHEN a developer copies .env.example to .env THEN they SHALL have placeholder values for all required security settings
3. IF any required security setting is missing from .env THEN the application SHALL provide clear error messages indicating which variables need to be set

### Requirement 2

**User Story:** As a developer, I want clear documentation on how to generate secure values for authentication and encryption settings, so that I can properly configure the application with strong security.

#### Acceptance Criteria

1. WHEN a developer reads the security documentation THEN they SHALL find instructions for generating secure FLASK_SECRET_KEY values
2. WHEN a developer reads the security documentation THEN they SHALL find instructions for generating secure PLATFORM_ENCRYPTION_KEY values
3. WHEN a developer reads the security documentation THEN they SHALL find instructions for setting up admin authentication credentials
4. WHEN a developer reads the security documentation THEN they SHALL understand the security implications of each setting

### Requirement 3

**User Story:** As a system administrator, I want the .env.example file to contain secure placeholder values and clear comments, so that I understand what each setting does and how to configure it properly.

#### Acceptance Criteria

1. WHEN examining .env.example THEN it SHALL contain placeholder values for AUTH_ADMIN_USERNAME, AUTH_ADMIN_EMAIL, and AUTH_ADMIN_PASSWORD
2. WHEN examining .env.example THEN it SHALL contain placeholder values for FLASK_SECRET_KEY and PLATFORM_ENCRYPTION_KEY with comments explaining their purpose
3. WHEN examining .env.example THEN each security setting SHALL have clear comments explaining its purpose and security requirements
4. WHEN examining .env.example THEN it SHALL include warnings about not using default values in production

### Requirement 4

**User Story:** As a developer, I want the configuration loading code to be simplified back to reading from .env files, so that the application startup is straightforward and reliable.

#### Acceptance Criteria

1. WHEN config.py loads configuration THEN it SHALL read security settings directly from environment variables loaded by python-dotenv
2. WHEN the application starts THEN it SHALL NOT attempt to load security settings from system environment variables outside of .env
3. WHEN configuration validation occurs THEN it SHALL verify all required security settings are present and non-empty
4. IF any security setting validation fails THEN the application SHALL provide specific guidance on how to fix the configuration

### Requirement 5

**User Story:** As a developer, I want existing security documentation and setup scripts to be updated to reflect the .env file approach, so that all documentation remains accurate and helpful.

#### Acceptance Criteria

1. WHEN reading security documentation THEN it SHALL reflect the .env file approach for all security settings
2. WHEN using setup scripts THEN they SHALL generate or update .env files rather than system environment variables
3. WHEN following setup instructions THEN they SHALL guide users to configure .env files properly
4. WHEN troubleshooting configuration issues THEN documentation SHALL provide .env-specific guidance