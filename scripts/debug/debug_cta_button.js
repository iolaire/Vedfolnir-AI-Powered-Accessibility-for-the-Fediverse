const { webkit } = require('playwright');

(async () => {
  const browser = await webkit.launch({ headless: false });
  const context = await browser.newContext({
    viewport: { width: 375, height: 667 } // Mobile viewport
  });
  const page = await context.newPage();
  
  await page.goto('http://127.0.0.1:5000');
  await page.waitForLoadState('domcontentloaded');
  
  // Check if CTA buttons exist
  const ctaButtons = await page.locator('.cta-button').count();
  console.log(`Found ${ctaButtons} CTA buttons`);
  
  // Check if mobile-touch-compliant buttons exist
  const mobileButtons = await page.locator('.mobile-touch-compliant').count();
  console.log(`Found ${mobileButtons} mobile-touch-compliant buttons`);
  
  // Get the first CTA button
  const firstButton = page.locator('.cta-button').first();
  const isVisible = await firstButton.isVisible();
  console.log(`First CTA button visible: ${isVisible}`);
  
  if (isVisible) {
    const boundingBox = await firstButton.boundingBox();
    console.log('Button bounding box:', boundingBox);
    
    // Get computed styles
    const styles = await firstButton.evaluate(el => {
      const computed = window.getComputedStyle(el);
      return {
        height: computed.height,
        minHeight: computed.minHeight,
        display: computed.display,
        padding: computed.padding,
        boxSizing: computed.boxSizing
      };
    });
    console.log('Button computed styles:', styles);
  }
  
  await page.screenshot({ path: 'debug_mobile_cta.png' });
  await browser.close();
})();