const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  console.log('=== QA Flow Test: Aspirante Registration & Application ===\n');
  
  let browser;
  let context;
  let page;
  let errors = [];
  
  try {
    // Launch with chromium
    browser = await chromium.launch({ 
      headless: true,
      executablePath: '/usr/bin/chromium'
    });
    context = await browser.newContext();
    page = await context.newPage();
    
    // Capture console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(`Console Error: ${msg.text()}`);
      }
    });
    
    page.on('pageerror', err => {
      errors.push(`Page Error: ${err.message}`);
    });
    
    // Test 1: Homepage
    console.log('1. Navigating to homepage...');
    await page.goto('http://127.0.0.1:8000/', { timeout: 30000 });
    console.log(`   ✓ Homepage loaded: ${page.url()}`);
    
    // Test 2: Check for registration link
    console.log('2. Looking for registration...');
    const pageContent = await page.content();
    
    // Look for register/signup links
    const registerLinks = await page.locator('a[href*="register"], a[href*="signup"], a[href*="registro"]').count();
    console.log(`   Found ${registerLinks} register links`);
    
    // Try common registration paths
    const possiblePaths = [
      '/accounts/register/',
      '/accounts/signup/',
      '/registro/',
      '/signup/',
    ];
    
    let registerUrl = null;
    for (const p of possiblePaths) {
      try {
        const resp = await page.request.get(`http://127.0.0.1:8000${p}`);
        if (resp.ok()) {
          registerUrl = p;
          console.log(`   ✓ Found registration at: ${p}`);
          break;
        }
      } catch (e) {}
    }
    
    // Test 3: Navigate to registration
    if (registerUrl) {
      console.log('3. Opening registration page...');
      await page.goto(`http://127.0.0.1:8000${registerUrl}`, { timeout: 30000 });
      console.log(`   ✓ Registration page: ${page.url()}`);
      
      // Get form fields
      const inputs = await page.locator('input').count();
      console.log(`   Found ${inputs} input fields`);
    } else {
      console.log('   ⚠ No registration page found - checking for convocation pages instead');
    }
    
    // Test 4: Look for convocation pages
    console.log('4. Looking for convocation pages...');
    await page.goto('http://127.0.0.1:8000/convocatorias/', { timeout: 30000 }).catch(() => {});
    console.log(`   Convatorias page: ${page.url()}`);
    
    // Try alternative paths
    const convPaths = ['/convocatories/', '/convocatoria/', '/'];
    for (const p of convPaths) {
      try {
        await page.goto(`http://127.0.0.1:8000${p}`, { timeout: 10000 });
        console.log(`   ${p}: ${page.url()}`);
      } catch (e) {}
    }
    
    // Test 5: Check API endpoints
    console.log('5. Checking API endpoints...');
    const apiEndpoints = [
      '/api/',
      '/api/convocatories/',
      '/api/applications/',
      '/accounts/api/',
    ];
    
    for (const api of apiEndpoints) {
      try {
        const resp = await page.request.get(`http://127.0.0.1:8000${api}`);
        console.log(`   ${api}: ${resp.status()}`);
      } catch (e) {
        console.log(`   ${api}: ERROR`);
      }
    }
    
    console.log('\n=== Summary ===');
    console.log(`Errors captured: ${errors.length}`);
    errors.forEach(e => console.log(`  - ${e}`));
    
  } catch (error) {
    console.error('\n❌ FATAL ERROR:', error.message);
  } finally {
    if (browser) await browser.close();
  }
})();
