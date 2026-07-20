from __future__ import annotations

import json
import re
import textwrap
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

import yaml
from openai import OpenAI

from dodai.origin import load_origin, validate_origin

RENDERER_VERSION = "5"
DEFAULT_MODEL = "gpt-5.6"


@dataclass(frozen=True)
class ProjectionContent:
    product_name: str
    audience: str
    headline: str
    value_proposition: str
    call_to_action: str
    stakeholder_summary: str


class ContentProvider(Protocol):
    def derive(self, origin_text: str) -> ProjectionContent: ...


@dataclass(frozen=True)
class ProjectionResult:
    digest: str
    changed: bool
    files: list[str]


class OpenAIContentProvider:
    def __init__(self, model: str = DEFAULT_MODEL, client: OpenAI | None = None) -> None:
        self.model = model
        self.client = client

    def derive(self, origin_text: str) -> ProjectionContent:
        schema = {
            "type": "object",
            "properties": {
                field: {"type": "string"} for field in ProjectionContent.__dataclass_fields__
            },
            "required": list(ProjectionContent.__dataclass_fields__),
            "additionalProperties": False,
        }
        client = self.client or OpenAI()
        response = client.responses.create(
            model=self.model,
            reasoning={"effort": "medium"},
            instructions=(
                "Derive concise product content for the pinned minimal waitlist journey. "
                "Honor the origin vocabulary and outcomes. Do not introduce capabilities. "
                "Write in the primary human language used by the product intent."
            ),
            input=origin_text,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "projection_content",
                    "strict": True,
                    "schema": schema,
                }
            },
        )
        values = json.loads(response.output_text)
        return ProjectionContent(**values)


class SampleContentProvider:
    """Provides an inspectable keyless path for tests and judge evaluation."""

    def derive(self, origin_text: str) -> ProjectionContent:
        def source_value(key: str, default: str) -> str:
            match = re.search(rf"^\s*{re.escape(key)}:\s*(.+)$", origin_text, re.MULTILINE)
            if match is None:
                return default
            value = yaml.safe_load(match.group(1))
            return str(value) if value is not None else default

        product_name = source_value("product_name", source_value("origin", "Sample product"))
        audience = source_value("who", "People accountable for the declared outcome")
        outcome = source_value(
            "statement", "The person can complete the declared minimal product journey."
        )
        journey = source_value("journey", outcome)
        japanese = re.search(r"[\u3040-\u30ff\u3400-\u9fff]", f"{audience} {outcome} {journey}")
        return ProjectionContent(
            product_name=product_name,
            audience=audience,
            headline=outcome,
            value_proposition=journey,
            call_to_action="参加意思を残す" if japanese else "Join the waitlist",
            stakeholder_summary=f"{audience}: {journey}",
        )


class ProjectionEngine:
    def __init__(self, root: Path, provider: ContentProvider) -> None:
        self.root = root
        self.provider = provider

    def _source_and_digest(self) -> tuple[str, str, str, str]:
        origin = load_origin(self.root / "origin")
        report = validate_origin(origin)
        if report.errors or report.warnings:
            messages = report.errors + [warning.message for warning in report.warnings]
            raise ValueError("Origin validation failed: " + "; ".join(messages))
        pin_text = ""
        pin_directory = self.root / "pins"
        if pin_directory.exists():
            pin_text = "\n".join(
                path.read_text(encoding="utf-8") for path in sorted(pin_directory.glob("*.yaml"))
            )
        source = origin.source_text() + "\n# projection pins\n" + pin_text
        digest = sha256(f"{RENDERER_VERSION}\n{source}".encode()).hexdigest()
        origin_digest = sha256(origin.source_text().encode()).hexdigest()
        pin_digest = sha256(pin_text.encode()).hexdigest()
        return source, digest, origin_digest, pin_digest

    def _projection_kind(self) -> str:
        for path in sorted((self.root / "pins").glob("*.yaml")):
            value = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(value, dict) and "projection_kind" in value:
                return str(value["projection_kind"])
        return "waitlist"

    def project(self, *, refresh: bool = False) -> ProjectionResult:
        source, digest, origin_digest, pin_digest = self._source_and_digest()
        cache_path = self.root / ".dodai" / "cache" / f"{digest}.yaml"
        if cache_path.exists() and not refresh:
            content = ProjectionContent(**yaml.safe_load(cache_path.read_text(encoding="utf-8")))
        elif not refresh and (
            migrated := self._migrate_approved_content(origin_digest, pin_digest)
        ):
            content = migrated
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                yaml.safe_dump(asdict(content), sort_keys=True, allow_unicode=True),
                encoding="utf-8",
            )
        else:
            content = self.provider.derive(source)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                yaml.safe_dump(asdict(content), sort_keys=True, allow_unicode=True),
                encoding="utf-8",
            )

        rendered = _render(content, digest, origin_digest, pin_digest, self._projection_kind())
        projection_root = self.root / "projections"
        before = (
            {
                path.relative_to(projection_root).as_posix(): path.read_bytes()
                for path in projection_root.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
            }
            if projection_root.exists()
            else {}
        )
        for relative_path, body in rendered.items():
            destination = projection_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(body, encoding="utf-8")
        after = {path: body.encode() for path, body in rendered.items()}
        return ProjectionResult(digest=digest, changed=before != after, files=sorted(rendered))

    def _migrate_approved_content(
        self, origin_digest: str, pin_digest: str
    ) -> ProjectionContent | None:
        manifest_path = self.root / "projections/manifest.yaml"
        if not manifest_path.exists():
            return None
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            return None
        if (
            manifest.get("origin_source_digest") != origin_digest
            or manifest.get("pin_digest") != pin_digest
        ):
            return None
        previous = self.root / ".dodai/cache" / f"{manifest.get('origin_digest', '')}.yaml"
        if not previous.exists():
            return None
        return ProjectionContent(**yaml.safe_load(previous.read_text(encoding="utf-8")))


