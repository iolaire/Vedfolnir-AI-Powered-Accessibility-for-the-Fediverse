# Implementation Plan

- [x] 1. Implement multi-user processing support
  - Add functionality to process multiple users in a single run
  - Update command-line interface to accept multiple user IDs
  - Modify the main controller to handle batches of users
  - _Requirements: 1.1, 5.4_

- [x] 2. Enhance error handling and recovery
  - [x] 2.1 Implement retry mechanism for failed API calls
    - [x] 2.1.1. Enhance RetryConfig class with additional parameters
      - Add jitter support to prevent thundering herd problem
      - Add specific error message pattern matching
      - Add configuration for different error types (timeout, connection, server)
      - _Requirements: 1.6, 4.4_
    
    - [x] 2.1.2. Create statistics tracking for retries
      - Implement counters for retry attempts, successes, and failures
      - Add timing measurements for retry operations
      - Create summary reporting function
      - _Requirements: 1.6, 4.4, 5.3_
    
    - [x] 2.1.3. Update ActivityPubClient to use enhanced retry mechanism
      - Apply retry decorators to all API call methods
      - Configure retry parameters based on environment variables
      - Add specific retry logic for Pixelfed API
      - _Requirements: 1.6, 4.4_
    
    - [x] 2.1.4. Add retry reporting to main application
      - Display retry statistics after processing runs
      - Log detailed retry information for debugging
      - Add retry information to processing run records
      - _Requirements: 1.6, 4.4, 5.3_

  - [x] 2.2 Improve error logging and reporting
    - Enhance error messages with more context
    - Implement structured logging for better analysis
    - Create error summary reports after processing runs
    - _Requirements: 5.3_

- [x] 3. Optimize image processing
  - [x] 3.1 Add support for additional image formats
    - Extend image processor to handle more image formats (AVIF, HEIC)
    - Add appropriate conversion logic for unsupported formats
    - Update file extension detection logic
    - _Requirements: 1.3, 1.4_

  - [x] 3.2 Implement image validation
    - Add checks for image validity before processing
    - Detect and handle corrupted images gracefully
    - Add image dimension and size validation
    - _Requirements: 1.3, 1.4_

  - [x] 3.3 Add tests for image processing functionality
    - Create tests for additional image format support
    - Implement tests for image validation
    - Test error handling for corrupted images
    - _Requirements: 1.3, 1.4, 5.3_

- [x] 4. Enhance caption generation
  - [x] 4.1 Implement prompt templates for different image types
    - Create specialized prompts for different categories of images
    - Add logic to detect image content type
    - Select appropriate prompt based on image content
    - _Requirements: 2.1, 2.3_
    
  - [x] 4.1.1 Add tests for prompt templates and image classification
    - Test image classification functionality
    - Test prompt template selection based on image category
    - Verify confidence score calculation
    - _Requirements: 2.1, 2.3, 5.3_

  - [x] 4.2 Optimize Ollama integration with llava:7b model
    - Ensure proper configuration for connecting to existing Ollama endpoint
    - Add environment variable support for Ollama URL and model name
    - Implement connection validation and error handling for Ollama API
    - Add detailed logging for model interactions
    - _Requirements: 2.1_

  - [x] 4.3 Implement caption quality assessment
    - Add metrics for evaluating caption quality (relevance, length, detail)
    - Flag low-quality captions for special review
    - Provide feedback on caption quality in the review interface
    - Ensure captions are concise (under 500 characters by default, configurable) for optimal screen reader compatibility
    - _Requirements: 2.2, 2.3_
    
  - [x] 4.4 Enhance caption formatting and cleanup
    - Implement better sentence structure and grammar checking
    - _Requirements: 2.2, 2.3_
    
  - [x] 4.5 Implement fallback mechanisms for caption generation
    - Add retry logic for failed caption generation attempts
    - Create fallback prompts for when specialized prompts don't yield good results
    - Implement a simpler backup model option when primary model fails
    - _Requirements: 2.4, 2.5_

  - [x] 4.6 Simplify caption generation by removing image classification
    - Remove image classification and category-specific prompt templates
    - Use a single, general-purpose prompt for all images
    - Remove image_classifier.py, enhanced_image_classifier.py, and related files
    - Update ollama_caption_generator.py to use only general prompts
    - Simplify main.py to remove classification calls
    - _Requirements: 2.1, 2.3_

