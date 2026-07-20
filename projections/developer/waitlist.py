"""Generated waitlist projection. Regenerate instead of editing."""

from __future__ import annotations

import argparse
import json
import re
from html import escape
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

PRODUCT_NAME = "dodai"
HEADLINE = "Keep product intent and delegated work aligned."
VALUE_PROPOSITION = (
    "Connect approved product intent, verification, executable behavior, and "
    "stakeholder meaning—without micromanaging technical methods."
)
CALL_TO_ACTION = "Join the waitlist"
HTML_LANGUAGE = "en"
STATUS = "Origin aligned"
EYEBROW = "Origin-driven development"
CARD_TITLE = "Build from intent."
CARD_TEXT = "Get early access to a calmer way of delegating software delivery."
EMAIL_LABEL = "Work email"
EMAIL_PLACEHOLDER = "you@company.com"
INVALID = "Enter a valid email address."
CREATED = "You're on the list. We'll be in touch."
DUPLICATE = "You're already on the list—your place is saved."
FOOTER = "One origin · Multiple projections"


def register(email: str, records_path: Path) -> bool:
    normalized = email.strip().lower()
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized) is None:
        raise ValueError(INVALID)
    records = json.loads(records_path.read_text()) if records_path.exists() else []
    if normalized in records:
        return False
    records.append(normalized)
    records_path.parent.mkdir(parents=True, exist_ok=True)
    records_path.write_text(json.dumps(records, indent=2) + "\n")
    return True


