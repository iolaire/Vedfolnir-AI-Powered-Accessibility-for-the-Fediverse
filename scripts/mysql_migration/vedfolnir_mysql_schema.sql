[2025-08-20T14:31:18.384956] INFO root - DB_POOL_SIZE from environment after load_dotenv: 50 (taskName=None)
-- Vedfolnir MySQL Database Schema
-- Generated for MySQL with utf8mb4 charset
-- Database: database_user_1d7b0d0696a20
-- Authentication: Unix socket

-- Set charset and collation
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
SET CHARACTER SET utf8mb4;


CREATE TABLE users (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	username VARCHAR(64) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	password_hash VARCHAR(256) NOT NULL, 
	`role` ENUM('ADMIN','MODERATOR','REVIEWER','VIEWER'), 
	is_active BOOL, 
	created_at DATETIME, 
	last_login DATETIME, 
	email_verified BOOL, 
	email_verification_token VARCHAR(255), 
	email_verification_sent_at DATETIME, 
	first_name VARCHAR(100), 
	last_name VARCHAR(100), 
	password_reset_token VARCHAR(255), 
	password_reset_sent_at DATETIME, 
	password_reset_used BOOL, 
	data_processing_consent BOOL, 
	data_processing_consent_date DATETIME, 
	account_locked BOOL, 
	failed_login_attempts INTEGER, 
	last_failed_login DATETIME, 
	PRIMARY KEY (id)
)CHARSET=utf8mb4 ENGINE=InnoDB COLLATE utf8mb4_unicode_ci

;

CREATE UNIQUE INDEX ix_users_username ON users (username);

CREATE UNIQUE INDEX ix_users_email ON users (email);


CREATE TABLE user_audit_log (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER, 
	action VARCHAR(100) NOT NULL, 
	details TEXT, 
	ip_address VARCHAR(45), 
	user_agent TEXT, 
	created_at DATETIME, 
	admin_user_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(admin_user_id) REFERENCES users (id)
)CHARSET=utf8mb4 ENGINE=InnoDB COLLATE utf8mb4_unicode_ci

;


CREATE TABLE gdpr_audit_log (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER, 
	action_type VARCHAR(50) NOT NULL, 
	gdpr_article VARCHAR(20), 
	action_details TEXT, 
	request_data TEXT, 
	response_data TEXT, 
	status VARCHAR(20), 
	ip_address VARCHAR(45), 
	user_agent TEXT, 
	created_at DATETIME, 
	completed_at DATETIME, 
	admin_user_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(admin_user_id) REFERENCES users (id)
)CHARSET=utf8mb4 ENGINE=InnoDB COLLATE utf8mb4_unicode_ci

;