def _render(
    content: ProjectionContent,
    digest: str,
    origin_source_digest: str,
    pin_digest: str,
    projection_kind: str,
) -> dict[str, str]:
    if projection_kind == "brief":
        return _render_brief(content, digest, origin_source_digest, pin_digest)
    if projection_kind != "waitlist":
        raise ValueError(f"Unsupported projection kind: {projection_kind}")
    product_name = _python_assignment("PRODUCT_NAME", content.product_name)
    headline = _python_assignment("HEADLINE", content.headline)
    value_proposition = _python_assignment("VALUE_PROPOSITION", content.value_proposition)
    call_to_action = _python_assignment("CALL_TO_ACTION", content.call_to_action)
    japanese = (
        re.search(
            r"[\u3040-\u30ff\u3400-\u9fff]",
            " ".join((content.headline, content.value_proposition, content.call_to_action)),
        )
        is not None
    )
    labels = (
        {
            "html_language": "ja",
            "status": "原点と整合済み",
            "eyebrow": "原点駆動開発",
            "card_title": "意図から始める。",
            "card_text": "落ち着いてソフトウェア開発を委譲する体験へ参加してください。",
            "email_label": "メールアドレス",
            "email_placeholder": "you@example.com",
            "invalid": "有効なメールアドレスを入力してください。",
            "created": "参加を受け付けました。後ほどご連絡します。",
            "duplicate": "すでに参加済みです。登録は保持されています。",
            "footer": "1つの原点・複数の射影",
        }
        if japanese
        else {
            "html_language": "en",
            "status": "Origin aligned",
            "eyebrow": "Origin-driven development",
            "card_title": "Build from intent.",
            "card_text": "Get early access to a calmer way of delegating software delivery.",
            "email_label": "Work email",
            "email_placeholder": "you@company.com",
            "invalid": "Enter a valid email address.",
            "created": "You're on the list. We'll be in touch.",
            "duplicate": "You're already on the list—your place is saved.",
            "footer": "One origin · Multiple projections",
        }
    )
    label_assignments = "\n".join(
        _python_assignment(name.upper(), value) for name, value in labels.items()
    )
    app_template = '''"""Generated waitlist projection. Regenerate instead of editing."""

from __future__ import annotations

import argparse
import json
import re
from html import escape
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

__PRODUCT_NAME__
__HEADLINE__
__VALUE_PROPOSITION__
__CALL_TO_ACTION__
__LABEL_ASSIGNMENTS__


def register(email: str, records_path: Path) -> bool:
    normalized = email.strip().lower()
    if re.fullmatch(r"[^@\\s]+@[^@\\s]+\\.[^@\\s]+", normalized) is None:
        raise ValueError(INVALID)
    records = json.loads(records_path.read_text()) if records_path.exists() else []
    if normalized in records:
        return False
    records.append(normalized)
    records_path.parent.mkdir(parents=True, exist_ok=True)
    records_path.write_text(json.dumps(records, indent=2) + "\\n")
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
'''
    app = (
        app_template.replace("__PRODUCT_NAME__", product_name)
        .replace("__HEADLINE__", headline)
        .replace("__VALUE_PROPOSITION__", value_proposition)
        .replace("__CALL_TO_ACTION__", call_to_action)
        .replace("__LABEL_ASSIGNMENTS__", label_assignments)
    )
    test = """from html import escape
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode

import pytest
from waitlist import CREATED, DUPLICATE, HEADLINE, INVALID, create_application, register


def request(application, method: str = "GET", email: str = "") -> tuple[str, str]:
    payload = urlencode({"email": email}).encode() if method == "POST" else b""
    environ = {
        "REQUEST_METHOD": method,
        "CONTENT_LENGTH": str(len(payload)),
        "wsgi.input": BytesIO(payload),
    }
    response = {}

    def start_response(status, headers):
        response["status"] = status

    body = b"".join(application(environ, start_response)).decode()
    return response["status"], body


def test_registration_survives_a_new_call(tmp_path: Path) -> None:
    records = tmp_path / "registrations.json"
    assert register("Person@example.com", records) is True
    assert register("person@example.com", records) is False


def test_invalid_email_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=INVALID):
        register("not-an-email", tmp_path / "registrations.json")


def test_browser_journey_explains_registration_outcomes(tmp_path: Path) -> None:
    application = create_application(tmp_path / "registrations.json")

    status, page = request(application)
    assert status == "200 OK"
    assert HEADLINE in page

    status, page = request(application, "POST", "person@example.com")
    assert status == "201 Created"
    assert escape(CREATED) in page

    status, page = request(application, "POST", "person@example.com")
    assert status == "200 OK"
    assert escape(DUPLICATE) in page

    status, page = request(application, "POST", "not-an-email")
    assert status == "400 Bad Request"
    assert escape(INVALID) in page
"""
    brief = f"""# {content.product_name}

## Audience

{content.audience}

## Promise

**{content.headline}**

{content.value_proposition}

## Journey

A visitor understands the promise, chooses **{content.call_to_action}**, and a
valid registration remains available to later visits. Repeated registration is
recognized without creating a duplicate.

## Why this projection exists

{content.stakeholder_summary}
"""
    manifest = yaml.safe_dump(
        {
            "origin_digest": digest,
            "origin_source_digest": origin_source_digest,
            "pin_digest": pin_digest,
            "projection_kind": projection_kind,
            "renderer_version": RENDERER_VERSION,
            "files": [
                "developer/waitlist.py",
                "developer/test_waitlist.py",
                "stakeholder/brief.md",
            ],
        },
        sort_keys=False,
    )
    return {
        "developer/waitlist.py": app,
        "developer/test_waitlist.py": test,
        "stakeholder/brief.md": brief,
        "manifest.yaml": manifest,
    }


