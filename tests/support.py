"""Shared browser selection for local, CI and deployed-site checks."""

import os
from pathlib import Path

BROWSER = os.environ.get("BROWSER", "chromium")


def launch(playwright):
    if BROWSER not in ("chromium", "firefox", "webkit"):
        raise ValueError(f"Unknown BROWSER: {BROWSER}")
    options = {"headless": True}
    if BROWSER == "chromium":
        path = os.environ.get("CHROMIUM_PATH")
        if path:
            options["executable_path"] = path
        options["args"] = ["--no-sandbox"]
    return getattr(playwright, BROWSER).launch(**options)


def watch_errors(page):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "console", lambda msg: errors.append(msg.text) if msg.type == "error" else None
    )
    page.on(
        "requestfailed", lambda request: errors.append(f"Request failed: {request.url}")
    )
    page.on(
        "response",
        lambda response: (
            errors.append(f"HTTP {response.status}: {response.url}")
            if response.status >= 400
            else None
        ),
    )
    return errors
