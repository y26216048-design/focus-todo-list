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
  # Badges center their numbers inside equal-height pills.
  for badge in page.locator('.desktop-nav [data-count]').all():
   position=badge.evaluate("""el=>{const box=el.getBoundingClientRect();const range=document.createRange();range.selectNodeContents(el);const text=range.getBoundingClientRect();return {dx:Math.abs(text.x+text.width/2-box.x-box.width/2),dy:Math.abs(text.y+text.height/2-box.y-box.height/2)}}""")
   assert position['dx']<=2 and position['dy']<=2,position
  active=page.evaluate("""()=>{document.querySelector('.desktop-nav [data-view=upcoming]').click();return document.querySelector('#main').getAnimations().length}""")
  assert active>0
  page.wait_for_timeout(260)
  page.locator('.stats [data-view=completed]').click()
  expect(page.locator('#page-title')).to_have_text('Завершено')
  page.locator('.stats [data-view=today]').click()
  expect(page.locator('#page-title')).to_have_text('Сегодня')
  shell=page.locator('.app-shell').bounding_box()
  assert shell['x']==shell['y']==0 and shell['width']==width and shell['height']>=height
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
  if width==1920:
   initial=page.evaluate("""()=>{document.querySelector('.desktop-nav [data-view=upcoming]').click();document.querySelector('.desktop-nav [data-view=today]').click();return parseInt(document.querySelector('.sidebar [data-progress]').textContent)}""")
   assert initial==0
   page.wait_for_timeout(200)
   middle=int(page.locator('.sidebar [data-progress]').inner_text().rstrip('%'))
   assert 0<middle<40,middle
   page.wait_for_timeout(1000)
   assert page.locator('.sidebar [data-progress]').inner_text()=='40%'
  page.wait_for_timeout(1000)
  page.mouse.move(width-5,height-5)
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
