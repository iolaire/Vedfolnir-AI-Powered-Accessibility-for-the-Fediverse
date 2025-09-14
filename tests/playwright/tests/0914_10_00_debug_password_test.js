const { chromium } = require('playwright');

(async () => {
  console.log('=== Debug Password Change Test ===');
  
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  // Set up console monitoring
  page.on('console', msg => {
    console.log(`Console ${msg.type()}: ${msg.text()}`);
  });
  
  try {
    // Login with iolaire
    console.log('Logging in with iolaire...');
    await page.goto('http://127.0.0.1:5000/user-management/login');
    await page.waitForLoadState('networkidle');
    
    await page.fill('#username_or_email', 'iolaire');
    await page.fill('#password', 'g9bDFB9JzgEaVZx');
    await page.click('input[type="submit"]');
    await page.waitForTimeout(3000);
    
    // Handle first-time setup redirect
    let currentUrl = page.url();
    if (currentUrl.includes('/first_time_setup')) {
      console.log('Handling first-time setup redirect...');
      await page.goto('http://127.0.0.1:5000/user-management/change-password');
      await page.waitForTimeout(2000);
    } else {
      // Navigate to change password page
      console.log('Navigating to change password page...');
      await page.goto('http://127.0.0.1:5000/user-management/change-password');
      await page.waitForLoadState('networkidle');
    }
    
    console.log('Current URL:', page.url());
    
    // Check form fields exist
    const currentPasswordField = await page.locator('#current_password').count();
    const newPasswordField = await page.locator('#new_password').count();
    const confirmNewPasswordField = await page.locator('#confirm_new_password').count();
    const submitButton = await page.locator('input[type="submit"]').count();
    
    console.log(`Form fields found - Current: ${currentPasswordField}, New: ${newPasswordField}, Confirm: ${confirmNewPasswordField}, Submit: ${submitButton}`);
    
    // Fill form with correct data
    console.log('Filling form with valid data...');
    await page.fill('#current_password', 'g9bDFB9JzgEaVZx');
    await page.fill('#new_password', 'NewTestPassword123!');
    await page.fill('#confirm_new_password', 'NewTestPassword123!');
    
    // Get the form HTML before submission to check CSRF token
    const formHtml = await page.locator('form').innerHTML();
    const hasCsrfToken = formHtml.includes('csrf_token');
    console.log(`Form has CSRF token: ${hasCsrfToken}`);
    
    // Submit the form
    console.log('Submitting form...');
    await page.click('input[type="submit"]');
    
    // Wait for response
    await page.waitForTimeout(5000);
    
    currentUrl = page.url();
    console.log('URL after submission:', currentUrl);
    
    // Check if we were redirected to login (expected behavior)
    if (currentUrl.includes('login')) {
      console.log('✓ Successfully redirected to login page');
      
      // Look for success notification on login page
      const notifications = await page.locator('.unified-notification').count();
      console.log(`Notifications found on login page: ${notifications}`);
      
      if (notifications > 0) {
        const notificationText = await page.locator('.unified-notification .notification-message').textContent();
        console.log(`Notification text: ${notificationText}`);
      }
    } else {
      console.log('❌ Not redirected to login, still on:', currentUrl);
      
      // Check for errors on current page
      const errors = await page.locator('.unified-notification, .alert, .error-message').count();
      console.log(`Error elements found: ${errors}`);
      
      if (errors > 0) {
        const errorText = await page.locator('.unified-notification .notification-message, .alert, .error-message').first().textContent();
        console.log(`Error text: ${errorText}`);
      }
    }
    
  } catch (error) {
    console.error('Test failed:', error);
  } finally {
    await browser.close();
  }
})();