def render_page(message: str = "", kind: str = "") -> str:
    notice = ""
    if message:
        notice = (
            f'<p class="notice {escape(kind)}" role="status" aria-live="polite">'
            f"{escape(message)}</p>"
        )
    return f"""<!doctype html>
<html lang="{escape(HTML_LANGUAGE)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(PRODUCT_NAME)} — Early access</title>
  <style>
    :root {{ color-scheme: light; --ink: #14231d; --paper: #f4f0e6; --lime: #c9ff5b; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; min-height: 100vh; background: var(--paper); color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    body::before {{ content: ""; position: fixed; inset: 0; pointer-events: none;
      background: radial-gradient(circle at 82% 12%, #d9ff8a 0, transparent 30%),
        linear-gradient(120deg, transparent 55%, rgb(20 35 29 / 8%) 55.2%, transparent 55.5%); }}
    main {{ position: relative; width: min(1120px, calc(100% - 40px)); margin: 0 auto;
      min-height: 100vh; display: grid; grid-template-rows: auto 1fr auto; }}
    nav {{ display: flex; justify-content: space-between; align-items: center;
      padding: 28px 0; border-bottom: 1px solid rgb(20 35 29 / 22%); }}
    .brand {{ font-size: 1.15rem; font-weight: 850; letter-spacing: -.04em; }}
    .status {{ display: flex; gap: 8px; align-items: center; font-size: .78rem;
      text-transform: uppercase; letter-spacing: .13em; }}
    .status::before {{ content: ""; width: 9px; height: 9px; border-radius: 50%;
      background: #55b34c; box-shadow: 0 0 0 5px rgb(85 179 76 / 14%); }}
    .hero {{ display: grid; grid-template-columns: 1.35fr .65fr; gap: 72px;
      align-items: center; padding: 70px 0; }}
    .eyebrow {{ display: inline-flex; padding: 8px 12px; border: 1px solid currentColor;
      border-radius: 999px; font-size: .72rem; text-transform: uppercase;
      letter-spacing: .16em; font-weight: 750; }}
    h1 {{ max-width: 760px; margin: 24px 0; font-size: clamp(3.6rem, 8vw, 7.4rem);
      line-height: .88; letter-spacing: -.075em; font-weight: 880; }}
    .lede {{ max-width: 650px; font-size: clamp(1.05rem, 2vw, 1.35rem);
      line-height: 1.55; color: rgb(20 35 29 / 74%); }}
    .card {{ background: var(--ink); color: white; padding: 32px; border-radius: 4px;
      box-shadow: 18px 18px 0 var(--lime); transform: rotate(1.2deg); }}
    .card h2 {{ margin: 0 0 8px; font-size: 1.65rem; letter-spacing: -.04em; }}
    .card p {{ color: rgb(255 255 255 / 68%); line-height: 1.5; }}
    form {{ display: grid; gap: 12px; margin-top: 26px; }}
    label {{ font-size: .75rem; text-transform: uppercase; letter-spacing: .12em; }}
    input {{ width: 100%; border: 1px solid rgb(255 255 255 / 35%); background: transparent;
      color: white; padding: 15px 14px; border-radius: 2px; font: inherit; }}
    input:focus {{ outline: 3px solid var(--lime); outline-offset: 2px; }}
    button {{ border: 0; padding: 16px; background: var(--lime); color: var(--ink);
      font: inherit; font-weight: 850; cursor: pointer; border-radius: 2px; }}
    button:hover {{ filter: brightness(.94); transform: translateY(-1px); }}
    .notice {{ margin: 16px 0 0; padding: 12px; color: white !important;
      border-left: 3px solid var(--lime); background: rgb(255 255 255 / 10%); }}
    .notice.error {{ border-color: #ff806d; }}
    footer {{ display: flex; justify-content: space-between; padding: 22px 0;
      border-top: 1px solid rgb(20 35 29 / 22%); font-size: .8rem; }}
    @media (max-width: 780px) {{ .hero {{ grid-template-columns: 1fr; gap: 42px; }}
      h1 {{ font-size: clamp(3.2rem, 16vw, 5.2rem); }} .card {{ margin-right: 18px; }} }}
  </style>
</head>
<body>
  <main>
    <nav><span class="brand">{escape(PRODUCT_NAME)}</span>
      <span class="status">{escape(STATUS)}</span></nav>
    <section class="hero">
      <div><span class="eyebrow">{escape(EYEBROW)}</span>
        <h1>{escape(HEADLINE)}</h1><p class="lede">{escape(VALUE_PROPOSITION)}</p></div>
      <aside class="card"><h2>{escape(CARD_TITLE)}</h2>
        <p>{escape(CARD_TEXT)}</p>
        <form method="post" action="/"><label for="email">{escape(EMAIL_LABEL)}</label>
          <input id="email" name="email" type="email" placeholder="{escape(EMAIL_PLACEHOLDER)}"
            autocomplete="email" required><button type="submit">{escape(CALL_TO_ACTION)}</button>
        </form>{notice}</aside>
    </section>
    <footer><span>{escape(FOOTER)}</span><span>Generated from approved origin</span></footer>
  </main>
</body>
</html>"""


def create_application(records_path: Path):
    def application(environ, start_response):
        status = "200 OK"
        message = ""
        kind = "success"
        if environ.get("REQUEST_METHOD", "GET").upper() == "POST":
            length = int(environ.get("CONTENT_LENGTH") or 0)
            form = parse_qs(environ["wsgi.input"].read(length).decode("utf-8"))
            email = form.get("email", [""])[0]
            try:
                created = register(email, records_path)
            except ValueError as error:
                status, message, kind = "400 Bad Request", str(error), "error"
            else:
                if created:
                    status, message = "201 Created", CREATED
                else:
                    message = DUPLICATE
        body = render_page(message, kind).encode("utf-8")
        start_response(
            status,
            [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))],
        )
        return [body]

    return application


application = create_application(Path(".dodai/demo/registrations.json"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the generated dodai waitlist demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data", type=Path, default=Path(".dodai/demo/registrations.json"))
    args = parser.parse_args()
    url = f"http://{args.host}:{args.port}"
    print(f"dodai waitlist demo: {url}")
    with make_server(args.host, args.port, create_application(args.data)) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
