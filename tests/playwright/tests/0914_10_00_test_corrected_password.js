const { chromium } = require('playwright');

(async () => {
  console.log('=== Corrected Password Change Workflow Test ===');
  
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  // Set up console monitoring
  const consoleMessages = [];
  page.on('console', msg => {
    const message = `Console ${msg.type()}: ${msg.text()}`;
    consoleMessages.push(message);
    console.log(message);
  });
  
  try {
    // Login with iolaire
    console.log('Logging in with iolaire...');
    await page.goto('http://127.0.0.1:5000/user-management/login');
    await page.waitForLoadState('networkidle');
    
    await page.fill('#username_or_email', 'iolaire');
    await page.fill('#password', 'g9bDFB9JzgEaVZx');
    await page.click('input[type="submit"]');
    
    // Handle first-time setup redirect
    await page.waitForTimeout(5000);
    let currentUrl = page.url();
    
    if (currentUrl.includes('/first_time_setup')) {
      console.log('Handling first-time setup redirect...');
      await page.goto('http://127.0.0.1:5000/user-management/change-password');
      await page.waitForTimeout(3000);
    } else {
      // Navigate to change password page
      console.log('Navigating to change password page...');
      await page.goto('http://127.0.0.1:5000/user-management/change-password');
      await page.waitForLoadState('networkidle');
    }
    
    // Wait a bit for any JavaScript to initialize
    await page.waitForTimeout(2000);
    
    // Test password change
    console.log('Testing password change workflow...');
    
    await page.fill('#current_password', 'g9bDFB9JzgEaVZx');
    await page.fill('#new_password', 'NewPassword123!');
    await page.fill('#confirm_new_password', 'NewPassword123!');
    
    // Submit the form
    console.log('Submitting password change form...');
    await page.click('input[type="submit"]');
    await page.waitForTimeout(5000);
    
    // Check if we're redirected to login page
    currentUrl = page.url();
    console.log(`Current URL after password change: ${currentUrl}`);
    
    if (currentUrl.includes('login')) {
      console.log('✓ Successfully redirected to login page after password change');
      
      // Look for success notification
      const notificationSelectors = [
        '.unified-notification .notification-message',
        '.alert-success',
        '.notification',
        '[class*="success"]'
      ];
      
      let successNotificationFound = false;
      for (const selector of notificationSelectors) {
        try {
          const elements = await page.locator(selector).count();
          if (elements > 0) {
            const text = await page.locator(selector).first().textContent();
            console.log(`Found notification: ${text}`);
            if (text.toLowerCase().includes('password') && 
                (text.toLowerCase().includes('changed') || text.toLowerCase().includes('success'))) {
              successNotificationFound = true;
              console.log('✓ Password change success notification found');
              break;
            }
          }
        } catch (err) {
          continue;
        }
      }
      
      if (!successNotificationFound) {
        console.log('⚠️  Success notification not found on login page');
      }
      
      // Test login with new password
      console.log('\nTesting login with new password...');
      await page.fill('#username_or_email', 'iolaire');
      await page.fill('#password', 'NewPassword123!');
      await page.click('input[type="submit"]');
      await page.waitForTimeout(3000);
      
      currentUrl = page.url();
      if (currentUrl.includes('profile') || currentUrl.includes('first_time_setup')) {
        console.log('✓ Successfully logged in with new password');
        
        // Navigate back to change password to change it back
        if (currentUrl.includes('first_time_setup')) {
          await page.goto('http://127.0.0.1:5000/user-management/change-password');
          await page.waitForTimeout(3000);
        } else {
          await page.goto('http://127.0.0.1:5000/user-management/change-password');
          await page.waitForLoadState('networkidle');
        }
        
        // Change password back to original
        console.log('Changing password back to original...');
        await page.fill('#current_password', 'NewPassword123!');
        await page.fill('#new_password', 'g9bDFB9JzgEaVZx');
        await page.fill('#confirm_new_password', 'g9bDFB9JzgEaVZx');
        await page.click('input[type="submit"]');
        await page.waitForTimeout(5000);
        
        // Verify redirect to login again
        currentUrl = page.url();
        if (currentUrl.includes('login')) {
          console.log('✓ Password change back to original successful');
        } else {
          console.log(`❌ Expected redirect to login, got: ${currentUrl}`);
        }
        
      } else {
        console.log(`❌ Failed to login with new password, current URL: ${currentUrl}`);
      }
      
    } else {
      console.log(`❌ Expected redirect to login page, got: ${currentUrl}`);
    }
    
    console.log('\n=== Corrected Password Change Workflow Test Complete ===');
    
  } catch (error) {
    console.error('Test failed:', error);
  } finally {
    await browser.close();
  }
})();