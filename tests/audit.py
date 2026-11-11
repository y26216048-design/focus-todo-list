"""Regression scenarios for data integrity, timing, dates and keyboard access.

Every test uses an isolated browser context, including on the public site.
No real user's browser storage is accessed.
"""

import os
import unittest
from playwright.sync_api import sync_playwright, expect
from support import launch, BROWSER

URL = os.environ.get("BASE_URL", "http://127.0.0.1:4173/")
KEY = "velio-tasks-v1"


def task(identifier, done=False, date="2026-11-11", text=None, time=""):
    return dict(id=identifier, text=text or identifier, done=done, date=date, time=time)


class Audit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = launch(cls.playwright)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(
            locale="ru-RU", timezone_id="UTC", reduced_motion="reduce"
        )
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.errors, self.network = [], []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.on(
            "console",
            lambda msg: self.errors.append(msg.text) if msg.type == "error" else None,
        )
        self.page.on("requestfailed", lambda request: self.network.append(request.url))
        self.page.on(
            "response",
            lambda response: (
                self.network.append(f"{response.status} {response.url}")
                if response.status >= 400
                else None
            ),
        )
        self.page.clock.install(time="2026-11-11T12:00:00Z")

    def tearDown(self):
        self.assertEqual(self.errors, [])
        self.assertEqual(self.network, [])

    def open(self, tasks):
        self.page.goto(URL)
        self.page.evaluate(
            '(data) => localStorage.setItem("velio-tasks-v1", JSON.stringify(data))',
            tasks,
        )
        self.page.reload()

    def saved(self, count):
        self.page.wait_for_function(
            '(n) => JSON.parse(localStorage.getItem("velio-tasks-v1")).length === n',
            arg=count,
        )
        return self.page.evaluate('JSON.parse(localStorage.getItem("velio-tasks-v1"))')

    def add(self, title, date="2026-11-11"):
        self.page.locator("#task-input").fill(title)
        self.page.locator("#task-date").fill(date)
        self.page.locator("#task-form .add-button").click()

    def test_progress_is_immediate_and_persistent(self):
        self.open([task("a"), task("b"), task("c")])
        for identifier, percentage in [
            ("a", "33%"),
            ("b", "67%"),
            ("c", "100%"),
            ("a", "67%"),
        ]:
            values = self.page.evaluate(
                """id => {
                document.querySelector(`[data-id="${id}"] .task-check`).click();
                return [...document.querySelectorAll('[data-progress]')].map(el => el.textContent)
                    .concat([...document.querySelectorAll('.ring')].map(el => el.style.getPropertyValue('--value')));
            }""",
                identifier,
            )
            self.assertTrue(all(value == percentage for value in values), values)
        self.page.wait_for_function(
            'JSON.parse(localStorage.getItem("velio-tasks-v1")).filter(t=>t.done).length === 2'
        )
        self.page.reload()
        expect(self.page.locator("#stat-done")).to_have_text("2")
        expect(self.page.locator("#stat-left")).to_have_text("1")
        self.page.locator('[data-id="b"] .delete-button').click()
        expect(self.page.locator("[data-progress]").first).to_have_text("50%")
        self.page.locator("#toast button").click()
        expect(self.page.locator("[data-progress]").first).to_have_text("67%")
        self.saved(3)
        self.open([])
        expect(self.page.locator("[data-progress]").first).to_have_text("0%")
        self.add("single")
        self.page.locator(".task-check").check()
        expect(self.page.locator("[data-progress]").first).to_have_text("100%")

    def test_rapid_input_validation_and_safe_long_text(self):
        self.open([])
        self.add("   ")
        expect(self.page.locator(".task-row")).to_have_count(0)
        self.assertFalse(
            self.page.locator("#task-input").evaluate("el => el.checkValidity()")
        )
        self.page.locator("#task-input").fill("valid")
        self.page.locator("#task-date").fill("")
        self.page.locator("#task-form .add-button").click()
        expect(self.page.locator(".task-row")).to_have_count(0)
        self.page.locator("#task-date").fill("2026-11-11")
        self.page.evaluate(
            """() => { for (let i=0; i<10; i++) document.querySelector('#task-form').requestSubmit(); }"""
        )
        expect(self.page.locator(".task-row")).to_have_count(1)
        self.page.evaluate(
            """() => { for (let i=0; i<20; i++) document.querySelector('.task-check').click(); }"""
        )
        self.saved(1)
        self.page.wait_for_function(
            '!JSON.parse(localStorage.getItem("velio-tasks-v1"))[0].done'
        )
        text = (
            "<img src=x onerror=alert(1)> & \" ' <script>alert(2)</script>" + "Ж" * 300
        )
        self.add(text)
        self.saved(2)
        expect(self.page.locator(".task-title").last).to_have_text(text[:300])
        expect(self.page.locator(".task-title img, .task-title script")).to_have_count(
            0
        )
        for width in (320, 390, 768, 1024, 1440, 1920):
            self.page.set_viewport_size(dict(width=width, height=844))
            self.assertTrue(
                self.page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                ),
                width,
            )
        self.page.reload()
        expect(self.page.locator(".task-row")).to_have_count(2)

    def test_two_tabs_rebase_and_serialize_changes(self):
        self.open([task("initial")])
        # Suppress storage notifications to reproduce a stale/background tab.
        other = self.context.new_page()
        other.add_init_script(
            "window.addEventListener('storage', e => e.stopImmediatePropagation())"
        )
        other.goto(URL)
        self.add("from-first")
        self.saved(2)
        other.locator("#task-input").fill("from-second")
        other.locator("#task-form .add-button").click()
        self.saved(3)
        self.assertEqual(
            {t["text"] for t in self.saved(3)}, {"initial", "from-first", "from-second"}
        )
        # Hold the same Web Lock while both tabs queue changes. Neither write
        # may overwrite the other's data when the lock is released.
        self.page.evaluate("""() => {
            navigator.locks.request('velio-tasks-v1', () => new Promise(resolve => window.releaseAuditLock = resolve));
        }""")
        self.page.wait_for_function('typeof window.releaseAuditLock === "function"')
        self.add("queued-first")
        other.locator("#task-input").fill("queued-second")
        other.locator("#task-form .add-button").click()
        self.assertEqual(
            len(
                self.page.evaluate('JSON.parse(localStorage.getItem("velio-tasks-v1"))')
            ),
            3,
        )
        self.page.evaluate("window.releaseAuditLock()")
        self.saved(5)
        # Complete in one tab and delete a different task in the stale tab.
        self.page.locator("[data-id=initial] .task-check").check()
        other.locator("[data-id=initial] .delete-button").click()
        self.saved(4)
        self.page.reload()
        expect(self.page.locator("[data-id=initial]")).to_have_count(0)
        other.locator("#toast button").click()
        self.saved(5)
        self.assertEqual(len({t["id"] for t in self.saved(5)}), 5)
        other.close()

    def test_immediate_reload_before_async_save(self):
        for iteration in range(5):
            self.open([])
            self.page.evaluate("""() => {
                navigator.locks.request('velio-tasks-v1', () => {
                    window.auditLockHeld = true;
                    return new Promise(() => {});
                });
            }""")
            self.page.wait_for_function("window.auditLockHeld === true")
            title = f"reload-with-pending-lock-{iteration}"
            self.add(title)
            self.assertEqual(self.saved(0), [])
            self.page.reload()
            expect(self.page.locator(".task-title")).to_have_text(title)
            self.saved(1)
            self.page.wait_for_function(
                "!Object.keys(localStorage).some(key => key.startsWith('velio-pending-v1:'))"
            )

    def test_theme_sync_and_clear_storage_event(self):
        self.open([task("initial")])
        other = self.context.new_page()
        other.goto(URL)
        self.page.locator(".theme-toggle").click()
        theme = self.page.locator("html").get_attribute("data-theme")
        expect(other.locator("html")).to_have_attribute("data-theme", theme)
        other.reload()
        expect(other.locator("html")).to_have_attribute("data-theme", theme)
        other.evaluate("localStorage.clear()")
        expect(self.page.locator(".task-row")).to_have_count(0)
        other.close()

    def test_corrupt_data_is_not_overwritten(self):
        self.page.goto(URL)
        for raw in (
            "{broken",
            "{}",
            '[{"id":"bad","text":"keep me","date":"2026-02-30","done":false}]',
        ):
            self.page.evaluate(
                '(raw) => localStorage.setItem("velio-tasks-v1", raw)', raw
            )
            self.page.reload()
            expect(self.page.locator("#storage-error")).to_be_visible()
            self.add("memory-only")
            self.page.wait_for_timeout(100)
            self.assertEqual(
                self.page.evaluate('localStorage.getItem("velio-tasks-v1")'), raw
            )
            expect(self.page.locator("#storage-error")).to_be_visible()

        self.page.evaluate("""() => {
            localStorage.setItem('velio-tasks-v1', '[]');
            localStorage.setItem('velio-pending-v1:broken', '{broken');
        }""")
        self.page.reload()
        expect(self.page.locator("#storage-error")).to_be_visible()
        self.add("do-not-overwrite-broken-journal")
        self.assertEqual(
            self.page.evaluate("localStorage.getItem('velio-tasks-v1')"), "[]"
        )
        self.assertEqual(
            self.page.evaluate("localStorage.getItem('velio-pending-v1:broken')"),
            "{broken",
        )

    def test_storage_quota_and_denied_access(self):
        self.open([])
        self.page.evaluate("""() => {
            window.auditSetItem = Storage.prototype.setItem;
            Storage.prototype.setItem = function(key, value) {
                if (key === 'velio-tasks-v1') throw new DOMException('Full', 'QuotaExceededError');
                return window.auditSetItem.call(this, key, value);
            };
        }""")
        self.add("memory-one")
        expect(self.page.locator("#storage-error")).to_be_visible()
        self.add("memory-two")
        expect(self.page.locator(".task-row")).to_have_count(2)
        self.assertEqual(self.saved(0), [])
        self.page.evaluate("() => { Storage.prototype.setItem = window.auditSetItem; }")
        self.add("saved-three")
        self.saved(3)
        expect(self.page.locator("#storage-error")).to_be_hidden()
        self.page.reload()
        expect(self.page.locator(".task-row")).to_have_count(3)
        self.page.add_init_script(
            "Storage.prototype.getItem = function() { throw new DOMException('Denied', 'SecurityError'); }"
        )
        self.page.reload()
        expect(self.page.locator("#storage-error")).to_be_visible()
        self.add("works-in-memory")
        expect(self.page.locator(".task-row")).to_have_count(1)

    def test_legacy_migration_and_empty_persistence(self):
        self.page.goto(URL)
        self.page.evaluate("""() => {
            localStorage.removeItem('velio-tasks-v1');
            localStorage.setItem('focus-todo-tasks-v1', JSON.stringify([{text:'Legacy <b>',done:true}]));
        }""")
        self.page.reload()
        self.assertEqual(self.saved(1)[0]["text"], "Legacy <b>")
        self.page.locator(".delete-button").click()
        self.saved(0)
        self.page.reload()
        expect(self.page.locator(".task-row")).to_have_count(0)
        self.assertIsNotNone(
            self.page.evaluate('localStorage.getItem("focus-todo-tasks-v1")')
        )

    def test_day_rollover_without_focus(self):
        self.page.clock.set_fixed_time("2026-11-11T23:59:45Z")
        self.open(
            [
                task("yesterday-active"),
                task("yesterday-done", True),
                task("tomorrow", date="2026-11-12"),
            ]
        )
        self.page.clock.fast_forward(31000)
        # fixed_time does not advance Date; set_system_time simulates midnight.
        self.page.clock.set_system_time("2026-11-12T00:00:16Z")
        self.page.clock.fast_forward(30000)
        expect(self.page.locator("[data-id=tomorrow]")).to_be_visible()
        expect(self.page.locator("[data-id=yesterday-active]")).to_be_visible()
        expect(self.page.locator("[data-id=yesterday-done]")).to_have_count(0)
        expect(self.page.locator("#task-date")).to_have_value("2026-11-12")
        expect(self.page.locator(".group-title")).to_have_text("Просроченные1")

    def test_timezone_calendar_dates_remain_local(self):
        self.open([task("date-only", date="2026-11-12", time="00:30")])
        state = self.context.storage_state()
        for zone, today in [
            ("Pacific/Kiritimati", "2026-11-12"),
            ("America/Los_Angeles", "2026-11-11"),
        ]:
            context = self.browser.new_context(
                timezone_id=zone, storage_state=state, reduced_motion="reduce"
            )
            try:
                page = context.new_page()
                page.clock.install(time="2026-11-12T00:30:00Z")
                page.goto(URL)
                expect(page.locator("#task-date")).to_have_value(today)
                page.locator("#calendar-open").click()
                page.locator("#calendar-date").fill("2026-11-12")
                page.locator("#calendar-date").dispatch_event("change")
                expect(page.locator("#calendar-tasks .task-title")).to_have_text(
                    "date-only"
                )
                expect(page.locator("#calendar-tasks .task-meta")).to_contain_text(
                    "00:30"
                )
                page.locator("#calendar-date").fill("")
                page.locator("#calendar-date").dispatch_event("change")
                expect(page.locator("#calendar-add")).to_be_disabled()
            finally:
                context.close()

    def test_invalid_date_time_and_last_delete_undo(self):
        self.open([])
        self.page.locator("#task-input").fill("invalid-schedule")
        for invalid in ("0000-01-01", "10000-01-01"):
            self.page.locator("#task-date").evaluate(
                "(el, value) => el.value = value", invalid
            )
            self.page.locator("#task-form .add-button").click()
            expect(self.page.locator(".task-row")).to_have_count(0)
        self.page.locator("#task-date").fill("0001-01-01")
        self.page.locator("#task-time").evaluate("el => el.value = '25:99'")
        expect(self.page.locator("#task-time")).to_have_value("")
        self.page.locator("#task-form .add-button").click()
        self.assertEqual(self.saved(1)[0]["date"], "0001-01-01")
        self.add("second")
        self.saved(2)
        self.page.locator(".delete-button").first.click()
        self.page.locator(".delete-button").first.click()
        self.saved(0)
        self.page.locator("#toast button").click()
        self.saved(1)
        expect(self.page.locator(".task-title")).to_have_text("second")
        self.page.clock.fast_forward(5100)
        expect(self.page.locator(".task-title")).to_have_text("second")
        self.page.reload()
        expect(self.page.locator(".task-title")).to_have_text("second")

    def test_keyboard_focus_and_undo_expiry(self):
        self.open([task("a"), task("b")])
        checkbox = self.page.locator("[data-id=a] .task-check")
        checkbox.focus()
        self.page.keyboard.press("Space")
        expect(checkbox).to_be_checked()
        expect(checkbox).to_be_focused()
        self.page.keyboard.press("Tab")
        expect(self.page.locator("[data-id=a] .delete-button")).to_be_focused()
        self.page.keyboard.press("Enter")
        expect(self.page.locator("[data-id=b] .delete-button")).to_be_focused()
        self.saved(1)
        self.add("keep-undo-visible")
        self.saved(2)
        expect(self.page.locator("#toast button")).to_be_visible()
        self.page.locator("#calendar-open").click()
        expect(self.page.locator("#calendar-dialog #toast button")).to_be_visible()
        self.page.locator("#calendar-close").click()
        self.page.clock.fast_forward(5100)
        expect(self.page.locator("#toast")).to_be_hidden()
        self.page.reload()
        expect(self.page.locator("[data-id=a]")).to_have_count(0)


if __name__ == "__main__":
    print(f"Audit engine={BROWSER}, url={URL}", flush=True)
    unittest.main(verbosity=2)
