#!/usr/bin/env node

const { chromium } = require('playwright');

(async () => {
  console.log('=== Manual Password Strength JavaScript Test ===');
  
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  // Set up console monitoring
  const consoleMessages = [];
  page.on('console', msg => {
    const message = `Console ${msg.type()}: ${msg.text()}`;
    consoleMessages.push(message);
    console.log(message);
  });
  
  page.on('pageerror', error => {
    console.log(`Page Error: ${error.message}`);
    consoleMessages.push(`Page Error: ${error.message}`);
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
      await page.goto('http://127.0.0.1:5000/user-management/profile');
      await page.waitForTimeout(3000);
    }
    
    // Navigate to change password page
    console.log('Navigating to change password page...');
    await page.goto('http://127.0.0.1:5000/user-management/change-password');
    await page.waitForLoadState('networkidle');
    
    // Check if JavaScript function exists
    const jsFunctionExists = await page.evaluate(() => {
      return typeof window.updatePasswordStrength === 'function';
    });
    
    console.log(`updatePasswordStrength function exists: ${jsFunctionExists}`);
    
    if (jsFunctionExists) {
      // Test password strength functionality
      console.log('Testing password strength functionality...');
      
      const testPasswords = [
        'weak',           // Very weak
        'password123',    // Weak
        'Password123',    // Fair
        'Password123!',   // Good
        'Str0ngP@ssw0rd!'  // Strong
      ];
      
      for (const password of testPasswords) {
        console.log(`\nTesting password: "${password}"`);
        
        await page.fill('#new_password', password);
        await page.waitForTimeout(1000); // Wait for JavaScript to update
        
        const currentState = await page.evaluate(() => {
          const progressBar = document.getElementById('password-strength-bar');
          const strengthText = document.getElementById('strength-level');
          
          return {
            width: progressBar ? progressBar.style.width : 'N/A',
            text: strengthText ? strengthText.textContent : 'N/A',
            class: progressBar ? progressBar.className : 'N/A'
          };
        });
        
        console.log(`  Result: width=${currentState.width}, text="${currentState.text}", class="${currentState.class}"`);
      }
    } else {
      console.log('❌ Password strength JavaScript function not found');
      // Take screenshot for debugging
      await page.screenshot({ path: 'password_strength_js_missing.png' });
    }
    
    // Check console messages for password strength debug info
    const passwordStrengthMessages = consoleMessages.filter(msg => 
      msg.includes('Password strength') ||
      msg.includes('password-strength') ||
      msg.includes('strength-level') ||
      msg.includes('Password strength check:')
    );
    
    console.log(`\nFound ${passwordStrengthMessages.length} password strength related messages:`);
    passwordStrengthMessages.forEach((msg, index) => {
      console.log(`  ${index + 1}. ${msg}`);
    });
    
    console.log('\n=== Manual Test Complete ===');
    
  } catch (error) {
    console.error('Test failed:', error);
  } finally {
    await browser.close();
  }
})();