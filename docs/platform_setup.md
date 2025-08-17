# Platform Setup Guide

This guide provides detailed instructions for setting up platform connections with the Vedfolnir's platform-aware database system.

## Overview

The Vedfolnir now supports managing multiple ActivityPub platform connections through a web-based interface. Each user can manage their own platform connections independently, with secure credential storage and complete data isolation between platforms.

## Prerequisites

- Vedfolnir installed and running
- Admin user account created
- Access to one or more ActivityPub platforms (Pixelfed or Mastodon)

## Web Interface Setup

### Accessing Platform Management

1. **Start the web application:**
   ```bash
   # For testing/development (non-blocking)
   python web_app.py & sleep 10
   
   # For production (blocking)
   python web_app.py
   ```

2. **Open your browser and navigate to:** `http://localhost:5000`

3. **Log in with your credentials**

4. **Navigate to Platform Management:**
   - Click "Platforms" in the navigation menu
   - Select "Manage Platforms"

## Pixelfed Platform Setup

### Step 1: Create Pixelfed Application

1. **Log in to your Pixelfed instance**

2. **Navigate to Settings → Applications:**
   - URL format: `https://your-pixelfed-instance.com/settings/applications`
   - Example: `https://pixelfed.social/settings/applications`

3. **Create a new application:**
   - Click "Create New Application" or similar button
   - **Application Name:** `Vedfolnir` (or your preferred name)
   - **Application Description:** (optional) "Accessibility bot for generating alt text"
   - **Scopes:** Select both `read` and `write`
     - `read`: Required to fetch user posts and media information
     - `write`: Required to update media descriptions with alt text
   - **Redirect URI:** Leave default or use `urn:ietf:wg:oauth:2.0:oob`

4. **Submit the application**

5. **Copy the Access Token:**
   - After creation, you'll see your application details
   - Copy the "Access Token" - this is what you'll need for the Vedfolnir
   - Keep this token secure and private

### Step 2: Add Pixelfed Platform in Vedfolnir

1. **In the Vedfolnir web interface, click "Add Platform"**

2. **Fill in the platform connection form:**
   - **Connection Name:** A friendly name for this connection (e.g., "My Pixelfed Account", "Personal Pixelfed")
   - **Platform Type:** Select "Pixelfed" from the dropdown
   - **Instance URL:** The full URL of your Pixelfed instance (e.g., `https://pixelfed.social`)
   - **Username:** Your Pixelfed username (optional, for display purposes)
   - **Access Token:** Paste the access token from Step 1

3. **Test the connection:**
   - Check the "Test connection before saving" checkbox (recommended)
   - The system will verify that it can connect to your Pixelfed instance

4. **Save the platform connection**

### Step 3: Verify Pixelfed Setup

1. **Check the platform list:**
   - Your new Pixelfed connection should appear in the platform list
   - It should show as "Active" with a green status indicator

2. **Test processing:**
   ```bash
   python main.py --users your_pixelfed_username
   ```

3. **Check the web interface:**
   - Navigate to the main dashboard
   - You should see the current platform indicator showing your Pixelfed instance
   - Any processed images should appear for review

## Mastodon Platform Setup

### Step 1: Create Mastodon Application

1. **Log in to your Mastodon instance**

2. **Navigate to Preferences → Development:**
   - URL format: `https://your-mastodon-instance.com/settings/applications`
   - Example: `https://mastodon.social/settings/applications`

3. **Click "New Application"**

4. **Fill in the application details:**
   - **Application name:** `Vedfolnir` (or your preferred name)
   - **Application website:** (optional) Your website or the bot's repository URL
   - **Redirect URI:** `urn:ietf:wg:oauth:2.0:oob` (for command-line applications)
   - **Scopes:** Check both `read` and `write`
     - `read`: Required to fetch user posts and media information
     - `write`: Required to update media descriptions with alt text

5. **Click "Submit"**

6. **Copy the application credentials:**
   After creation, you'll see three important pieces of information:
   - **Client key** (also called Client ID)
   - **Client secret**
   - **Your access token**
   
   Copy all three - you'll need them for the Vedfolnir configuration.

### Step 2: Add Mastodon Platform in Vedfolnir

1. **In the Vedfolnir web interface, click "Add Platform"**

2. **Fill in the platform connection form:**
   - **Connection Name:** A friendly name for this connection (e.g., "My Mastodon Account", "Work Mastodon")
   - **Platform Type:** Select "Mastodon" from the dropdown
   - **Instance URL:** The full URL of your Mastodon instance (e.g., `https://mastodon.social`)
   - **Username:** Your Mastodon username (optional, for display purposes)
   - **Access Token:** Paste the access token from Step 1
   - **Client Key:** Paste the client key from Step 1
   - **Client Secret:** Paste the client secret from Step 1

3. **Test the connection:**
   - Check the "Test connection before saving" checkbox (recommended)
   - The system will verify that it can connect to your Mastodon instance

4. **Save the platform connection**

### Step 3: Verify Mastodon Setup

1. **Check the platform list:**
   - Your new Mastodon connection should appear in the platform list
   - It should show as "Active" with a green status indicator

2. **Test processing:**
   ```bash
   python main.py --users your_mastodon_username
   ```

