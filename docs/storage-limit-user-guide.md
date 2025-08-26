# Storage Limit User Guide

This guide explains how storage limits work in Vedfolnir, what to do when you encounter storage limit notifications, and how the system protects against storage overflow.

## Table of Contents

1. [Understanding Storage Limits](#understanding-storage-limits)
2. [Storage Limit Notifications](#storage-limit-notifications)
3. [What to Do When Storage Limits Are Reached](#what-to-do-when-storage-limits-are-reached)
4. [Monitoring Your Storage Usage](#monitoring-your-storage-usage)
5. [Frequently Asked Questions](#frequently-asked-questions)

## Understanding Storage Limits

### What Are Storage Limits?

Vedfolnir automatically monitors the total storage space used by image files to prevent the system from running out of disk space. When storage usage approaches or reaches the configured limit, the system takes protective actions to maintain system stability.

### How Storage Limits Work

- **Automatic Monitoring**: The system continuously monitors total image storage usage
- **Proactive Protection**: Caption generation is automatically blocked when limits are reached
- **User Notifications**: Clear notifications explain when and why caption generation is unavailable
- **Automatic Recovery**: Caption generation resumes automatically when storage space is freed

### Storage Limit Thresholds

The system uses two main thresholds:

1. **Warning Threshold (80%)**: Administrators receive warnings when storage usage exceeds 80% of the limit
2. **Blocking Threshold (100%)**: Caption generation is blocked when the storage limit is reached

## Storage Limit Notifications

### When You'll See Storage Notifications

You'll encounter storage limit notifications in these situations:

- **Caption Generation Page**: A banner appears when storage limits are active
- **Processing Attempts**: Error messages when trying to generate captions during storage limits
- **Dashboard Alerts**: Status indicators showing storage limit status

### Types of Storage Notifications

#### Storage Limit Active Banner

When storage limits are reached, you'll see a prominent notification banner:

```
⚠️ Caption Generation Temporarily Unavailable

Caption generation is currently disabled due to storage limits. 
Our administrators are working to free up space. Please try again later.

The system will automatically resume caption generation when storage space becomes available.
```

#### Form Disabled State

- The caption generation form will be hidden or disabled
- Submit buttons will be inactive
- Clear messaging explains why the feature is unavailable

#### Processing Error Messages

If you attempt to process captions during storage limits:

```
❌ Processing Failed: Storage Limit Reached

Caption generation is currently blocked due to storage limits. 
Please wait for administrators to free up space and try again.
```

### What Storage Notifications Mean

- **Temporary Condition**: Storage limits are typically temporary situations
- **System Protection**: The system is protecting itself from running out of disk space
- **No Data Loss**: Your existing captions and data are safe
- **Automatic Resolution**: The system will resume normal operation when space is available

## What to Do When Storage Limits Are Reached

### Immediate Actions

1. **Don't Panic**: Storage limits are a normal protective measure
2. **Wait for Resolution**: Administrators are automatically notified and will address the issue
3. **Check Back Later**: The system will automatically resume when space is available
4. **Continue Other Activities**: Other system features remain available

### What You Can Do

#### Review Your Existing Captions

- Use the time to review and approve pending captions
- Edit and improve existing captions
- Organize your caption review workflow

#### Plan Future Processing

- Identify which images need captions when the system resumes
- Prioritize important content for processing
- Prepare batch processing lists

#### Contact Administrators (If Needed)

Contact administrators if:
- Storage limits persist for an extended period (more than 24 hours)
- You have urgent caption generation needs
- You notice other system issues

### What NOT to Do

- **Don't repeatedly try to generate captions**: This won't work and may slow down the system
- **Don't delete your own data**: Your personal data doesn't significantly impact system storage
- **Don't worry about data loss**: Storage limits don't affect existing data

## Monitoring Your Storage Usage

### Dashboard Indicators

The system dashboard may show storage-related information:

- **System Status**: Overall system health including storage status
- **Processing Status**: Whether caption generation is currently available
- **Recent Activity**: Information about recent processing activities

### Understanding Storage Status

#### Normal Operation
- Caption generation is available
- No storage-related notifications
- All features function normally

#### Warning State (Admin Visible)
- System approaching storage limits
- Administrators receive warnings
- Users may not see immediate changes

#### Limit Reached
- Caption generation blocked
- Clear user notifications displayed
- Automatic recovery when space is freed

### Checking System Status

You can check if storage limits are affecting the system by:

1. **Visiting the Caption Generation Page**: Look for storage limit banners
2. **Checking the Dashboard**: Look for system status indicators
3. **Attempting to Process**: Try generating captions to see current status

## Frequently Asked Questions

### General Questions

**Q: How long do storage limits typically last?**
A: Storage limits are usually resolved within a few hours to a day, depending on how quickly administrators can free up space or increase storage capacity.

**Q: Will I lose my existing captions during storage limits?**
A: No, storage limits only affect new caption generation. All existing captions and data remain safe and accessible.

**Q: Can I still review and approve captions during storage limits?**
A: Yes, caption review and approval functions continue to work normally during storage limits.

**Q: Why doesn't the system just automatically delete old files?**
A: The system prioritizes data safety and requires administrator oversight for data cleanup to prevent accidental loss of important content.

### Technical Questions

**Q: What counts toward the storage limit?**
A: The storage limit includes all image files downloaded and processed by the system, including original images and any processed versions.

**Q: How often does the system check storage usage?**
A: The system checks storage usage before each caption generation request and periodically in the background.

**Q: Can storage limits affect other users?**
A: Yes, storage limits are system-wide and affect all users equally to protect overall system stability.

**Q: How do I know when storage limits are lifted?**
A: The system automatically removes storage limit notifications when caption generation becomes available again. You can also try accessing the caption generation page to check current status.

### Troubleshooting Questions

**Q: I don't see storage limit notifications but caption generation isn't working. What should I do?**
A: This might indicate a different issue. Check for other error messages, verify your platform connections, and contact administrators if the problem persists.

**Q: The storage limit notification disappeared but I still can't generate captions. Why?**
A: There might be a brief delay as the system updates. Wait a few minutes and refresh the page. If the issue persists, there may be other system issues.

**Q: Can I request priority processing during storage limits?**
A: Storage limits affect all users equally for system protection. However, you can contact administrators about urgent needs, and they may be able to provide guidance or expedite storage cleanup.

### Administrative Questions

**Q: How can I help reduce storage usage?**
A: Individual users typically don't have direct control over system storage, but you can:
- Review and clean up your personal data if the system provides such options
- Avoid unnecessary repeated processing of the same images
- Report any issues that might cause excessive storage use

**Q: Who should I contact about storage limit issues?**
A: Contact your system administrators. They receive automatic notifications about storage limits and are responsible for managing system storage.

**Q: Can storage limits be prevented?**
A: Administrators can monitor storage usage and take proactive measures, but storage limits are an important safety feature that protects the entire system from running out of disk space.

## Best Practices During Storage Limits

### For Regular Users

1. **Be Patient**: Storage limits are temporary and will be resolved
2. **Use the Time Productively**: Review existing captions and plan future work
3. **Stay Informed**: Check for updates from administrators
4. **Report Issues**: Contact administrators if you notice unusual behavior

### For Content Managers

1. **Prioritize Content**: Identify which images need captions most urgently
2. **Batch Planning**: Prepare lists of content for processing when limits are lifted
3. **Quality Focus**: Use the time to improve existing caption quality
4. **Communication**: Keep your team informed about temporary limitations

### For Platform Administrators

1. **Monitor Notifications**: Watch for storage limit notifications
2. **Plan Ahead**: Consider storage needs when planning content campaigns
3. **Coordinate with System Admins**: Communicate about urgent processing needs
4. **Document Impact**: Track how storage limits affect your workflows

## Getting Help

### Self-Service Resources

- **System Status Page**: Check current system status and known issues
- **User Documentation**: Review other user guides for related information
- **FAQ Section**: Check frequently asked questions for common issues

### Contacting Support

When contacting administrators about storage limits:

1. **Provide Context**: Explain what you were trying to do
2. **Include Screenshots**: Show any error messages or notifications
3. **Specify Urgency**: Indicate if you have time-sensitive needs
4. **Be Patient**: Remember that storage limits affect the entire system

### Information to Include

- Current date and time
- What you were trying to do
- Any error messages you received
- Screenshots of notifications or issues
- Your username and platform information

## Conclusion

Storage limits are an important protective feature that ensures system stability and prevents data loss due to insufficient disk space. While they may temporarily interrupt caption generation, they help maintain the overall health and reliability of the Vedfolnir system.

By understanding how storage limits work and what to do when they occur, you can minimize disruption to your workflow and make productive use of the time while administrators resolve storage issues.

Remember that storage limits are temporary, automatic recovery is built into the system, and your existing data remains safe throughout the process.