CREATE TABLE platform_connections (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	platform_type VARCHAR(50) NOT NULL, 
	instance_url VARCHAR(500) NOT NULL, 
	username VARCHAR(200), 
	access_token TEXT NOT NULL, 
	client_key TEXT, 
	client_secret TEXT, 
	is_active BOOL, 
	is_default BOOL, 
	created_at DATETIME, 
	updated_at DATETIME, 
	last_used DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_platform_name UNIQUE (user_id, name), 
	CONSTRAINT uq_user_instance_username UNIQUE (user_id, instance_url, username), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE INDEX ix_platform_user_active ON platform_connections (user_id, is_active);

CREATE INDEX ix_platform_type_active ON platform_connections (platform_type, is_active);

CREATE INDEX ix_platform_instance_type ON platform_connections (instance_url, platform_type);


CREATE TABLE posts (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	post_id VARCHAR(500) NOT NULL, 
	user_id VARCHAR(200) NOT NULL, 
	post_url VARCHAR(500) NOT NULL, 
	post_content TEXT, 
	created_at DATETIME, 
	updated_at DATETIME, 
	platform_connection_id INTEGER, 
	platform_type VARCHAR(50), 
	instance_url VARCHAR(500), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_post_platform UNIQUE (post_id, platform_connection_id), 
	FOREIGN KEY(platform_connection_id) REFERENCES platform_connections (id)
)

;

CREATE INDEX ix_posts_post_id ON posts (post_id);


CREATE TABLE processing_runs (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(200) NOT NULL, 
	batch_id VARCHAR(200), 
	started_at DATETIME, 
	completed_at DATETIME, 
	posts_processed INTEGER, 
	images_processed INTEGER, 
	captions_generated INTEGER, 
	errors_count INTEGER, 
	status VARCHAR(50), 
	platform_connection_id INTEGER, 
	platform_type VARCHAR(50), 
	instance_url VARCHAR(500), 
	retry_attempts INTEGER, 
	retry_successes INTEGER, 
	retry_failures INTEGER, 
	retry_total_time INTEGER, 
	retry_stats_json TEXT, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_batch_platform UNIQUE (batch_id, platform_connection_id), 
	FOREIGN KEY(platform_connection_id) REFERENCES platform_connections (id)
)

;


CREATE TABLE user_sessions (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	session_id VARCHAR(255) NOT NULL, 
	user_id INTEGER NOT NULL, 
	active_platform_id INTEGER, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	last_activity DATETIME NOT NULL, 
	expires_at DATETIME NOT NULL, 
	is_active BOOL NOT NULL, 
	session_fingerprint TEXT, 
	user_agent TEXT, 
	ip_address VARCHAR(45), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(active_platform_id) REFERENCES platform_connections (id)
)CHARSET=utf8mb4 ENGINE=InnoDB COLLATE utf8mb4_unicode_ci

;

CREATE UNIQUE INDEX ix_user_sessions_session_id ON user_sessions (session_id);

CREATE INDEX ix_user_sessions_is_active ON user_sessions (is_active);

CREATE INDEX ix_user_sessions_updated_at ON user_sessions (updated_at);

CREATE INDEX ix_user_sessions_last_activity ON user_sessions (last_activity);

CREATE INDEX ix_user_sessions_expires_at ON user_sessions (expires_at);

CREATE INDEX ix_user_sessions_user_id ON user_sessions (user_id);


CREATE TABLE caption_generation_tasks (
	id VARCHAR(36) NOT NULL, 
	user_id INTEGER NOT NULL, 
	platform_connection_id INTEGER NOT NULL, 
	status ENUM('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED'), 
	settings_json TEXT, 
	created_at DATETIME, 
	started_at DATETIME, 
	completed_at DATETIME, 
	error_message TEXT, 
	results_json TEXT, 
	progress_percent INTEGER, 
	current_step VARCHAR(200), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(platform_connection_id) REFERENCES platform_connections (id)
)

;


CREATE TABLE caption_generation_user_settings (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	platform_connection_id INTEGER NOT NULL, 
	max_posts_per_run INTEGER, 
	max_caption_length INTEGER, 
	optimal_min_length INTEGER, 
	optimal_max_length INTEGER, 
	reprocess_existing BOOL, 
	processing_delay FLOAT, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_platform_settings UNIQUE (user_id, platform_connection_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(platform_connection_id) REFERENCES platform_connections (id)
)

;


CREATE TABLE images (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	post_id INTEGER NOT NULL, 
	image_url VARCHAR(1000) NOT NULL, 
	local_path VARCHAR(500) NOT NULL, 
	original_filename VARCHAR(200), 
	media_type VARCHAR(100), 
	image_post_id VARCHAR(100), 
	attachment_index INTEGER NOT NULL, 
	platform_connection_id INTEGER, 
	platform_type VARCHAR(50), 
	instance_url VARCHAR(500), 
	original_caption TEXT, 
	generated_caption TEXT, 
	reviewed_caption TEXT, 
	final_caption TEXT, 
	image_category VARCHAR(50), 
	prompt_used TEXT, 
	status ENUM('PENDING','REVIEWED','APPROVED','REJECTED','POSTED','ERROR'), 
	created_at DATETIME, 
	updated_at DATETIME, 
	reviewed_at DATETIME, 
	posted_at DATETIME, 
	original_post_date DATETIME, 
	reviewer_notes TEXT, 
	processing_error TEXT, 
	caption_quality_score INTEGER, 
	needs_special_review BOOL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_image_platform UNIQUE (image_post_id, platform_connection_id), 
	FOREIGN KEY(post_id) REFERENCES posts (id), 
	FOREIGN KEY(platform_connection_id) REFERENCES platform_connections (id)
)

;

-- Indexes and constraints are automatically created by the above statements
-- Foreign key constraints are included in the table definitions

-- Migration complete!