3. **Check the web interface:**
   - Navigate to the main dashboard
   - You should see the current platform indicator showing your Mastodon instance
   - Any processed images should appear for review

## Managing Multiple Platforms

### Adding Multiple Connections

You can add multiple platform connections of the same or different types:

1. **Multiple instances of the same platform:**
   - Add separate connections for different Pixelfed or Mastodon instances
   - Each connection is independent and secure

2. **Mixed platform types:**
   - Add both Pixelfed and Mastodon connections
   - Switch between them as needed

### Platform Switching

1. **Using the navigation dropdown:**
   - Click the "Platforms" dropdown in the navigation bar
   - Select the platform you want to switch to
   - The interface will update to show data from the selected platform

2. **Setting a default platform:**
   - In Platform Management, click "Edit" on a platform
   - Check "Set as default platform"
   - This platform will be selected automatically when you log in

### Data Isolation

- **Complete separation:** Each platform's data is completely separate
- **No cross-contamination:** Posts from one platform never appear when viewing another
- **Secure switching:** Switching platforms immediately updates the context
- **User-specific:** Each user sees only their own platform connections

## Security Considerations

### Credential Security

- **Encryption:** All platform credentials are encrypted using Fernet encryption
- **Secure storage:** Credentials are stored in the database, not in configuration files
- **Access control:** Users can only access their own platform connections
- **No plaintext:** Credentials are never stored or transmitted in plaintext

### Best Practices

1. **Use strong, unique access tokens:**
   - Generate new tokens specifically for the Vedfolnir
   - Don't reuse tokens from other applications

2. **Regular token rotation:**
   - Periodically regenerate your platform access tokens
   - Update the connections in the Vedfolnir interface

3. **Monitor access:**
   - Check your platform's application access logs regularly
   - Revoke access if you notice any suspicious activity

4. **Secure your Vedfolnir instance:**
   - Use strong passwords for user accounts
   - Keep the application updated
   - Use HTTPS in production deployments

## Troubleshooting

### Common Issues

#### Connection Test Fails

**Problem:** "Connection test failed" when adding a platform

**Solutions:**
1. **Verify credentials:**
   - Double-check that all credentials are copied correctly
   - Ensure there are no extra spaces or characters

2. **Check scopes:**
   - Verify that your application has both `read` and `write` scopes
   - Some platforms require explicit approval for write access

3. **Instance accessibility:**
   - Ensure the instance URL is correct and accessible
   - Test the URL in your browser

4. **Token validity:**
   - Verify that the access token hasn't expired
   - Some platforms have token expiration policies

#### Platform Shows as Inactive

**Problem:** Platform connection shows as "Inactive" in the list

**Solutions:**
1. **Test the connection:**
   - Click "Edit" on the platform
   - Use the "Test Connection" feature
   - Fix any reported issues

2. **Update credentials:**
   - Regenerate tokens on the platform
   - Update the connection with new credentials

3. **Check platform status:**
   - Verify that the platform instance is online and accessible
   - Check for any platform-wide issues or maintenance

#### Processing Fails

**Problem:** `python main.py --users username` fails with authentication errors

**Solutions:**
1. **Verify platform selection:**
   - Ensure you're using the correct username for the selected platform
   - Check that the platform is set as active

2. **Check user permissions:**
   - Verify that the user account has permission to access the posts
   - Ensure the posts are public or accessible to your application

3. **Review logs:**
   - Check `logs/vedfolnir.log` for detailed error messages
   - Look for specific authentication or authorization errors

### Platform-Specific Issues

#### Pixelfed Issues

- **API compatibility:** Ensure your Pixelfed instance supports the required API endpoints
- **Version compatibility:** Some older Pixelfed versions may have limited API support
- **Instance configuration:** Some instances may have restricted API access

#### Mastodon Issues

- **Application approval:** Some Mastodon instances require manual approval of applications
- **Rate limiting:** Mastodon has strict rate limits; adjust processing speed if needed
- **Federation issues:** Some federated instances may have connectivity issues

### Getting Help

If you continue to experience issues:

1. **Check the logs:** Look in `logs/vedfolnir.log` for detailed error messages
2. **Test manually:** Try accessing the platform's API directly to isolate issues
3. **Verify platform status:** Check if the platform instance is experiencing issues
4. **Review documentation:** Check the platform's API documentation for any changes
5. **Seek support:** Create an issue with detailed error messages and configuration details

## Advanced Configuration

### Custom Platform Settings

For advanced users, you can customize platform-specific settings:

1. **Rate limiting:** Adjust per-platform rate limits in the database
2. **Timeout settings:** Configure connection timeouts for specific platforms
3. **Retry policies:** Set custom retry behavior for different platforms

### Bulk Platform Management

For administrators managing multiple users:

1. **Platform templates:** Create template configurations for common platforms
2. **Bulk import:** Import platform connections from configuration files
3. **User management:** Assign platform connections to specific users

### Integration with External Systems

1. **API access:** Use the platform management API for external integrations
2. **Monitoring:** Set up monitoring for platform connection health
3. **Automation:** Automate platform connection management through scripts

This completes the platform setup guide. Users should now be able to successfully configure and manage their ActivityPub platform connections through the Vedfolnir's web interface.