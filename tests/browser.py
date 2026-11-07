"""End-to-end browser checks; BASE_URL can point to the public Pages site."""
import os
from pathlib import Path
from datetime import date,timedelta
from playwright.sync_api import sync_playwright, expect
URL=os.environ.get('BASE_URL','http://127.0.0.1:4173/')
OUT=Path('test-results');OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_PATH') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None), args=['--no-sandbox'])
    for width,height in [(1280,960),(390,844),(320,740),(768,1024)]:
        context=browser.new_context(viewport={'width':width,'height':height},is_mobile=width<761,has_touch=width<761,color_scheme='light',reduced_motion='reduce',locale='ru-RU')
        page=context.new_page(); errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(URL);page.wait_for_selector('.task-row')
        assert page.locator('.task-row').count()==5
        page.screenshot(path=str(OUT/f'initial-{width}-light.png'),full_page=True)
        page.get_by_role('button',name='Включить тёмную тему').click()
        page.reload();expect(page.locator('html')).to_have_attribute('data-theme','dark')
        page.screenshot(path=str(OUT/f'initial-{width}-dark.png'),full_page=True)
        page.get_by_role('button',name='Включить светлую тему').click()
        page.get_by_label('Название задачи').fill('Проверка VELIO <b>без HTML</b>')
        page.get_by_label('Дата задачи',exact=True).fill(date.today().isoformat())
        page.get_by_label('Время задачи',exact=True).fill('12:30')
        page.locator('#task-form .add-button').click()
        expect(page.locator('.task-row')).to_have_count(6)
        page.reload();expect(page.locator('.task-row')).to_have_count(6)
        row=page.locator('.task-row').filter(has_text='Проверка VELIO')
        assert row.locator('.task-title b').count()==0
        row.get_by_role('checkbox').check()
        expect(row).to_have_class('task-row done')
        nav=page.locator('.bottom-nav' if width<761 else '.desktop-nav')
        nav.locator('[data-view=completed]').click()
        row=page.locator('.task-row').filter(has_text='Проверка VELIO')
        expect(row).to_be_visible();row.get_by_role('checkbox').click();expect(row).to_have_count(0)
        nav.locator('[data-view=today]').click()
        row=page.locator('.task-row').filter(has_text='Проверка VELIO');row.get_by_role('button').click();expect(row).to_have_count(0)
        page.locator('#toast button').click();expect(row).to_have_count(1)
        row.get_by_role('button').click();page.reload();expect(row).to_have_count(0)
        nav.locator('[data-view=upcoming]').click()
        page.get_by_label('Название задачи').fill('Будущая задача')
        page.get_by_label('Дата задачи',exact=True).fill((date.today()+timedelta(days=2)).isoformat())
        page.locator('#task-form .add-button').click();expect(page.locator('#page-title')).to_have_text('Предстоящие')
        expect(page.locator('.task-row').filter(has_text='Будущая задача')).to_be_visible()
        page.reload();expect(page.locator('.task-row').filter(has_text='Будущая задача')).to_be_visible()
        for v in ['today','upcoming','completed']:
            nav.locator(f'[data-view={v}]').click()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'Overflow at {width} {v}'
            if width<761:
                assert not page.locator('.desktop-nav').is_visible()
                rows=page.locator('.task-row')
                if rows.count():
                    page.evaluate('window.scrollTo(0,document.documentElement.scrollHeight)')
                    assert rows.last.bounding_box()['y']+rows.last.bounding_box()['height']<=page.locator('.bottom-nav').bounding_box()['y']
            page.screenshot(path=str(OUT/f'{v}-{width}.png'),full_page=True)
        # Desktop fills the viewport, and calendar performs real task operations.
        if width>=761:
            shell=page.locator('.app-shell').bounding_box()
            assert shell['x']==0 and shell['y']==0 and shell['width']==width
            page.locator('#calendar-open').click()
            expect(page.get_by_role('dialog')).to_be_visible()
            page.locator('#calendar-date').fill((date.today()+timedelta(days=2)).isoformat())
            page.locator('#calendar-date').dispatch_event('change')
            calendar_row=page.locator('#calendar-tasks .task-row').filter(has_text='Будущая задача')
            expect(calendar_row).to_be_visible()
            calendar_row.get_by_role('checkbox').click()
            expect(calendar_row.get_by_role('checkbox')).to_be_checked()
            calendar_row.get_by_role('button').click()
            expect(calendar_row).to_have_count(0)
            page.locator('#toast button').click()
            expect(calendar_row).to_have_count(1)
            page.locator('#calendar-add').click()
            expect(page.get_by_role('dialog')).not_to_be_visible()
            expect(page.locator('#task-date')).to_have_value((date.today()+timedelta(days=2)).isoformat())
            page.locator('#calendar-open').click()
            page.locator('#calendar-today').click()
            expect(page.locator('#calendar-date')).to_have_value(date.today().isoformat())
            page.keyboard.press('Escape')
            expect(page.get_by_role('dialog')).not_to_be_visible()
            page.locator('#calendar-open').click()
            page.locator('#calendar-close').click()
            expect(page.get_by_role('dialog')).not_to_be_visible()
        # Empty states persist after reloading.
        page.evaluate("localStorage.setItem('velio-tasks-v1','[]')");page.reload()
        for v in ['today','upcoming','completed']:
            nav.locator(f'[data-view={v}]').click();expect(page.locator('#empty-state')).to_be_visible()
        page.reload();assert page.locator('.task-row').count()==0
        assert not errors,errors
        print(f'PASS {URL} {width}x{height}: CRUD, undo, storage, dates, sections, themes, empty states, no overflow, no page errors')
        context.close()
    browser.close()