- [x] 5. Improve database management
  - [x] 5.1 Implement database migrations
    - Set up Alembic for managing schema changes
    - Create initial migration from current schema
    - Document migration process
    - _Requirements: 5.5_

  - [x] 5.2 Optimize database performance
    - Add indexes for frequently queried fields
    - Implement connection pooling
    - Add database query logging for performance analysis
    - _Requirements: 5.5_

  - [x] 5.3 Add data cleanup functionality
    - Implement routine for archiving old processing runs
    - Add configuration for data retention policies
    - Create admin interface for manual data cleanup
    - _Requirements: 5.5_

- [-] 6. Enhance web interface
  - [x] 6.1 Implement user authentication
    - Add login/logout functionality
    - Implement role-based access control
    - Secure API endpoints with authentication
    - _Requirements: 3.1, 3.3_

  - [x] 6.2 Improve review interface
    - Add keyboard shortcuts for common actions
    - Implement side-by-side comparison of original and edited captions
    - Add image zooming and panning capabilities
    - _Requirements: 3.2, 3.3, 3.4_

  - [x] 6.3 Enhance batch review capabilities
    - Implement filtering and sorting options
    - Add bulk action functionality
    - Improve pagination for large sets of images
    - _Requirements: 3.5_

- [-] 7. Improve ActivityPub integration
  - [x] 7.1 Implement rate limiting for API calls
    - Add configurable rate limits for API requests
    - Implement backoff strategy for rate limit errors
    - Add monitoring for API usage
    - _Requirements: 4.5_

  - [x] 7.2 Add support for additional ActivityPub platforms
    - Create platform-specific adapters
    - Implement platform detection logic
    - Add configuration options for platform selection
    - _Requirements: 4.2_

  - [x] 7.3 Enhance post update functionality
    - Implement batched updates to reduce API calls
    - Add verification of successful updates
    - Implement rollback for failed updates
    - _Requirements: 4.1, 4.3_

- [x] 8. Implement system monitoring and management
  - [x] 8.1 Create health check endpoints
    - Add API endpoints for system status
    - Implement component-level health checks
    - Create dashboard for system health
    - _Requirements: 5.1, 5.2_

  - [x] 8.3 Add performance metrics collection
    - Implement timing for key operations
    - Add memory usage tracking
    - Create performance reports
    - _Requirements: 5.2_

- [x] 9. Add comprehensive testing
  - [x] 9.1 Expand unit test coverage
    - Add tests for retry mechanism
    - Create tests for caption generation fallbacks
    - Add tests for database optimizations
    - _Requirements: 5.3_

  - [x] 9.2 Enhance integration tests
    - Create tests for component interactions
    - Implement mock Pixelfed API for testing
    - Add database integration tests
    - _Requirements: 5.3_

  - [x] 9.3 Set up end-to-end tests
    - Create test scenarios for complete workflows
    - Implement browser automation for web interface testing
    - Add performance benchmarks
    - _Requirements: 5.3_

