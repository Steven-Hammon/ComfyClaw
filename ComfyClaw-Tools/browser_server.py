from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent
SETTINGS_FILE = ROOT / "settings.json"

PLAYWRIGHT = None
BROWSER = None
CONTEXT = None
PAGE = None


INTERACTIVE_ELEMENTS_SCRIPT = """
() => {
    const items = [];
    let id = 0;
    const isVisible = (el) => {
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    };
    const cleanText = (t) => (t || "").trim().replace(/\\s+/g, " ").slice(0, 100);
    const getSelector = (el) => {
        if (el.id) return `#${el.id}`;
        if (el.name) return `[name="${el.name}"]`;
        if (el.getAttribute("aria-label")) return `[aria-label="${el.getAttribute("aria-label")}"]`;
        if (el.placeholder) return `[placeholder="${el.placeholder}"]`;
        const tag = el.tagName.toLowerCase();
        const text = (el.innerText || "").trim();
        if (text && text.length < 50) {
            if (tag === "button") return `button:has-text("${text}")`;
            if (tag === "a") return `a:has-text("${text}")`;
        }
        return null;
    };
    const nodes = document.querySelectorAll("a, button, input, textarea, select, [onclick], [role='button']");
    nodes.forEach(el => {
        if (!isVisible(el)) return;
        const selector = getSelector(el);
        if (!selector) return;
        items.push({ id: id++, tag: el.tagName.toLowerCase(), text: cleanText(el.innerText || el.value), type: el.type || null, selector: selector });
    });
    return items;
}
"""


def load_settings() -> dict[str, object]:
    data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))

    for key in {"BrowserTimeoutMs", "BrowserVisibleTextChars", "BrowserPort", "BrowserHeadless"}:
        if key not in data:
            raise ValueError(f"settings.json missing required key: {key}")

    for key in {"BrowserTimeoutMs", "BrowserVisibleTextChars", "BrowserPort"}:
        if not isinstance(data[key], int):
            raise ValueError(f"settings.json {key} must be an integer")

    if not isinstance(data["BrowserHeadless"], bool):
        raise ValueError("settings.json BrowserHeadless must be true or false")

    if data["BrowserTimeoutMs"] <= 0:
        raise ValueError("settings.json BrowserTimeoutMs must be greater than 0")
    if data["BrowserVisibleTextChars"] < 0:
        raise ValueError("settings.json BrowserVisibleTextChars must be 0 or greater")
    if data["BrowserPort"] <= 0:
        raise ValueError("settings.json BrowserPort must be greater than 0")

    return data


def resolve_output_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (ROOT / path).resolve()

    resolved.relative_to(ROOT)
    return resolved


def start_browser(settings: dict[str, object]) -> None:
    global PLAYWRIGHT, BROWSER, CONTEXT, PAGE

    PLAYWRIGHT = sync_playwright().start()
    BROWSER = PLAYWRIGHT.chromium.launch(headless=bool(settings["BrowserHeadless"]))
    CONTEXT = BROWSER.new_context(accept_downloads=True)
    PAGE = CONTEXT.new_page()
    PAGE.set_default_timeout(int(settings["BrowserTimeoutMs"]))


def close_browser() -> None:
    global PLAYWRIGHT, BROWSER, CONTEXT, PAGE

    for item in (PAGE, CONTEXT, BROWSER):
        if item is None:
            continue
        try:
            item.close()
        except Exception:
            pass

    if PLAYWRIGHT is not None:
        try:
            PLAYWRIGHT.stop()
        except Exception:
            pass

    PLAYWRIGHT = None
    BROWSER = None
    CONTEXT = None
    PAGE = None


def get_page_state(settings: dict[str, object]) -> dict[str, object]:
    visible_text = PAGE.evaluate("() => document.body ? document.body.innerText : ''")
    visible_text = visible_text[: int(settings["BrowserVisibleTextChars"])]
    interactive_elements = PAGE.evaluate(INTERACTIVE_ELEMENTS_SCRIPT)

    return {
        "status": "success",
        "url": PAGE.url,
        "title": PAGE.title(),
        "visible_text": visible_text,
        "interactive_elements": interactive_elements,
    }


def require_arg(args: dict[str, object], name: str) -> str:
    value = args.get(name)
    if value is None or value == "":
        raise ValueError(f"missing required argument {name}")
    return str(value)


def wait_for_page_ready(settings: dict[str, object]) -> None:
    timeout_ms = int(settings["BrowserTimeoutMs"])
    try:
        PAGE.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        PAGE.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception:
        pass


def handle_command(settings: dict[str, object], action: str, args: dict[str, object]) -> dict[str, object]:
    if action == "goto":
        PAGE.goto(require_arg(args, "url"), wait_until="domcontentloaded")
        wait_for_page_ready(settings)
        return get_page_state(settings)

    if action == "click":
        PAGE.locator(require_arg(args, "selector")).first.click()
        wait_for_page_ready(settings)
        return get_page_state(settings)

    if action == "type":
        PAGE.locator(require_arg(args, "selector")).first.fill(require_arg(args, "text"))
        return get_page_state(settings)

    if action == "press":
        PAGE.locator(require_arg(args, "selector")).first.press(require_arg(args, "key"))
        wait_for_page_ready(settings)
        return get_page_state(settings)

    if action == "state":
        return get_page_state(settings)

    if action == "screenshot":
        output_path = resolve_output_path(str(args.get("out") or "screenshot.png"))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        PAGE.screenshot(path=str(output_path))
        return {"status": "success", "saved_to": str(output_path)}

    if action == "end":
        close_browser()
        return {"status": "success", "message": "Browser server stopped"}

    raise ValueError(f"unknown action {action}")


def build_error_response(settings: dict[str, object], exc: Exception) -> dict[str, object]:
    error_response: dict[str, object] = {
        "status": "error",
        "error": str(exc),
    }

    try:
        state = get_page_state(settings)
        state["status"] = "error"
        state["error"] = str(exc)
        return state
    except Exception as state_exc:
        error_response["state_error"] = str(state_exc)
        return error_response


class BrowserCommandHandler(BaseHTTPRequestHandler):
    settings: dict[str, object] = {}

    def log_message(self, format: str, *args) -> None:
        return

    def send_json(self, status_code: int, data: dict[str, object]) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def do_POST(self) -> None:
        if self.path != "/command":
            self.send_json(404, {"status": "error", "error": "unknown path"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            action = str(payload.get("action", ""))
            args = payload.get("args", {})
            if not isinstance(args, dict):
                raise ValueError("args must be an object")

            response = handle_command(self.settings, action, args)
            self.send_json(200, response)

            if action == "end" and response.get("status") == "success":
                threading.Thread(target=self.server.shutdown, daemon=True).start()
        except Exception as exc:
            self.send_json(200, build_error_response(self.settings, exc))


def main() -> int:
    settings = load_settings()
    start_browser(settings)
    BrowserCommandHandler.settings = settings
    server = HTTPServer(("localhost", int(settings["BrowserPort"])), BrowserCommandHandler)

    print(f"Browser server running on port {settings['BrowserPort']}. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        close_browser()
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
