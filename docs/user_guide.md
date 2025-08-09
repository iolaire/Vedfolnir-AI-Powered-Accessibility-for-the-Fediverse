# User Guide: Vedfolnir Web Interface

This guide provides comprehensive instructions for using the Vedfolnir's web interface to manage platform connections, review captions, and monitor processing activities.

## Getting Started

### Accessing the Web Interface

1. **Start the web application:**
   ```bash
   python web_app.py
   ```

2. **Open your browser and navigate to:** `http://localhost:5000`

3. **Log in with your credentials:**
   - Username: Your assigned username
   - Password: Your assigned password

### First-Time Setup

If you're a new user or this is your first time using the platform-aware system:

1. **Add your first platform connection** (see Platform Management section)
2. **Test the connection** to ensure it works
3. **Set it as your default platform**
4. **Run your first processing job**

## Dashboard Overview

The main dashboard provides an overview of your Vedfolnir activities:

### Current Platform Indicator

- **Platform Name:** Shows your currently selected platform
- **Platform Type:** Displays whether it's Pixelfed or Mastodon
- **Instance URL:** Shows the domain of your platform instance
- **Statistics:** Quick stats for the current platform

### Quick Stats

- **Total Posts:** Number of posts processed from your platforms
- **Images Processed:** Total images that have been analyzed
- **Pending Review:** Images waiting for your review
- **Approved Captions:** Captions you've approved for posting

### Recent Activity

- **Latest Processing Runs:** Recent bot executions
- **Recent Reviews:** Your recent caption review activities
- **Platform Switches:** History of platform changes

## Platform Management

### Viewing Your Platforms

1. **Navigate to Platform Management:**
   - Click "Platforms" in the navigation menu
   - Select "Manage Platforms"

2. **Platform List View:**
   - **Connection Cards:** Each platform shows as a card with key information
   - **Status Indicators:** Green (active) or red (inactive) status
   - **Default Badge:** Shows which platform is your default
   - **Last Used:** When you last used each platform

### Adding a New Platform

1. **Click "Add Platform" button**

2. **Fill in the platform details:**
   - **Connection Name:** A friendly name (e.g., "My Personal Mastodon")
   - **Platform Type:** Select Pixelfed or Mastodon
   - **Instance URL:** Full URL (e.g., `https://mastodon.social`)
   - **Username:** Your username on that platform
   - **Access Token:** Your API access token
   - **Client Key/Secret:** Required for Mastodon only

3. **Test the connection:**
   - Check "Test connection before saving"
   - The system will verify your credentials

4. **Save the platform**

### Editing Platform Connections

1. **Click "Edit" on any platform card**

2. **Update the information:**
   - Modify any field except the platform type
   - Update credentials if they've changed
   - Change the connection name

3. **Test the updated connection**

4. **Save changes**

### Managing Default Platform

1. **Set Default Platform:**
   - Click "Edit" on the desired platform
   - Check "Set as default platform"
   - Save changes

2. **Default Platform Benefits:**
   - Automatically selected when you log in
   - Used for command-line processing if no platform specified
   - Shown first in platform lists

### Switching Between Platforms

#### Method 1: Navigation Dropdown

1. **Click the "Platforms" dropdown in the navigation bar**
2. **Select the platform you want to switch to**
3. **The interface updates immediately**

#### Method 2: Platform Management Page

1. **Go to Platform Management**
2. **Click "Switch" on the desired platform**
3. **Confirm the switch**

### Platform Connection Testing

1. **Test Individual Connections:**
   - Click "Test Connection" on any platform
   - View the test results
   - Fix any issues reported

2. **Bulk Testing:**
   - Use "Test All Connections" to check all platforms
   - Review results for each platform
   - Address any failed connections

## Caption Review Interface

### Accessing Caption Review

1. **Navigate to the Review page:**
   - Click "Review" in the main navigation
   - Or click "Review Captions" from the dashboard

2. **Platform Context:**
   - Reviews show only images from your currently selected platform
   - Switch platforms to review different platform's images

### Review Interface Layout

#### Image Display

- **Image Preview:** Large preview of the image
- **Original Post Context:** Link to the original post
- **Platform Information:** Shows which platform and instance
- **Post Metadata:** Date, user, and post details

#### Caption Information

- **Generated Caption:** AI-generated description
- **Caption Quality Score:** Automatic quality assessment
- **Generation Method:** Which AI model was used
- **Processing Date:** When the caption was generated

#### Review Actions

