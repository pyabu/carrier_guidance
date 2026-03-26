const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });
  await page.goto('http://127.0.0.1:5001/login', {waitUntil: 'networkidle2'});
  await page.screenshot({path: 'login_screenshot.png'});
  await page.goto('http://127.0.0.1:5001/signup', {waitUntil: 'networkidle2'});
  await page.screenshot({path: 'signup_screenshot.png'});
  await browser.close();
})();
