# Requirements Document

## Introduction

The Vedfolnir is a system designed to enhance accessibility on ActivityPub platforms (Pixelfed and Mastodon) by automatically generating and managing alt text (image descriptions) for posts that lack them. The bot identifies images without alt text, uses AI to generate appropriate descriptions, provides a human review interface, and updates the original posts with approved descriptions. This feature aims to make visual content more accessible to users with visual impairments who rely on screen readers.

## Requirements

### Requirement 1: Image Discovery and Processing

**User Story:** As an ActivityPub instance administrator, I want to automatically identify posts with images lacking alt text, so that I can make my platform more accessible.

#### Acceptance Criteria

1. WHEN the bot is run with a user ID THEN the system SHALL retrieve that user's recent posts from the configured ActivityPub platform.
2. WHEN retrieving posts THEN the system SHALL identify images without alt text descriptions.
3. WHEN an image without alt text is found THEN the system SHALL download and store the image locally.
4. WHEN an image is downloaded THEN the system SHALL optimize it for processing while preserving visual quality.
5. WHEN an image is processed THEN the system SHALL store the original post creation date for proper chronological sorting.
6. WHEN processing posts THEN the system SHALL track processing statistics including posts processed, images found, and errors encountered.
7. WHEN the system encounters errors THEN it SHALL log detailed error information and continue processing other images.

### Requirement 2: Alt Text Generation

**User Story:** As a content moderator, I want the system to automatically generate high-quality alt text for images   so that I can efficiently improve accessibility without manual description of every image.

#### Acceptance Criteria

1. WHEN an image without alt text is identified THEN the system SHALL use the Ollama endpoint and the llava:7b model to generate an appropriate description.
2. WHEN generating alt text THEN the system SHALL ensure descriptions are concise (under 500 characters by default, configurable) for optimal screen reader compatibility.
3. WHEN generating alt text THEN the system SHALL focus on describing the main subjects, actions, setting, and important visual details.
4. WHEN the AI model fails to generate a caption THEN the system SHALL log the error and mark the image for manual review.
5. WHEN a caption is generated THEN the system SHALL store it in the database linked to the original image.

### Requirement 3: Human Review Interface

**User Story:** As a content reviewer, I want a user-friendly interface to review, edit, and approve AI-generated alt text, so that I can ensure the quality and appropriateness of descriptions before they go live.

#### Acceptance Criteria

1. WHEN a user accesses the review interface THEN the system SHALL display a list of images with pending reviews sorted by original post creation date (most recent posts first).
2. WHEN reviewing an image THEN the system SHALL display the image alongside its AI-generated caption.
3. WHEN reviewing an image THEN the system SHALL allow the reviewer to approve, reject, or edit the caption.
4. WHEN a reviewer edits a caption THEN the system SHALL save the changes and update the status accordingly.
5. WHEN multiple images need review THEN the system SHALL provide a batch review interface for efficient processing with images sorted by original post creation date (most recent posts first) by default.
6. WHEN a caption is approved THEN the system SHALL mark it ready for posting to the configured ActivityPub platform.

### Requirement 4: ActivityPub Platform Integration

**User Story:** As an ActivityPub platform user, I want approved alt text to be automatically added to my posts, so that my content becomes accessible without manual intervention.

#### Acceptance Criteria

1. WHEN a caption is approved THEN the system SHALL update the original post on the configured ActivityPub platform with the new alt text.
2. WHEN updating a post THEN the system SHALL use the appropriate platform-specific API endpoints for media description updates.
3. WHEN a post is successfully updated THEN the system SHALL mark the image as posted in the database.
4. WHEN the system encounters API errors THEN it SHALL log the issue and retry at a later time.
5. WHEN integrating with an ActivityPub platform THEN the system SHALL respect platform-specific API rate limits and authentication requirements.

### Requirement 5: Multi-Platform ActivityPub Support

**User Story:** As a system administrator, I want to use the Vedfolnir with both Pixelfed and Mastodon servers, so that I can improve accessibility across different ActivityPub platforms.

#### Acceptance Criteria

1. WHEN the system is configured THEN it SHALL support both Pixelfed and Mastodon as ActivityPub platform types via an `ACTIVITYPUB_API_TYPE` setting.
2. WHEN `ACTIVITYPUB_API_TYPE` is set to "mastodon" THEN the system SHALL use Mastodon-specific API endpoints and authentication methods.
3. WHEN `ACTIVITYPUB_API_TYPE` is set to "pixelfed" THEN the system SHALL continue to use the existing Pixelfed API implementation.
4. WHEN using Mastodon authentication THEN the system SHALL support OAuth2 client credentials (client key, client secret) and access token authentication.
5. WHEN retrieving posts from Mastodon THEN the system SHALL use Mastodon's statuses API endpoints to get user posts.
6. WHEN identifying images in Mastodon posts THEN the system SHALL parse Mastodon's media attachment format to find images without alt text.
7. WHEN updating media descriptions on Mastodon THEN the system SHALL use Mastodon's media update API endpoints.
8. WHEN the system encounters platform-specific API differences THEN it SHALL handle them gracefully through platform adapters.
9. WHEN configuration is invalid or incomplete THEN the system SHALL provide clear error messages indicating what settings are missing.
10. WHEN switching between platforms THEN the system SHALL maintain the same core functionality (image discovery, caption generation, review interface, posting).
11. WHEN `ACTIVITYPUB_API_TYPE` is not set THEN the system SHALL default to "pixelfed" for backward compatibility.
12. WHEN existing Pixelfed configuration is present THEN it SHALL continue to work without modification.

### Requirement 6: System Management and Monitoring

**User Story:** As a system administrator, I want to monitor the bot's performance and manage its operation, so that I can ensure it's functioning correctly and efficiently.

#### Acceptance Criteria

1. WHEN the bot runs THEN the system SHALL log detailed information about its operations.
2. WHEN the web interface is accessed THEN the system SHALL display statistics about processing status and results.
3. WHEN errors occur THEN the system SHALL provide detailed logs for troubleshooting.
4. WHEN the system is configured THEN it SHALL use environment variables or configuration files for settings.
5. WHEN the system stores data THEN it SHALL use a structured database with appropriate schemas.