- [-] 10. Implement Multi-Platform ActivityPub Support
  - [x] 10.1 Update configuration system for multi-platform support
    - Update config.py to handle ACTIVITYPUB_API_TYPE setting
    - Add Mastodon-specific configuration variables (client key, secret, access token)
    - Implement backward compatibility for existing Pixelfed configurations
    - Add configuration validation for platform-specific required settings
    - **Testing Requirements:**
      - Write unit tests for configuration parsing with both platform types
      - Test default behavior when ACTIVITYPUB_API_TYPE is not set (should default to pixelfed)
      - Test configuration validation errors for missing required Mastodon credentials
      - Test configuration validation errors for missing required Pixelfed credentials
      - Test backward compatibility with existing .env files
      - Test environment variable precedence and overrides
      - Test configuration object creation for both platforms
      - Add integration tests for configuration loading in different deployment scenarios
    - _Requirements: 5.1, 5.9_

  - [x] 10.2 Create platform adapter architecture
    - Create base ActivityPubPlatform abstract class defining common interface
    - Implement PixelfedPlatform adapter for existing functionality
    - Implement MastodonPlatform adapter for Mastodon-specific API calls
    - Add platform detection and adapter factory pattern
    - **Testing Requirements:**
      - Write unit tests for the abstract base class interface compliance
      - Test PixelfedPlatform adapter maintains all existing functionality
      - Test MastodonPlatform adapter implements all required methods
      - Test platform adapter factory creates correct adapter based on configuration
      - Test factory error handling for unsupported platform types
      - Mock both platform adapters to test interface consistency
      - Test adapter method signatures match the abstract base class
      - Add integration tests for adapter instantiation and basic functionality
      - Test adapter cleanup and resource management
    - _Requirements: 5.2, 5.3, 5.8_

  - [ ] 10.3 Implement Mastodon API integration
    - [x] 10.3.1 Implement Mastodon authentication
      - Add OAuth2 client credentials authentication for Mastodon
      - Update HTTP client to use Mastodon authentication headers
      - Add token validation and refresh logic if needed
      - **Testing Requirements:**
        - Mock Mastodon OAuth2 endpoints for authentication testing
        - Test successful authentication with valid credentials
        - Test authentication failure with invalid client key/secret
        - Test authentication failure with invalid access token
        - Test HTTP client header injection for Mastodon authentication
        - Test token validation logic with valid and invalid tokens
        - Test token refresh mechanism if implemented
        - Test authentication timeout and retry scenarios
        - Test authentication with different Mastodon instance configurations
      - _Requirements: 5.4_
    
    - [x] 10.3.2 Implement Mastodon posts retrieval
      - Add Mastodon statuses API endpoint integration (/api/v1/accounts/{id}/statuses)
      - Parse Mastodon post format and extract media attachments
      - Handle Mastodon-specific pagination and limits
      - **Testing Requirements:**
        - Mock Mastodon /api/v1/accounts/{id}/statuses endpoint responses
        - Test posts retrieval with valid user IDs
        - Test posts retrieval with invalid/non-existent user IDs
        - Test parsing of Mastodon post JSON format
        - Test extraction of media attachments from Mastodon posts
        - Test handling of posts with no media attachments
        - Test handling of posts with multiple media attachments
        - Test Mastodon pagination (max_id, since_id parameters)
        - Test API rate limiting and error responses
        - Test posts retrieval with different limit parameters
        - Create test fixtures with realistic Mastodon API responses
      - _Requirements: 5.5_
    
    - [x] 10.3.3 Implement Mastodon media processing
      - Parse Mastodon media attachment JSON format
      - Identify images without alt text descriptions in Mastodon format
      - Extract image URLs and metadata from Mastodon attachments
      - **Testing Requirements:**
        - Test parsing of Mastodon media attachment JSON structure
        - Test identification of images vs other media types (video, audio)
        - Test detection of images with existing alt text (should be skipped)
        - Test detection of images without alt text (should be processed)
        - Test extraction of image URLs from different Mastodon media formats
        - Test extraction of image metadata (dimensions, file type, etc.)
        - Test handling of malformed or incomplete media attachment data
        - Test processing of different image formats supported by Mastodon
        - Create comprehensive test fixtures with various Mastodon media scenarios
        - Test edge cases like empty media arrays or null values
      - _Requirements: 5.6_
    
    - [x] 10.3.4 Implement Mastodon media updates
      - Add Mastodon media update API integration (/api/v1/media/{id})
      - Handle Mastodon-specific media update request format
      - Add error handling for Mastodon API responses
      - **Testing Requirements:**
        - Mock Mastodon /api/v1/media/{id} PUT endpoint
        - Test successful media description updates with valid media IDs
        - Test media update failures with invalid/non-existent media IDs
        - Test media update request format and payload structure
        - Test handling of Mastodon API error responses (400, 401, 403, 404, 500)
        - Test media updates with different caption lengths and formats
        - Test media updates with special characters and Unicode
        - Test concurrent media updates and rate limiting
        - Test media update retry logic on temporary failures
        - Test media update verification (confirm description was actually updated)
        - Create integration tests with mock Mastodon server responses
      - _Requirements: 5.7_

  - [x] 10.4 Update ActivityPub client for multi-platform support
    - Refactor ActivityPubClient to use platform adapters
    - Update method signatures to be platform-agnostic
    - Add platform-specific error handling and retry logic
    - Maintain existing Pixelfed functionality unchanged
    - **Testing Requirements:**
      - Test ActivityPubClient refactoring maintains existing Pixelfed functionality
      - Test ActivityPubClient works correctly with both platform adapters
      - Test platform-agnostic method signatures work with both platforms
      - Test platform-specific error handling for different error scenarios
      - Test retry logic works correctly for both Pixelfed and Mastodon
      - Mock both platform adapters to test client behavior
      - Test client initialization with different platform configurations
      - Test client method delegation to appropriate platform adapter
      - Test error propagation from platform adapters to client
      - Add regression tests to ensure no existing functionality is broken
      - Test client cleanup and resource management for both platforms
    - _Requirements: 5.8, 5.10_

  - [x] 10.5 Update rate limiting for multiple platforms
    - Add Mastodon-specific rate limiting configuration
    - Update rate limiter to handle different platform rate limit headers
    - Add platform-specific endpoint rate limiting rules
    - **Testing Requirements:**
      - Test rate limiting configuration for both Pixelfed and Mastodon
      - Test parsing of Mastodon rate limit headers (X-RateLimit-*)
      - Test parsing of Pixelfed rate limit headers (existing format)
      - Test platform-specific endpoint rate limiting rules
      - Test rate limit enforcement and backoff behavior
      - Test rate limit reset and window handling
      - Mock HTTP responses with different rate limit headers
      - Test rate limiter behavior when limits are exceeded
      - Test rate limiter recovery after rate limit windows reset
      - Test concurrent request handling with rate limiting
      - Test rate limiting statistics and reporting
      - Add integration tests with simulated rate limit scenarios
    - _Requirements: 5.8_

  - [x] 10.6 Create example configuration files
    - Create .env.example.mastodon with Mastodon configuration example
    - Create .env.example.pixelfed with Pixelfed configuration example
    - Update main .env.example to show both platform options
    - Add configuration documentation in README
    - **Testing Requirements:**
      - Test that .env.example.mastodon contains all required Mastodon variables
      - Test that .env.example.pixelfed contains all required Pixelfed variables
      - Test that example configurations are syntactically valid
      - Test that example configurations can be loaded by the application
      - Validate that all example values are properly formatted and realistic
      - Test that documentation examples match actual configuration requirements
      - Test configuration file parsing with example files
      - Verify that example configurations don't contain real credentials
      - Test that missing optional variables have appropriate defaults
      - Add automated validation of example configuration completeness
    - _Requirements: 5.9_

  - [x] 10.7 Add comprehensive testing for multi-platform support
    - [x] 10.7.1 Add unit tests for platform adapters
      - Test PixelfedPlatform adapter maintains existing functionality
      - Test MastodonPlatform adapter handles Mastodon API correctly
      - Test platform detection and adapter factory
      - _Requirements: 5.2, 5.3_
    
    - [x] 10.7.2 Add integration tests for Mastodon support
      - Mock Mastodon API endpoints for testing
      - Test complete workflow with Mastodon configuration
      - Test error handling for Mastodon-specific scenarios
      - _Requirements: 5.4, 5.5, 5.6, 5.7_
    
    - [x] 10.7.3 Add configuration validation tests
      - Test configuration validation for both platforms
      - Test backward compatibility with existing Pixelfed configs
      - Test error messages for invalid configurations
      - _Requirements: 5.1, 5.9_

  - [x] 10.8 Update documentation and deployment
    - Update README with multi-platform setup instructions
    - Add Mastodon OAuth2 app creation guide
    - Update deployment documentation for platform selection
    - Add troubleshooting guide for platform-specific issues
    - **Testing Requirements:**
      - Test that README setup instructions are accurate and complete
      - Validate that Mastodon OAuth2 app creation steps work with real Mastodon instances
      - Test deployment documentation with both platform configurations
      - Verify that troubleshooting guide covers common error scenarios
      - Test documentation examples and code snippets for accuracy
      - Validate that all configuration variables mentioned in docs are implemented
      - Test that setup instructions work for new users from scratch
      - Verify that migration instructions work for existing Pixelfed users
      - Test documentation links and references are valid
      - Add automated documentation testing where possible (link checking, example validation)
    - _Requirements: 5.9_