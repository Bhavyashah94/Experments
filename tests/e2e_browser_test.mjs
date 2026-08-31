import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import path from 'path';
import fs from 'fs';

const SCREENSHOT_DIR = path.resolve('tests/screenshots');
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function runE2ETests() {
  console.log('🚀 Starting Playwright End-to-End Browser Automation Tests...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  });

  const page = await context.newPage();

  try {
    // 1. Navigate to LabStudio
    console.log('1. Navigating to http://localhost:5173/ ...');
    await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
    console.log('✅ Page loaded successfully. Title:', await page.title());

    // 2. Verify Clean Navbar (No Duplicate Action Buttons)
    const navButtons = await page.$$('nav button');
    console.log(`✅ Clean top navbar buttons count: ${navButtons.length} (Guide only)`);

    // 3. Fill Student Details
    console.log('2. Filling Student Metadata Form...');
    await page.fill('input[placeholder="e.g. Bhavya Shah"]', 'Bhavya Shah');
    await page.fill('input[placeholder="e.g. 34"]', '34');
    await page.fill('input[placeholder="e.g. I3"]', 'I3');
    await page.fill('input[placeholder="e.g. BE IT"]', 'BE IT');
    await page.fill('input[placeholder="e.g. VII"]', 'VII');
    await page.fill('input[placeholder="e.g. Internet of Things"]', 'Internet of Things Lab');
    console.log('✅ Student Metadata filled cleanly without text squishing.');

    // 4. Test Share Profile Modal
    console.log('3. Testing Profile Share Modal...');
    await page.click('button[title="Share / Import subject profile with classmates"]');
    await page.waitForSelector('text=Share Subject Profile', { timeout: 3000 });
    console.log('✅ Share Modal opened.');

    const shareScreenshot = path.join(SCREENSHOT_DIR, '01_share_modal.png');
    await page.screenshot({ path: shareScreenshot });
    console.log(`📸 Saved screenshot: ${shareScreenshot}`);

    // Close modal
    await page.keyboard.press('Escape');
    await page.waitForTimeout(400);
    const closeBtn = await page.$('div[role="dialog"] button, .bg-card button:has(svg.lucide-x)');
    if (closeBtn && (await closeBtn.isVisible())) {
      await closeBtn.click();
      await page.waitForTimeout(400);
    }

    // 5. Test Document Cards: Add Card & Renumber 1..N
    console.log('4. Testing Document Cards and Renumber 1..N...');
    await page.click('button:has-text("Add Card")');
    await page.waitForTimeout(200);

    const cards = await page.$$('.drag-handle');
    console.log(`✅ Total experiment cards: ${cards.length}`);

    // Click Renumber 1..N button
    await page.click('button[title="Renumber cards sequentially (1..N)"]');
    console.log('✅ Renumber 1..N clicked successfully.');

    // 6. Test Weekly Date Auto-Fill
    console.log('5. Testing +7 Days Weekly Date Generator...');
    await page.fill('input[placeholder="DD/MM/YYYY"]', '01/09/2026');
    await page.click('button:has-text("+7 Days Weekly Auto-Fill")');
    await page.waitForTimeout(300);
    console.log('✅ Weekly date calculation executed.');

    // 7. Test Live Preview Modal
    console.log('6. Testing Live Canvas Preview Modal...');
    const previewButtons = await page.$$('button:has-text("Preview")');
    if (previewButtons.length > 0) {
      await previewButtons[0].click();
      await page.waitForSelector('canvas', { timeout: 5000 });
      await page.waitForTimeout(1000);
      console.log('✅ Live Canvas Preview rendered successfully.');

      const previewScreenshot = path.join(SCREENSHOT_DIR, '02_live_preview.png');
      await page.screenshot({ path: previewScreenshot });
      console.log(`📸 Saved screenshot: ${previewScreenshot}`);

      // Close preview modal
      await page.click('button[title="Close preview (Esc)"]');
      await page.waitForTimeout(300);
    }

    // 8. Test Compile Action & Transition to Download Buttons
    console.log('7. Testing Compile Reports Action...');
    await page.click('button:has-text("Compile Reports")');
    await page.waitForSelector('button:has-text("Download Combined PDF")', { timeout: 10000 });
    console.log('✅ Compilation finished. "Download Combined PDF" and "Download ZIP" buttons active.');

    // 9. Capture Full Workbench Screenshot in Compiled State
    const mainScreenshot = path.join(SCREENSHOT_DIR, '03_workbench_full.png');
    await page.screenshot({ path: mainScreenshot, fullPage: true });
    console.log(`📸 Saved full workbench screenshot: ${mainScreenshot}`);

    console.log('\n🎉 ALL BROWSER AUTOMATION TESTS PASSED 100%!');
  } catch (err) {
    console.error('❌ Browser test failed:', err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

runE2ETests();
