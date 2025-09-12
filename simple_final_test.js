const { chromium } = require('playwright');

(async () => {
  console.log('=== Simple Password Change Test ===');
  
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  // Set up console monitoring
  page.on('console', msg => {
    console.log(`Console ${msg.type()}: ${msg.text()}`);
  });
  
  try {
    // Go directly to change password page (will redirect to login first)
    console.log('1. Going directly to change password page...');
    await page.goto('http://127.0.0.1:5000/user-management/change-password');
    await page.waitForTimeout(3000);
    
    let currentUrl = page.url();
    console.log('2. Current URL after navigation:', currentUrl);
    
    // If redirected to login, login manually
    if (currentUrl.includes('/login')) {
      console.log('3. Redirected to login, attempting to login...');
      await page.fill('#username_or_email', 'iolaire');
      await page.fill('#password', 'g9bDFB9JzgEaVZx');
      await page.click('input[type="submit"]');
      await page.waitForTimeout(5000);
      
      currentUrl = page.url();
      console.log('4. URL after login:', currentUrl);
      
      // If redirected to change password, proceed
      if (currentUrl.includes('/change-password')) {
        console.log('5. Successfully reached change password page');
      } else {
        console.log('5. Not on change password page, navigating manually...');
        await page.goto('http://127.0.0.1:5000/user-management/change-password');
        await page.waitForTimeout(3000);
        currentUrl = page.url();
        console.log('6. URL after manual navigation:', currentUrl);
      }
    }
    
    // Check if we're on the change password page
    if (currentUrl.includes('/change-password')) {
      console.log('7. ✓ On change password page');
      
      // Check form fields exist
      const currentPasswordField = await page.locator('#current_password').count();
      const newPasswordField = await page.locator('#new_password').count();
      const confirmNewPasswordField = await page.locator('#confirm_new_password').count();
      
      console.log(`8. Form fields found - Current: ${currentPasswordField}, New: ${newPasswordField}, Confirm: ${confirmNewPasswordField}`);
      
      if (currentPasswordField > 0 && newPasswordField > 0 && confirmNewPasswordField > 0) {
        console.log('9. All form fields found, proceeding with password change...');
        
        // Fill out password change form
        await page.fill('#current_password', 'g9bDFB9JzgEaVZx');
        await page.fill('#new_password', 'NewTestPassword123!');
        await page.fill('#confirm_new_password', 'NewTestPassword123!');
        
        console.log('10. Form filled, submitting...');
        await page.click('input[type="submit"]');
        await page.waitForTimeout(5000);
        
        currentUrl = page.url();
        console.log('11. URL after password change submission:', currentUrl);
        
        if (currentUrl.includes('/login')) {
          console.log('12. ✓ Successfully redirected to login page after password change');
          
          // Check for success notification
          const notificationSelectors = [
            '.unified-notification .notification-message',
            '.alert-success',
            '.notification',
            '[class*="success"]'
          ];
          
          let successFound = false;
          for (const selector of notificationSelectors) {
            try {
              const elements = await page.locator(selector).count();
              if (elements > 0) {
                const text = await page.locator(selector).first().textContent();
                console.log(`Found notification: ${text}`);
                if (text.toLowerCase().includes('password') && 
                    (text.toLowerCase().includes('changed') || text.toLowerCase().includes('success'))) {
                  successFound = true;
                  console.log('✓ Password change success notification found');
                  break;
                }
              }
            } catch (err) {
              continue;
            }
          }
          
          if (!successFound) {
            console.log('⚠️  Success notification not found, but redirect occurred');
          }
          
          // Test login with new password
          console.log('13. Testing login with new password...');
          await page.fill('#username_or_email', 'iolaire');
          await page.fill('#password', 'NewTestPassword123!');
          await page.click('input[type="submit"]');
          await page.waitForTimeout(5000);
          
          currentUrl = page.url();
          if (currentUrl.includes('profile') || currentUrl.includes('first_time_setup') || currentUrl.includes('change-password')) {
            console.log('14. ✓ Successfully logged in with new password');
            
            // Change password back to original
            console.log('15. Changing password back to original...');
            if (!currentUrl.includes('change-password')) {
              await page.goto('http://127.0.0.1:5000/user-management/change-password');
              await page.waitForTimeout(3000);
            }
            
            await page.fill('#current_password', 'NewTestPassword123!');
            await page.fill('#new_password', 'g9bDFB9JzgEaVZx');
            await page.fill('#confirm_new_password', 'g9bDFB9JzgEaVZx');
            await page.click('input[type="submit"]');
            await page.waitForTimeout(5000);
            
            currentUrl = page.url();
            if (currentUrl.includes('/login')) {
              console.log('16. ✓ Password changed back to original successfully');
            } else {
              console.log(`16. ❌ Expected redirect to login, got: ${currentUrl}`);
            }
          } else {
            console.log(`14. ❌ Failed to login with new password, current URL: ${currentUrl}`);
          }
          
        } else {
          console.log(`12. ❌ Expected redirect to login page, got: ${currentUrl}`);
          
          // Check for error notifications
          const errorSelectors = [
            '.unified-notification .notification-message',
            '.alert-danger',
            '.alert-error',
            '.error-message',
            '[class*="error"]'
          ];
          
          for (const selector of errorSelectors) {
            try {
              const elements = await page.locator(selector).count();
              if (elements > 0) {
                const text = await page.locator(selector).first().textContent();
                console.log(`Error notification: ${text}`);
              }
            } catch (err) {
              continue;
            }
          }
        }
      } else {
        console.log('9. ❌ Not all form fields found');
      }
    } else {
      console.log('7. ❌ Not on change password page');
    }
    
    console.log('\\n=== Test Complete ===');
    
  } catch (error) {
    console.error('Test failed:', error);
  } finally {
    await browser.close();
  }
})();