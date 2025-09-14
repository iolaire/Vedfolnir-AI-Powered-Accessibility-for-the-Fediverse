const { chromium } = require('playwright');

(async () => {
  console.log('=== Debug Form Submission Test ===');
  
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  // Set up console monitoring
  page.on('console', msg => {
    console.log(`Console ${msg.type()}: ${msg.text()}`);
  });
  
  // Set up request/response monitoring
  page.on('request', request => {
    if (request.url().includes('/user-management/change-password') && request.method() === 'POST') {
      console.log('\n=== FORM SUBMISSION REQUEST ===');
      console.log('URL:', request.url());
      console.log('Method:', request.method());
      console.log('Headers:', request.headers());
      console.log('Post data:', request.postData());
    }
  });
  
  page.on('response', response => {
    if (response.url().includes('/user-management/change-password') && response.request().method() === 'POST') {
      console.log('\n=== FORM SUBMISSION RESPONSE ===');
      console.log('Status:', response.status());
      console.log('Headers:', response.headers());
      response.text().then(text => {
        console.log('Response body:', text.substring(0, 500));
      });
    }
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
    
    // Examine form HTML
    const formHtml = await page.locator('form').innerHTML();
    console.log('\n=== FORM HTML ANALYSIS ===');
    console.log('Form has CSRF token input:', formHtml.includes('csrf_token'));
    console.log('Form has current_password field:', formHtml.includes('current_password'));
    console.log('Form has new_password field:', formHtml.includes('new_password'));
    console.log('Form has confirm_new_password field:', formHtml.includes('confirm_new_password'));
    
    // Get form field values before filling
    console.log('\n=== FORM FIELD VALUES (BEFORE) ===');
    const currentPasswordField = await page.locator('#current_password');
    const newPasswordField = await page.locator('#new_password');
    const confirmNewPasswordField = await page.locator('#confirm_new_password');
    
    console.log('Current password value:', await currentPasswordField.inputValue());
    console.log('New password value:', await newPasswordField.inputValue());
    console.log('Confirm password value:', await confirmNewPasswordField.inputValue());
    
    // Fill form
    console.log('\n=== FILLING FORM ===');
    await currentPasswordField.fill('g9bDFB9JzgEaVZx');
    await newPasswordField.fill('NewTestPassword123!');
    await confirmNewPasswordField.fill('NewTestPassword123!');
    
    // Get form field values after filling
    console.log('\n=== FORM FIELD VALUES (AFTER) ===');
    console.log('Current password value:', await currentPasswordField.inputValue());
    console.log('New password value:', await newPasswordField.inputValue());
    console.log('Confirm password value:', await confirmNewPasswordField.inputValue());
    
    // Get form data that will be submitted
    const formData = await page.evaluate(() => {
      const form = document.querySelector('form');
      const formData = new FormData(form);
      const result = {};
      for (let [key, value] of formData.entries()) {
        result[key] = value;
      }
      return result;
    });
    
    console.log('\n=== FORM DATA THAT WILL BE SUBMITTED ===');
    console.log(formData);
    
    // Submit the form
    console.log('\n=== SUBMITTING FORM ===');
    await page.click('input[type="submit"]');
    
    // Wait for response
    await page.waitForTimeout(5000);
    
    currentUrl = page.url();
    console.log('\n=== AFTER SUBMISSION ===');
    console.log('URL after submission:', currentUrl);
    
  } catch (error) {
    console.error('Test failed:', error);
  } finally {
    await browser.close();
  }
})();