- **Approve:** Accept the caption as-is
- **Edit & Approve:** Modify the caption before approval
- **Reject:** Reject the caption (won't be posted)
- **Skip:** Skip for now (can review later)

### Reviewing Captions

#### Approving Captions

1. **Review the generated caption**
2. **Check that it accurately describes the image**
3. **Click "Approve" if satisfied**
4. **The caption will be queued for posting**

#### Editing Captions

1. **Click in the caption text area**
2. **Make your edits:**
   - Fix any inaccuracies
   - Improve clarity or detail
   - Ensure appropriate tone
3. **Click "Edit & Approve"**
4. **Your edited version will be used**

#### Rejecting Captions

1. **Click "Reject" if the caption is inappropriate or inaccurate**
2. **Optionally provide a reason**
3. **The image won't get alt text added**

### Batch Review

#### Accessing Batch Review

1. **Click "Batch Review" from the Review menu**
2. **Select review criteria:**
   - Platform filter
   - Date range
   - Quality score range
   - Processing status

#### Batch Operations

1. **Select Multiple Images:**
   - Use checkboxes to select images
   - Use "Select All" for all visible images

2. **Batch Actions:**
   - **Approve All Selected:** Approve multiple captions at once
   - **Reject All Selected:** Reject multiple captions
   - **Export Selected:** Export caption data

### Review Filters and Search

#### Filter Options

- **Platform:** Filter by specific platform connection
- **Status:** Pending, approved, rejected, posted
- **Date Range:** Filter by processing date
- **Quality Score:** Filter by AI-assessed quality
- **User:** Filter by original post author

#### Search Functionality

- **Text Search:** Search within captions or post content
- **Tag Search:** Search by hashtags or mentions
- **Image Search:** Search by image characteristics

## Processing Management

### Running Processing Jobs

#### Command Line Processing

1. **Basic processing:**
   ```bash
   python main.py --users your_username
   ```

2. **Multi-user processing:**
   ```bash
   python main.py --users user1 user2 user3
   ```

3. **Processing with specific platform:**
   - The bot uses your currently selected platform
   - Switch platforms in the web interface before running

#### Monitoring Processing

1. **Processing Status:**
   - View current processing jobs in the dashboard
   - Monitor progress and completion status

2. **Processing History:**
   - View past processing runs
   - See statistics and results
   - Filter by platform or date range

### Processing Configuration

#### Per-Platform Settings

1. **Access Platform Settings:**
   - Go to Platform Management
   - Click "Settings" on a platform

2. **Configure Processing Options:**
   - **Max Posts Per Run:** Limit posts processed
   - **Processing Delay:** Delay between API calls
   - **Caption Length Limits:** Min/max caption length
   - **Quality Thresholds:** Minimum quality scores

#### Global Processing Settings

Access through the Settings menu:

- **AI Model Configuration:** Choose Ollama model
- **Image Processing:** Size limits, format preferences
- **Rate Limiting:** API call frequency limits
- **Logging:** Log level and retention settings

## Statistics and Analytics

### Platform Statistics

#### Accessing Platform Stats

1. **Dashboard Overview:** Quick stats on the main page
2. **Detailed Statistics:** Click "Statistics" in the navigation
3. **Platform Comparison:** Compare stats across platforms

#### Available Metrics

- **Processing Volume:**
  - Total posts processed
  - Images analyzed
  - Captions generated

- **Review Activity:**
  - Captions approved/rejected
  - Review completion rate
  - Average review time

- **Quality Metrics:**
  - Average caption quality scores
  - Improvement over time
  - User satisfaction ratings

### Historical Analysis

#### Trends and Patterns

- **Processing Trends:** Volume over time
- **Quality Improvements:** Caption quality evolution
- **Platform Comparison:** Performance across platforms
- **User Activity:** Review and approval patterns

#### Export and Reporting

1. **Export Data:**
   - CSV export of statistics
   - Filtered data exports
   - Custom date ranges

2. **Generate Reports:**
   - Monthly processing summaries
   - Platform performance reports
   - Quality assessment reports

## User Account Management

### Profile Settings

#### Accessing Profile

1. **Click your username in the navigation**
2. **Select "Profile" from the dropdown**

#### Profile Information

- **Username:** Your login username
- **Email:** Contact email address
- **Role:** Your assigned role (Admin, Moderator, etc.)
- **Account Status:** Active/inactive status

#### Changing Password

1. **Go to Profile Settings**
2. **Click "Change Password"**
3. **Enter current password**
4. **Enter new password (twice)**
5. **Save changes**

### Notification Preferences

#### Email Notifications

Configure when you receive email notifications:

- **Processing Completion:** When processing jobs finish
- **Review Reminders:** Reminders to review pending captions
- **Platform Issues:** When platform connections fail
- **System Updates:** Important system announcements

#### In-App Notifications

- **Browser Notifications:** Enable/disable browser notifications
- **Dashboard Alerts:** Show alerts on the dashboard
- **Review Notifications:** Notifications for new items to review

## Advanced Features

### API Access

#### Personal API Tokens

1. **Generate API Token:**
   - Go to Profile Settings
   - Click "Generate API Token"
   - Copy and secure your token

2. **Using API Tokens:**
   ```bash
   # Example API call
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        http://localhost:5000/api/platforms
   ```

#### API Endpoints

- **Platform Management:** CRUD operations for platforms
- **Caption Review:** Programmatic caption review
- **Statistics:** Access to statistics data
- **Processing:** Trigger and monitor processing jobs

### Automation and Webhooks

#### Scheduled Processing

1. **Set up cron jobs:**
   ```bash
   # Process every hour
   0 * * * * cd /path/to/vedfolnir && python main.py --users username
   ```

2. **Platform-specific scheduling:**
   - Different schedules for different platforms
   - Peak/off-peak processing times

#### Webhook Integration

1. **Configure Webhooks:**
   - Set webhook URLs for processing events
   - Configure authentication for webhooks

2. **Webhook Events:**
   - Processing completion
   - Caption approval
   - Platform connection issues

### Bulk Operations

#### Bulk Caption Management

1. **Mass Approval:**
   - Select multiple captions
   - Apply bulk approval with filters

2. **Bulk Editing:**
   - Find and replace in captions
   - Apply consistent formatting

#### Data Management

1. **Bulk Export:**
   - Export all data for a platform
   - Filtered exports by date or status

2. **Bulk Import:**
   - Import caption data
   - Migrate data between platforms

## Troubleshooting

### Common Issues

#### Can't See My Platform Data

1. **Check Platform Selection:**
   - Verify correct platform is selected
   - Switch to the intended platform

2. **Check Platform Connection:**
   - Test platform connection
   - Update credentials if needed

#### Processing Not Working

1. **Verify Platform Connection:**
   - Test connection in Platform Management
   - Check credentials and permissions

2. **Check Processing Logs:**
   - View logs in the dashboard
   - Look for error messages

#### Web Interface Issues

1. **Clear Browser Cache:**
   - Clear cache and cookies
   - Refresh the page

2. **Check JavaScript:**
   - Enable JavaScript in browser
   - Check browser console for errors

### Getting Help

#### In-App Help

- **Help Tooltips:** Hover over ? icons for help
- **Context Help:** Click "Help" links on each page
- **FAQ Section:** Common questions and answers

#### Support Resources

- **Documentation:** Complete guides in the `docs/` folder
- **Troubleshooting Guide:** `docs/troubleshooting.md`
- **Platform Setup Guide:** `docs/platform_setup.md`

#### Contacting Support

1. **Collect Information:**
   - Screenshot of the issue
   - Error messages from logs
   - Steps to reproduce the problem

2. **Submit Support Request:**
   - Include platform type and version
   - Describe expected vs. actual behavior
   - Attach relevant log excerpts

## Best Practices

### Platform Management

1. **Regular Connection Testing:**
   - Test connections weekly
   - Update credentials promptly when they change

2. **Meaningful Names:**
   - Use descriptive names for platform connections
   - Include instance name and purpose

3. **Security:**
   - Rotate access tokens regularly
   - Use strong, unique passwords
   - Monitor access logs

### Caption Review

1. **Quality Standards:**
   - Ensure captions are accurate and descriptive
   - Use consistent tone and style
   - Consider the target audience

2. **Efficiency:**
   - Use batch review for similar images
   - Set up filters to prioritize important content
   - Review regularly to avoid backlogs

3. **Accessibility:**
   - Focus on essential visual information
   - Avoid redundant information
   - Consider context and purpose

### Processing Management

1. **Scheduling:**
   - Process during off-peak hours
   - Respect platform rate limits
   - Monitor processing performance

2. **Monitoring:**
   - Check processing logs regularly
   - Monitor platform connection health
   - Track processing statistics

This user guide should help you effectively use all features of the Vedfolnir's web interface. For additional help, refer to the other documentation files or contact support.