# Manual Test Instructions for Caption Submission Fix

## What We Fixed
The issue was that when you approved a caption in the review interface, it only updated the database but didn't actually post the caption to your Pixelfed platform. We've now added code to post the approved caption to the platform.

## How to Test

### Step 1: Check Available Images
You currently have these images available for testing:
- **4 pending images** (IDs: 1, 6, 7, 8) - ready for review
- **1 approved image** (ID: 9) - was approved before the fix

### Step 2: Test the Fix
1. **Go to the review page**: https://vedfolnir.org/review/
2. **Select any pending image** (you should see 4 available)
3. **Review and approve the caption**:
   - Edit the caption if needed
   - Click "Submit Review" or "Approve"
4. **Watch for the redirect** - you should be redirected back to the review list

### Step 3: Check the Logs
After submitting a caption, check the logs to see if the platform posting worked:

```bash
tail -20 logs/webapp.log
```

Look for these log messages:
- ✅ **Success**: `"Successfully posted caption for image X"`
- ✅ **Success**: `"update_media_caption"`
- ⚠️ **Warning**: `"Failed to post caption for image X, marked as approved"`
- ❌ **Error**: `"Error posting caption for image X"`

### Step 4: Verify on Platform
1. **Find the original post** on your Pixelfed account (https://pixey.org/p/iolaire/...)
2. **Check if the alt text was added** to the image
3. **Compare with the caption** you approved

## Expected Behavior

### Before the Fix:
- Caption approved → Database updated → Status: APPROVED
- **No posting to platform**

### After the Fix:
- Caption approved → Database updated → **Platform API called** → Status: POSTED (if successful) or APPROVED (if failed)

## Troubleshooting

### If No Images Show for Review:
```bash
# Generate new captions
python main.py --users admin
```

### If Platform Posting Fails:
Check these common issues:
1. **Platform credentials** - Make sure your Pixelfed connection is active
2. **API permissions** - Verify your API token has media update permissions
3. **Network connectivity** - Ensure the server can reach pixey.org

### Check Image Status:
```bash
python scripts/debug/check_review_images.py
```

## What to Look For

### Success Indicators:
- Log message: "Successfully posted caption for image X"
- Image status changes to "POSTED" in database
- Alt text appears on the original Pixelfed post

### Failure Indicators:
- Log message: "Failed to post caption" or "Error posting caption"
- Image status remains "APPROVED" 
- No alt text on the original post

## Database Status Meanings:
- **PENDING**: Caption generated, waiting for human review
- **APPROVED**: Caption approved by human, but posting failed/not attempted
- **POSTED**: Caption successfully posted to platform
- **REJECTED**: Caption rejected by human reviewer

The fix ensures that approved captions are automatically posted to the platform, changing the status from PENDING → POSTED (or APPROVED if posting fails).