def _render_brief(
    content: ProjectionContent, digest: str, origin_source_digest: str, pin_digest: str
) -> dict[str, str]:
    product_name = _python_assignment("PRODUCT_NAME", content.product_name)
    headline = _python_assignment("HEADLINE", content.headline)
    value_proposition = _python_assignment("VALUE_PROPOSITION", content.value_proposition)
    experience = f'''"""Generated executable meaning projection. Regenerate instead of editing."""

{product_name}
{headline}
{value_proposition}


def describe() -> dict[str, str]:
    return {{
        "product_name": PRODUCT_NAME,
        "headline": HEADLINE,
        "value_proposition": VALUE_PROPOSITION,
    }}
'''
    test = """from experience import describe


def test_executable_meaning_is_complete() -> None:
    meaning = describe()
    assert all(meaning.values())
    assert set(meaning) == {"product_name", "headline", "value_proposition"}
"""
    brief = f"""# {content.product_name}

## Audience

{content.audience}

## Promise

**{content.headline}**

{content.value_proposition}

## Shared outcome

{content.stakeholder_summary}
"""
    files = ["developer/experience.py", "developer/test_experience.py", "stakeholder/brief.md"]
    manifest = yaml.safe_dump(
        {
            "origin_digest": digest,
            "origin_source_digest": origin_source_digest,
            "pin_digest": pin_digest,
            "projection_kind": "brief",
            "renderer_version": RENDERER_VERSION,
            "files": files,
        },
        sort_keys=False,
    )
    return {
        "developer/experience.py": experience,
        "developer/test_experience.py": test,
        "stakeholder/brief.md": brief,
        "manifest.yaml": manifest,
    }


def _python_assignment(name: str, value: str) -> str:
    encoded = json.dumps(value, ensure_ascii=False)
    if len(name) + len(encoded) + 3 <= 100:
        return f"{name} = {encoded}"
    chunks = textwrap.wrap(
        value,
        width=72,
        break_long_words=False,
        break_on_hyphens=False,
        drop_whitespace=False,
        replace_whitespace=False,
    )
    expression = "\n    + ".join(json.dumps(chunk, ensure_ascii=False) for chunk in chunks)
    return f"{name} = (\n    {expression}\n)"
