from playwright.sync_api import sync_playwright, expect
from pathlib import Path
import os
URL=os.environ.get("BASE_URL","http://127.0.0.1:4173/")
Path("test-results").mkdir(exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None),args=['--no-sandbox'])
 for width,height in [(1920,1080),(1440,900),(1280,720),(1024,768),(980,720)]:
  page=b.new_page(viewport={'width':width,'height':height},color_scheme='dark')
  page.goto(URL)
  page.locator('.desktop-nav [data-view=upcoming]').click()
  assert page.locator('#main').evaluate('el => el.getAnimations().length')>0
  page.wait_for_timeout(260)
  page.locator('.stats [data-view=completed]').click()
  expect(page.locator('#page-title')).to_have_text('Завершено')
  page.locator('.stats [data-view=today]').click()
  expect(page.locator('#page-title')).to_have_text('Сегодня')
  shell=page.locator('.app-shell').bounding_box()
  assert shell['x']==shell['y']==0 and shell['width']==width and shell['height']>=height
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
  page.wait_for_timeout(260)
  page.screenshot(path=f'test-results/fullscreen-{width}.png',full_page=True)
  page.locator('#calendar-open').click()
  page.screenshot(path=f'test-results/calendar-{width}.png',full_page=True)
  page.keyboard.press('Escape')
  page.emulate_media(reduced_motion='reduce')
  page.locator('.desktop-nav [data-view=upcoming]').click()
  assert page.locator('#main').evaluate('el => el.getAnimations().length')==0
  print(f'PASS {width}x{height}: full viewport, statistic buttons, calendar, transitions and reduced motion')
  page.close()
 b.close()
