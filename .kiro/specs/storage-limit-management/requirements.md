# Requirements Document

## Introduction

This feature implements automatic storage limit management for image caption generation to prevent storage overflow and provide proper notifications to users and administrators. The system will monitor total image storage usage, block caption generation when limits are reached, notify administrators via email, and display appropriate user messages similar to the enhanced maintenance mode system.

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want to configure a maximum storage limit for caption images so that the system doesn't consume unlimited disk space.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL read a CAPTION_MAX_STORAGE_GB configuration value from environment variables
2. IF CAPTION_MAX_STORAGE_GB is not set THEN the system SHALL use a default value of 10 GB
3. WHEN CAPTION_MAX_STORAGE_GB is configured THEN it SHALL be validated as a positive number
4. IF CAPTION_MAX_STORAGE_GB is invalid THEN the system SHALL log an error and use the default value

### Requirement 2

**User Story:** As a system administrator, I want the system to automatically monitor storage usage so that I'm aware when limits are approaching.

#### Acceptance Criteria

1. WHEN caption generation is requested THEN the system SHALL calculate total image storage usage in bytes
2. WHEN calculating storage usage THEN the system SHALL sum all image files in the storage/images directory
3. WHEN storage usage is calculated THEN it SHALL be converted to GB for comparison with the limit
4. WHEN storage usage exceeds 80% of the limit THEN the system SHALL log a warning message
5. WHEN storage usage reaches or exceeds the configured limit THEN the system SHALL block new caption generation

### Requirement 3

**User Story:** As a system administrator, I want to receive email notifications when storage limits are reached so that I can take action promptly.

#### Acceptance Criteria

1. WHEN storage usage reaches the configured limit THEN the system SHALL send email notifications to all administrators
2. WHEN sending storage limit emails THEN the message SHALL include current storage usage and the configured limit
3. WHEN sending storage limit emails THEN the message SHALL include a direct link to the admin cleanup page
4. WHEN sending storage limit emails THEN the system SHALL not send duplicate emails within a 24-hour period
5. IF email sending fails THEN the system SHALL log the error but continue blocking caption generation

### Requirement 4

**User Story:** As a regular user, I want to see clear notifications when caption generation is unavailable due to storage limits so that I understand why the service is temporarily disabled.

#### Acceptance Criteria

1. WHEN a user visits the caption generation page AND storage limit is reached THEN the system SHALL display a storage limit notification
2. WHEN displaying storage limit notification THEN it SHALL explain that caption generation is temporarily unavailable
3. WHEN displaying storage limit notification THEN it SHALL inform users that administrators are working on the issue
4. WHEN displaying storage limit notification THEN it SHALL be styled consistently with maintenance mode notifications
5. WHEN storage limit is active THEN the caption generation form SHALL be disabled and hidden

### Requirement 5

**User Story:** As a regular user, I want caption generation to automatically resume when storage space is available so that I can continue using the service.

#### Acceptance Criteria

1. WHEN storage usage drops below the configured limit THEN caption generation SHALL be automatically re-enabled
2. WHEN caption generation is re-enabled THEN the storage limit notification SHALL be removed
3. WHEN caption generation is re-enabled THEN the caption generation form SHALL be displayed and functional
4. WHEN checking storage limits THEN the system SHALL perform the check before each caption generation request

### Requirement 6

**User Story:** As a system administrator, I want to view current storage usage in the admin dashboard so that I can monitor the situation.

#### Acceptance Criteria

1. WHEN viewing the admin dashboard THEN it SHALL display current image storage usage in GB
2. WHEN viewing the admin dashboard THEN it SHALL display the configured storage limit
3. WHEN viewing the admin dashboard THEN it SHALL display the percentage of storage used
4. WHEN storage usage exceeds 80% THEN the dashboard SHALL highlight the storage status with a warning color
5. WHEN storage limit is reached THEN the dashboard SHALL highlight the storage status with an error color

### Requirement 7

**User Story:** As a system administrator, I want to manually override storage limits temporarily so that I can allow caption generation in emergency situations.

#### Acceptance Criteria

1. WHEN in the admin interface THEN administrators SHALL have an option to temporarily override storage limits
2. WHEN storage limit override is activated THEN it SHALL allow caption generation for a configurable time period (default 1 hour)
3. WHEN storage limit override is active THEN the admin dashboard SHALL display the override status and remaining time
4. WHEN storage limit override expires THEN the system SHALL automatically re-enable storage limit enforcement
5. WHEN storage limit override is used THEN the system SHALL log the administrator action for audit purposes

### Requirement 8

**User Story:** As a system administrator, I want the storage limit system to integrate with the existing cleanup tools so that I can easily manage storage when limits are reached.

#### Acceptance Criteria

1. WHEN storage limit emails are sent THEN they SHALL include direct links to the admin cleanup page
2. WHEN viewing the admin cleanup page AND storage limit is active THEN it SHALL display prominent storage limit warnings
3. WHEN using cleanup tools THEN they SHALL update storage calculations in real-time
4. WHEN cleanup operations free sufficient space THEN storage limit blocking SHALL be automatically lifted
5. WHEN cleanup operations are performed THEN the system SHALL recalculate storage usage immediately