# Web-Based Caption Generation Documentation

## Overview
This directory contains comprehensive documentation for the web-based caption generation system, an advanced feature that allows users to generate alt text for their social media posts through an intuitive web interface with real-time progress tracking.

## Documentation Structure

### 📖 [User Guide](user-guide.md)
Complete guide for end users covering:
- Getting started with web-based caption generation
- Using the web interface and real-time progress tracking
- Configuring generation settings
- Managing tasks and reviewing results
- Troubleshooting common user issues

### 👨‍💼 [Administrator Guide](admin-guide.md)
Comprehensive guide for system administrators covering:
- Admin dashboard and monitoring features
- System resource monitoring and alerts
- User management and task oversight
- Performance optimization and maintenance
- Error management and recovery procedures

### 🔌 [API Documentation](api-documentation.md)
Technical reference for developers covering:
- REST API endpoints for caption generation
- WebSocket events for real-time updates
- Authentication and authorization
- Error codes and response formats
- SDK examples and integration patterns

### 🚀 [Deployment Guide](deployment-guide.md)
Complete deployment instructions covering:
- System requirements and prerequisites
- Docker and manual deployment options
- WebSocket and background task configuration
- Reverse proxy setup (Nginx/Apache)
- Scaling, monitoring, and security considerations

### 🔧 [Troubleshooting Guide](troubleshooting-guide.md)
Problem-solving resource covering:
- Common issues and their solutions
- Diagnostic commands and tools
- Emergency recovery procedures
- Performance optimization tips
- Support and help resources

## Quick Start

### For Users
1. Read the [User Guide](user-guide.md) to understand the web interface
2. Log in to your Vedfolnir instance
3. Navigate to **Caption Generation** to start generating captions
4. Monitor progress in real-time and review generated captions

### For Administrators
1. Review the [Administrator Guide](admin-guide.md) for system management
2. Access the admin dashboard for monitoring and control
3. Configure system settings and user limits
4. Set up monitoring and alerting for production use

### For Developers
1. Check the [API Documentation](api-documentation.md) for integration details
2. Use the REST API endpoints for programmatic access
3. Implement WebSocket connections for real-time updates
4. Follow the SDK examples for common integration patterns

### For Deployment
1. Follow the [Deployment Guide](deployment-guide.md) for installation
2. Choose between Docker or manual deployment options
3. Configure reverse proxy and SSL/TLS
4. Set up monitoring and backup procedures

## Key Features

### 🌐 Web-Based Interface
- **Intuitive UI**: Easy-to-use web interface for caption generation
- **Real-Time Progress**: Live updates via WebSocket connections
- **Responsive Design**: Works on desktop and mobile devices
- **Accessibility**: Full keyboard navigation and screen reader support

### ⚡ Real-Time Processing
- **Live Progress Updates**: See generation progress without refreshing
- **WebSocket Communication**: Instant notifications and status updates
- **Task Management**: Start, monitor, and cancel tasks in real-time
- **Error Notifications**: Immediate feedback on issues and failures

### 🔧 Advanced Configuration
- **User Settings**: Customizable generation parameters per platform
- **Platform Management**: Support for multiple ActivityPub platforms
- **Admin Controls**: System-wide configuration and monitoring
- **Security Features**: Authentication, authorization, and rate limiting

### 📊 Monitoring and Analytics
- **Admin Dashboard**: Comprehensive system monitoring interface
- **Performance Metrics**: Task completion rates and system health
- **Resource Monitoring**: CPU, memory, and database usage tracking
- **User Activity**: Track usage patterns and system load

### 🔒 Security and Reliability
- **Authentication**: Secure user login and session management
- **Authorization**: Role-based access control (Admin, User, etc.)
- **Rate Limiting**: Prevent abuse and ensure fair resource usage
- **Error Recovery**: Intelligent error handling with retry mechanisms

## System Architecture

### Components
- **Web Application**: Flask-based web interface with WebSocket support
- **Task Queue Manager**: Background task processing and queue management
- **Progress Tracker**: Real-time progress tracking and WebSocket broadcasting
- **Platform Adapters**: Integration with ActivityPub platforms (Mastodon, Pixelfed)
- **AI Service Integration**: Ollama/LLaVA model for caption generation
- **Database Layer**: SQLite with platform-aware data isolation

### Data Flow
1. **User Initiates**: User starts caption generation via web interface
2. **Task Creation**: System creates and queues generation task
3. **Background Processing**: Worker processes task with AI model
4. **Progress Updates**: Real-time progress sent via WebSocket
5. **Review Integration**: Generated captions available for review
6. **Platform Updates**: Approved captions published to social platforms

## Requirements

### System Requirements
- **Python**: 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: 10GB free space minimum
- **CPU**: 2+ cores recommended
- **Network**: Stable internet connection

### Dependencies
- **Ollama**: AI model server with LLaVA model
- **Redis**: Session storage and task queuing (optional but recommended)
- **Nginx**: Reverse proxy for production (recommended)
- **Supervisor**: Process management (recommended)

## Getting Help

### Documentation
- Start with the appropriate guide based on your role (User, Admin, Developer)
- Check the troubleshooting guide for common issues
- Review the API documentation for integration questions

### Support Channels
- **GitHub Issues**: Report bugs and request features
- **Community Forums**: Get help from other users and contributors
- **Documentation**: Comprehensive guides and references

### Contributing
- **Bug Reports**: Use GitHub issues with detailed reproduction steps
- **Feature Requests**: Describe use cases and expected behavior
- **Documentation**: Help improve guides and examples
- **Code Contributions**: Follow contribution guidelines in main repository

## Version Information

### Current Version
- **Web Caption Generation**: v1.0.0
- **API Version**: v1
- **WebSocket Protocol**: socket.io v4.x compatible

### Compatibility
- **Vedfolnir**: v2.0.0 and higher
- **Python**: 3.8, 3.9, 3.10, 3.11
- **Platforms**: Mastodon, Pixelfed (ActivityPub compatible)
- **Browsers**: Modern browsers with WebSocket support

### Changelog
See the main repository changelog for detailed version history and updates.

---

**Note**: This documentation covers the web-based caption generation system specifically. For general Vedfolnir documentation, see the main README.md file in the repository root.