# Requirements Document

## Introduction

This feature integrates caption generation functionality directly into the web application (web_app.py), allowing users to generate captions through the web interface instead of command-line tools. The system will use database-stored credentials rather than environment variables, operate within the context of the current logged-in user, and be fully aware of platform switching capabilities.

## Requirements

### Requirement 1

**User Story:** As a logged-in user, I want to generate captions for my posts through the web interface, so that I can manage caption generation without using command-line tools.

#### Acceptance Criteria

1. WHEN a user is logged into the web application THEN the system SHALL display caption generation options in the user interface
2. WHEN a user initiates caption generation THEN the system SHALL use the current user's database-stored credentials instead of .env file credentials
3. WHEN caption generation is triggered THEN the system SHALL process posts for the currently logged-in user only
4. WHEN caption generation completes THEN the system SHALL display results and status updates in the web interface

### Requirement 2

**User Story:** As a user with multiple platform accounts, I want caption generation to work with my currently selected platform, so that captions are generated for the correct account.

#### Acceptance Criteria

1. WHEN a user switches platforms in the web interface THEN the caption generation SHALL automatically use credentials for the newly selected platform
2. WHEN caption generation runs THEN the system SHALL fetch posts from the currently active platform only
3. WHEN displaying caption generation results THEN the system SHALL clearly indicate which platform the captions were generated for
4. IF no platform is selected THEN the system SHALL prompt the user to select a platform before allowing caption generation

### Requirement 3

**User Story:** As a user, I want to monitor caption generation progress in real-time through the web interface, so that I can see the status and results without switching to command-line tools.

#### Acceptance Criteria

1. WHEN caption generation starts THEN the system SHALL display a progress indicator showing current status
2. WHEN processing posts THEN the system SHALL show real-time updates of posts being processed
3. WHEN caption generation completes THEN the system SHALL display a summary of results including success/failure counts
4. WHEN errors occur during generation THEN the system SHALL display user-friendly error messages in the web interface
5. WHEN caption generation is running THEN the system SHALL prevent multiple simultaneous caption generation processes for the same user

### Requirement 4

**User Story:** As a user, I want the web-based caption generation to use the same AI models and processing logic as the command-line version, so that I get consistent caption quality regardless of interface.

#### Acceptance Criteria

1. WHEN generating captions through the web interface THEN the system SHALL use the same Ollama LLaVA model configuration as the command-line version
2. WHEN processing images THEN the system SHALL apply the same image classification and processing logic
3. WHEN storing generated captions THEN the system SHALL use the same database schema and relationships
4. WHEN caption generation parameters are configured THEN the system SHALL respect the same configuration settings (max length, optimal length, etc.)

### Requirement 5

**User Story:** As a user, I want to configure caption generation settings through the web interface, so that I can customize the generation process without editing configuration files.

#### Acceptance Criteria

1. WHEN accessing caption generation settings THEN the system SHALL display configurable options including max posts per run, caption length limits, and processing delays
2. WHEN updating caption generation settings THEN the system SHALL validate and save settings to the user's platform configuration
3. WHEN caption generation runs THEN the system SHALL use the user's saved settings instead of global defaults
4. IF no custom settings exist THEN the system SHALL use platform-specific default settings

### Requirement 6

**User Story:** As a user, I want to review and approve generated captions directly after the generation process, so that I can immediately manage the results without navigating to separate pages.

#### Acceptance Criteria

1. WHEN caption generation completes THEN the system SHALL automatically redirect to or display the caption review interface
2. WHEN viewing generated captions THEN the system SHALL show captions grouped by the generation batch with clear timestamps
3. WHEN approving captions THEN the system SHALL allow bulk approval operations for efficiency
4. WHEN editing captions THEN the system SHALL provide inline editing capabilities with real-time character count feedback

### Requirement 7

**User Story:** As a system administrator, I want web-based caption generation to maintain security and performance standards, so that the system remains stable and secure under load.

#### Acceptance Criteria

1. WHEN multiple users trigger caption generation THEN the system SHALL queue requests and prevent resource conflicts
2. WHEN caption generation runs THEN the system SHALL enforce the same rate limiting and API usage patterns as command-line version
3. WHEN handling user credentials THEN the system SHALL use secure database storage and never expose credentials in web responses
4. WHEN errors occur THEN the system SHALL log detailed information for debugging while showing user-friendly messages in the interface
5. WHEN caption generation is active THEN the system SHALL provide administrative monitoring capabilities to track system resource usage