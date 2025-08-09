# Requirements Document: Platform-Aware Database Schema

## Introduction

This feature implements platform identification in the database schema and frontend to prevent data corruption when switching between ActivityPub platforms (Pixelfed, Mastodon) and provide clear platform context to users.

## Requirements

### Requirement 1: Database Platform Identification

**User Story:** As a system administrator, I want the database to track which platform each piece of data belongs to, so that I can safely switch between platforms without data corruption.

#### Acceptance Criteria

1. WHEN a post is stored THEN the system SHALL record the platform type (pixelfed/mastodon) and instance URL
2. WHEN an image is stored THEN the system SHALL record the platform type associated with the parent post
3. WHEN a processing run is created THEN the system SHALL record the platform type and instance URL used
4. WHEN querying data THEN the system SHALL be able to filter by platform type
5. IF platform type is not specified THEN the system SHALL use the current configuration as default
6. WHEN migrating existing data THEN the system SHALL preserve data integrity and assign appropriate platform types

### Requirement 2: Platform-Aware Data Operations

**User Story:** As a developer, I want all database operations to be platform-aware, so that operations only affect data from the correct platform.

#### Acceptance Criteria

1. WHEN retrieving posts THEN the system SHALL filter by current platform configuration
2. WHEN updating media descriptions THEN the system SHALL only update items from the matching platform
3. WHEN performing cleanup operations THEN the system SHALL only clean data from the specified platform
4. WHEN generating statistics THEN the system SHALL provide platform-specific metrics
5. WHEN batch processing THEN the system SHALL group operations by platform type
6. IF no platform filter is specified THEN the system SHALL default to current configuration platform

### Requirement 3: Frontend Platform Indication

**User Story:** As a user, I want to see which platform and server I'm currently working with, so that I understand the context of my actions.

#### Acceptance Criteria

1. WHEN viewing the dashboard THEN the system SHALL display the current platform type and instance URL
2. WHEN reviewing images THEN the system SHALL show the source platform for each image
3. WHEN viewing statistics THEN the system SHALL indicate which platform the data represents
4. WHEN performing cleanup operations THEN the system SHALL show which platform will be affected
5. WHEN viewing processing history THEN the system SHALL display the platform used for each run
6. IF multiple platforms have data THEN the system SHALL provide platform filtering options

### Requirement 4: Safe Platform Switching

**User Story:** As a user, I want to safely switch between my configured platforms without losing or corrupting existing data, so that I can manage multiple ActivityPub instances through the web interface.

#### Acceptance Criteria

1. WHEN switching active platform THEN existing data SHALL remain intact and tagged with original platform
2. WHEN operating on a different platform THEN the system SHALL not affect data from other platforms
3. WHEN viewing data after platform switch THEN only relevant platform data SHALL be displayed
4. WHEN performing operations THEN the system SHALL prevent cross-platform data corruption
5. IF switching back to a previous platform THEN all original data SHALL be accessible and functional
6. WHEN platform connection is invalid THEN the system SHALL provide clear error messages and disable the platform

### Requirement 5: Data Migration and Backward Compatibility

**User Story:** As a system administrator, I want existing data to be properly migrated to the new schema, so that no data is lost during the upgrade and environment-based configuration is converted to database-managed platforms.

#### Acceptance Criteria

1. WHEN upgrading the database schema THEN existing posts SHALL be assigned to a platform created from current environment configuration
2. WHEN migrating data THEN all existing images SHALL inherit platform association from their parent posts
3. WHEN upgrading THEN existing processing runs SHALL be assigned to the migrated platform
4. WHEN migration completes THEN environment configuration SHALL be converted to a database platform record
5. WHEN migration completes THEN all data SHALL be accessible through the new platform-aware interface
6. IF migration fails THEN the system SHALL provide rollback capabilities
7. WHEN migration is complete THEN the system SHALL validate data integrity and platform associations

### Requirement 6: User-Managed Platform Connections

**User Story:** As a user, I want to manage multiple platform connections through the web interface, so that I can easily switch between different ActivityPub instances without editing configuration files.

#### Acceptance Criteria

1. WHEN accessing platform management THEN the system SHALL display all configured platform connections
2. WHEN adding a new platform THEN the system SHALL allow entering platform type, instance URL, username, and access token
3. WHEN testing a platform connection THEN the system SHALL validate credentials and connectivity
4. WHEN switching active platform THEN the system SHALL update the current working context
5. WHEN deleting a platform connection THEN the system SHALL warn about associated data and require confirmation
6. IF a platform connection fails THEN the system SHALL provide clear error messages and troubleshooting guidance

### Requirement 7: Platform Connection Database Schema

**User Story:** As a system administrator, I want platform connection details stored in the database, so that multiple users can manage their own platform connections independently.

#### Acceptance Criteria

1. WHEN storing platform connections THEN the system SHALL create a platforms table with connection details
2. WHEN associating data with platforms THEN the system SHALL reference the platform connection record
3. WHEN a user adds a platform THEN the system SHALL store encrypted credentials securely
4. WHEN querying platform data THEN the system SHALL join with platform connection information
5. IF platform credentials are invalid THEN the system SHALL mark the connection as inactive
6. WHEN migrating from environment configuration THEN the system SHALL create platform records from existing settings

### Requirement 8: Multi-User Platform Management

**User Story:** As a user, I want to manage my own platform connections independently of other users, so that I can work with my specific ActivityPub accounts.

#### Acceptance Criteria

1. WHEN logging into the web app THEN the system SHALL show only my platform connections
2. WHEN adding a platform connection THEN the system SHALL associate it with my user account
3. WHEN switching platforms THEN the system SHALL only show data from my accessible platforms
4. WHEN performing operations THEN the system SHALL use my selected platform credentials
5. IF I don't have access to a platform THEN the system SHALL prevent operations on that platform's data
6. WHEN sharing the application THEN other users SHALL not see my platform connections

### Requirement 9: Testing and Validation

**User Story:** As a developer, I want comprehensive tests to ensure platform-aware functionality works correctly, so that the system is reliable across different platforms.

#### Acceptance Criteria

1. WHEN running tests THEN the system SHALL validate platform identification for all data types
2. WHEN testing platform switching THEN the system SHALL verify data isolation between platforms
3. WHEN testing migrations THEN the system SHALL validate data integrity before and after
4. WHEN testing frontend THEN the system SHALL verify platform information is displayed correctly
5. WHEN testing cleanup operations THEN the system SHALL verify platform-specific data handling
6. WHEN testing user management THEN the system SHALL verify platform connection isolation between users
7. IF any test fails THEN the system SHALL provide detailed error information for debugging