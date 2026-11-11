"""Automated WCAG A/AA checks of rendered views and interactive states.

This supplements keyboard and visual checks; axe cannot prove full accessibility.
"""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from support import launch, BROWSER

URL = os.environ.get("BASE_URL", "http://127.0.0.1:4173/")
AXE = Path(__file__).resolve().parents[1] / "node_modules/axe-core/axe.min.js"


def check(page, label):
    violations = page.evaluate(
        """async () => (await axe.run(document, {
        runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa']}
    })).violations.map(v => ({id: v.id, nodes: v.nodes.map(n => ({target: n.target, reason: n.failureSummary}))}))"""
    )
    assert not violations, f"{label}: {violations}"


with sync_playwright() as p:
    browser = launch(p)
    for width in (320, 768, 1440):
        for theme in ("light", "dark"):
            context = browser.new_context(
                viewport=dict(width=width, height=900),
                color_scheme=theme,
                reduced_motion="reduce",
            )
            page = context.new_page()
            page.goto(URL)
            page.add_script_tag(path=str(AXE))
            nav = page.locator(".bottom-nav" if width < 761 else ".desktop-nav")
            for view in ("today", "upcoming", "completed"):
                nav.locator(f"[data-view={view}]").click()
                check(page, f"{BROWSER} {width} {theme} {view}")
            page.locator("#calendar-open").click()
            check(page, f"{BROWSER} {width} {theme} calendar")
            page.locator("#calendar-tasks .delete-button").first.click()
            check(page, f"{BROWSER} {width} {theme} calendar undo")
            page.locator("#toast button").click()
            page.locator("#calendar-close").click()
            page.locator("#task-groups .delete-button").first.click()
            check(page, f"{BROWSER} {width} {theme} undo")
            print(
                f"PASS axe {BROWSER} {width} {theme}: three views, calendar, both undo states",
                flush=True,
            )
            context.close()
    browser.close()
