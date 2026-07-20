from __future__ import annotations

import importlib.util
import shutil
import tempfile
from collections.abc import Callable, Iterable
from html import escape
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

import yaml

from dodai.evolution import (
    LAYER_COLLECTIONS,
    CandidateRevision,
    approve_candidate,
    candidate_from_proposal,
    prepare_candidate,
)
from dodai.localization import japanese_catalog, select_language, translated_record
from dodai.outer_loop import evaluate_telemetry
from dodai.projection import ContentProvider, OpenAIContentProvider, SampleContentProvider

StartResponse = Callable[[str, list[tuple[str, str]]], Any]
Application = Callable[[dict[str, Any], StartResponse], Iterable[bytes]]
ProviderFactory = Callable[[], ContentProvider]


def _localize(html: str, language: str) -> str:
    if language == "en":
        return html
    for english, japanese in japanese_catalog()["ui"].items():
        html = html.replace(str(english), str(japanese))
    return html.replace('<html lang="en">', '<html lang="ja">')


def _origin_audit(root: Path, language: str) -> str:
    cards = []
    collections = ("terms", "stories", "criteria", "specifications")
    for path in sorted((root / "origin").glob("0*.yaml")):
        layer = _mapping(path)
        collection = next(name for name in collections if name in layer)
        for record in layer[collection]:
            record_id = str(record["id"])
            if language == "ja":
                meaning = translated_record(record_id)
            else:
                meaning = str(
                    record.get("definition")
                    or record.get("pain")
                    or record.get("statement")
                    or record.get("then")
                )
            cards.append(
                f'<article data-origin-id="{escape(record_id)}"><code>{escape(record_id)}</code>'
                f"<p>{escape(meaning)}</p></article>"
            )
    title = "意味の監査" if language == "ja" else "Meaning audit"
    return f'<section class="audit"><h2>{title}</h2>{"".join(cards)}</section>'


def _mapping(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a mapping in {path}.")
    return value


def _projection_application(root: Path) -> Application:
    manifest = _mapping(root / "projections/manifest.yaml")
    projection_kind = str(manifest.get("projection_kind", "waitlist"))
    filename = "experience.py" if projection_kind == "brief" else "waitlist.py"
    path = root / "projections/developer" / filename
    spec = importlib.util.spec_from_file_location("dodai_generated_waitlist", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load generated projection from {path}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if projection_kind == "brief":
        meaning = cast(dict[str, str], module.describe())

        def brief_application(
            environ: dict[str, Any], start_response: StartResponse
        ) -> Iterable[bytes]:
            body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width"><title>{escape(meaning["product_name"])}</title>
<style>body{{margin:0;background:#f5f1e7;color:#14231d;font-family:system-ui,sans-serif}}
main{{width:min(900px,calc(100% - 40px));margin:auto;padding:12vh 0}}
h1{{font-size:clamp(4rem,10vw,8rem);line-height:.88;letter-spacing:-.07em}}
p{{font-size:1.3rem;line-height:1.6;max-width:650px}}</style></head><body><main>
<small>EXECUTABLE MEANING PROJECTION</small><h1>{escape(meaning["headline"])}</h1>
<p>{escape(meaning["value_proposition"])}</p></main></body></html>""".encode()
            start_response(
                "200 OK",
                [
                    ("Content-Type", "text/html; charset=utf-8"),
                    ("Content-Length", str(len(body))),
                ],
            )
            return [body]

        return brief_application
    create_application = module.create_application
    return cast(Application, create_application(root / ".dodai/demo/registrations.json"))


def _guardrail_demonstration(root: Path) -> tuple[str, str, str | None]:
    with tempfile.TemporaryDirectory(prefix="dodai-showcase-") as directory:
        isolated = Path(directory)
        shutil.copytree(root / "origin", isolated / "origin")
        telemetry = root / "examples/telemetry/guardrail-breach.yaml"
        result = evaluate_telemetry(isolated, telemetry)
        if result.proposal_path is None:
            return result.reason, "No proposal was produced.", None
        proposal = _mapping(result.proposal_path)["proposed_test_specification"]
        candidate = candidate_from_proposal(root, result.proposal_path)
        action = result.action.replace("_", " ")
        return (
            result.reason,
            f"{action}: {proposal['id']} — {proposal['then']}",
            candidate.candidate_id if candidate.valid else None,
        )


def _serve_projection(
    projection: Application, environ: dict[str, Any], start_response: StartResponse
) -> Iterable[bytes]:
    delegated = dict(environ)
    delegated["PATH_INFO"] = "/"
    response: dict[str, Any] = {}

    def capture_response(status: str, headers: list[tuple[str, str]]) -> None:
        response["status"] = status
        response["headers"] = headers

    body = b"".join(projection(delegated, capture_response))
    body = body.replace(b'action="/"', b'action="/projection"')
    headers = [
        (name, str(len(body)) if name.lower() == "content-length" else value)
        for name, value in cast(list[tuple[str, str]], response["headers"])
    ]
    start_response(cast(str, response["status"]), headers)
    return [body]


def _render_showcase(
    root: Path,
    outcome: tuple[str, str, str | None] | None = None,
    *,
    language: str = "ja",
) -> str:
    manifest = _mapping(root / "projections/manifest.yaml")
    cache_path = root / ".dodai/cache" / f"{manifest['origin_digest']}.yaml"
    semantic = _mapping(cache_path)
    origin_layers = sorted((root / "origin").glob("0*.yaml"))
    projection_files = manifest.get("files", [])
    developer_files = [path for path in projection_files if str(path).startswith("developer/")]
    introduction = (
        japanese_catalog()["content"]["introduction"]
        if language == "ja"
        else "One auditable origin becomes executable software, verification, and stakeholder "
        "meaning—without prescribing technical How."
    )
    stakeholder_summary = (
        japanese_catalog()["content"]["stakeholder_summary"]
        if language == "ja"
        else str(semantic["stakeholder_summary"])
    )
    result = ""
    if outcome:
        adoption = ""
        if outcome[2]:
            adoption = f"""
            <form method="post" action="/candidate/approve">
              <input type="hidden" name="candidate_id" value="{outcome[2]}">
              <input type="hidden" name="lang" value="{language}">
              <button type="submit">Adopt as layer-four verification →</button>
            </form>"""
        result = f"""
        <section class="result" id="result" aria-live="polite">
          <div><span class="result-label">Observed telemetry</span>
            <strong>{escape(outcome[0])}</strong></div>
          <div><span class="result-label">Dodai response</span>
            <strong>{escape(outcome[1])}</strong></div>
          <p>The demonstration ran in an isolated copy.
            The authoritative origin stayed unchanged.</p>
          {adoption}
        </section>"""
    switch_language = "en" if language == "ja" else "ja"
    switch_label = "English" if language == "ja" else "日本語"
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>dodai — From intent to evidence</title>
  <style>
    :root {{ --ink: #14231d; --paper: #f5f1e7; --lime: #c9ff5b; --line: #b9b5aa; }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{ margin: 0; background: var(--paper); color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    header, main, footer {{ width: min(1180px, calc(100% - 40px)); margin: auto; }}
    header {{ display: flex; justify-content: space-between; align-items: center;
      padding: 24px 0; border-bottom: 1px solid var(--line); }}
    .brand {{ font-size: 1.2rem; font-weight: 900; letter-spacing: -.05em; }}
    .verified {{ display: flex; align-items: center; gap: 9px; font-size: .75rem;
      text-transform: uppercase; letter-spacing: .12em; }}
    .verified::before {{ content: ""; width: 9px; height: 9px; border-radius: 50%;
      background: #4cab48; box-shadow: 0 0 0 5px rgb(76 171 72 / 14%); }}
    .hero {{ display: grid; grid-template-columns: 1.2fr .8fr; gap: 70px;
      padding: 70px 0 60px; align-items: end; }}
    .kicker, .step, .result-label {{ font-size: .7rem; font-weight: 800;
      text-transform: uppercase; letter-spacing: .15em; }}
    h1 {{ margin: 16px 0 22px; font-size: clamp(4rem, 9vw, 8rem); line-height: .86;
      letter-spacing: -.08em; max-width: 850px; }}
    .intro {{ max-width: 560px; font-size: 1.2rem; line-height: 1.55; color: #53615b; }}
    .proof {{ background: var(--ink); color: white; padding: 28px;
      box-shadow: 14px 14px 0 var(--lime); }}
    .proof strong {{ display: block; font-size: 2.6rem; letter-spacing: -.06em; }}
    .proof span {{ color: #b6c0bb; }}
    .pipeline {{ display: grid; grid-template-columns: repeat(4, 1fr);
      border: 1px solid var(--line); }}
    .card {{ min-height: 270px; padding: 24px; border-right: 1px solid var(--line);
      display: flex; flex-direction: column; }}
    .card:last-child {{ border: 0; }}
    .card h2 {{ margin: 40px 0 12px; font-size: 1.5rem; letter-spacing: -.04em; }}
    .card p {{ color: #5c6863; line-height: 1.5; }}
    .metric {{ margin-top: auto; font-weight: 850; }}
    .arrow {{ color: #67920c; }}
    .actions {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; padding: 50px 0; }}
    .action {{ border: 1px solid var(--ink); padding: 30px; background: transparent;
      text-align: left; }}
    .action h2 {{ margin: 0 0 10px; font-size: 2rem; letter-spacing: -.05em; }}
    .action p {{ color: #59655f; min-height: 48px; }}
    a.button, button {{ display: inline-block; border: 0; background: var(--ink); color: white;
      padding: 14px 18px; font: inherit; font-weight: 800; text-decoration: none;
      cursor: pointer; }}
    button {{ background: var(--lime); color: var(--ink); }}
    .result {{ background: #e2ffc0; border: 1px solid var(--ink); padding: 28px;
      display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 50px; }}
    .result strong {{ display: block; margin-top: 9px; line-height: 1.5; }}
    .result p {{ grid-column: 1 / -1; margin: 0; color: #526049; }}
    footer {{ display: flex; justify-content: space-between; border-top: 1px solid var(--line);
      padding: 24px 0 36px; font-size: .8rem; }}
    @media (max-width: 820px) {{ .hero, .actions {{ grid-template-columns: 1fr; }}
      .pipeline {{ grid-template-columns: 1fr; }} .card {{ min-height: 190px;
      border-right: 0; border-bottom: 1px solid var(--line); }} .card h2 {{ margin-top: 24px; }}
      .result {{ grid-template-columns: 1fr; }} .result p {{ grid-column: auto; }} }}
  </style>
</head>
<body>
  <header><span class="brand">dodai / 土台</span>
    <span><a href="/workbench?lang={language}">Origin workbench</a> ·
      <a class="language" href="/?lang={switch_language}">{switch_label}</a> ·
      <span class="verified">Repository aligned</span></span></header>
  <main>
    <section class="hero">
      <div><span class="kicker">Origin-driven development</span>
        <h1>From intent<br>to evidence.</h1>
        <p class="intro">{escape(str(introduction))}</p></div>
      <aside class="proof"><span>Current origin</span>
        <strong>{escape(str(manifest["origin_digest"]))[:12]}</strong>
        <span>Renderer v{escape(str(manifest["renderer_version"]))}
          · stable regeneration</span></aside>
    </section>
    <section class="pipeline" aria-label="Projection lineage">
      <article class="card"><span class="step">01 / Human intent</span><h2>4 origin layers</h2>
        <p>Definitions, solution-free stories, falsifiable outcomes,
          and implementation-independent tests.</p>
        <span class="metric">{len(origin_layers)} audited files
          <span class="arrow">→</span></span></article>
      <article class="card"><span class="step">02 / Model judgment</span><h2>GPT-5.6</h2>
        <p>Derives shared product meaning once. The approved bundle is addressed
          by the origin digest.</p>
        <span class="metric">1 cached bundle <span class="arrow">→</span></span></article>
      <article class="card"><span class="step">03 / Deterministic</span>
        <h2>Developer projection</h2>
        <p>Executable waitlist behavior and tests generated from the same approved meaning.</p>
        <span class="metric">{len(developer_files)} executable files
          <span class="arrow">→</span></span></article>
      <article class="card"><span class="step">04 / Same meaning</span>
        <h2>Stakeholder projection</h2>
        <p>{escape(str(stakeholder_summary))}</p>
        <span class="metric">1 aligned brief ✓</span></article>
    </section>
    <section class="actions">
      <article class="action"><h2>Touch the projection</h2>
        <p>Open the generated waitlist, register, and observe persistent behavior.</p>
        <a class="button" href="/projection">Open generated product →</a></article>
      <article class="action"><h2>Break a guardrail</h2>
        <p>Feed slow regeneration telemetry into the outer learning loop.</p>
        <form method="post" action="/guardrail#result">
          <input type="hidden" name="lang" value="{language}">
          <button type="submit">Run isolated scenario →</button></form></article>
    </section>
    {result}
  </main>
  <footer><span>Manage agents by outcomes, not methods.</span>
    <span>No API request · Local only</span></footer>
</body>
</html>"""
    return _localize(html, language)


def _read_form(environ: dict[str, Any]) -> dict[str, str]:
    length = int(environ.get("CONTENT_LENGTH") or 0)
    payload = environ["wsgi.input"].read(length).decode("utf-8")
    return {key: values[0] for key, values in parse_qs(payload).items()}


def _render_workbench(
    root: Path,
    candidate: CandidateRevision | None = None,
    *,
    layer_file: str = "02-user-stories.yaml",
    message: str = "",
    history_path: Path | None = None,
    language: str = "ja",
) -> str:
    layer_file = candidate.layer_file if candidate else layer_file
    source = candidate.proposed_text if candidate else (root / "origin" / layer_file).read_text()
    layer_labels = {
        "01-definitions.yaml": "01 · Definitions",
        "02-user-stories.yaml": "02 · User stories",
        "03-acceptance-criteria.yaml": "03 · Acceptance criteria",
        "04-test-specifications.yaml": "04 · Test specifications",
    }
    layer_links = "".join(
        f'<a href="/workbench?layer={name}&amp;lang={language}">{label}</a>'
        for name, label in layer_labels.items()
    )
    impact = ""
    if candidate:
        records = "".join(f"<li>{escape(item)}</li>" for item in candidate.affected_records)
        projections = "".join(f"<li>{escape(item)}</li>" for item in candidate.affected_projections)
        issues = (
            candidate.errors
            + candidate.warnings
            + [f"Repeats disproven approach: {bet}" for bet in candidate.blocked_by_losing_records]
        )
        issue_html = "".join(f"<li>{escape(item)}</li>" for item in issues)
        controls = ""
        if candidate.valid:
            controls = f"""
            <form method="post" action="/candidate/approve">
              <input type="hidden" name="candidate_id" value="{candidate.candidate_id}">
              <input type="hidden" name="lang" value="{language}">
              <button type="submit">Approve and regenerate →</button>
            </form>"""
        issue_section = (
            f'<div class="issues"><h3>Cannot approve</h3><ul>{issue_html}</ul></div>'
            if issues
            else ""
        )
        impact = f"""
        <section class="impact"><h2>Candidate impact</h2>
          <div><h3>Origin records</h3><ul>{records}</ul></div>
          <div><h3>Active projections</h3><ul>{projections}</ul></div>
          {issue_section}
          {controls}
        </section>"""
    history = ""
    if history_path:
        history = f"""<section class="history"><h2>Change history</h2>
          <p>{escape(history_path.relative_to(root).as_posix())}</p></section>"""
    switch_language = "en" if language == "ja" else "ja"
    switch_label = "English" if language == "ja" else "日本語"
    audit = _origin_audit(root, language)
    editor = f"""<section class="editor"><aside class="layers"><strong>Four origin layers</strong>
{layer_links}</aside>
<form class="panel" method="post" action="/candidate">
<input type="hidden" name="layer_file" value="{escape(layer_file)}">
<input type="hidden" name="lang" value="{language}">
<textarea name="proposed_text" aria-label="Candidate origin text">{escape(source)}</textarea>
<p><button type="submit">Preview complete impact →</button></p></form></section>"""
    work_area = (
        f"{audit}<details><summary>Edit authoritative source</summary>{editor}</details>"
        if language == "ja"
        else f"{editor}{audit}"
    )
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>dodai — Origin workbench</title><style>
:root {{ --ink:#14231d; --paper:#f5f1e7; --lime:#c9ff5b; }} * {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--paper); color:var(--ink);
  font-family:Inter,system-ui,sans-serif; }}
main {{ width:min(1180px,calc(100% - 40px)); margin:auto; padding:32px 0 60px; }}
nav {{ display:flex; justify-content:space-between; border-bottom:1px solid #aaa;
  padding-bottom:22px; }}
h1 {{ font-size:clamp(3rem,7vw,6rem); letter-spacing:-.07em; line-height:.9; margin:60px 0 20px; }}
.lede {{ max-width:700px; color:#56635d; font-size:1.15rem; }}
.editor {{ display:grid; grid-template-columns:1fr 2fr; gap:24px; margin-top:42px; }}
.layers, .panel, .impact, .history {{ border:1px solid var(--ink); padding:24px;
  background:#faf7ef; }}
.layers strong {{ display:block; margin-bottom:18px; }}
.layers a {{ display:block; padding:10px 0; color:var(--ink); }}
textarea {{ width:100%; min-height:520px; background:#10221a; color:#eaffde; padding:20px;
  border:0; font:13px/1.55 ui-monospace,monospace; tab-size:2; }}
button {{ border:0; background:var(--lime); color:var(--ink); padding:15px 18px;
  font:inherit; font-weight:850; cursor:pointer; }}
.impact {{ margin-top:24px; display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
.impact h2, .impact form, .issues {{ grid-column:1/-1; }}
.message {{ background:var(--lime); padding:16px; }}
.audit {{ margin-top:24px; display:grid; grid-template-columns:repeat(2,1fr); gap:12px; }}
.audit h2 {{ grid-column:1/-1; }} .audit article {{ border-top:1px solid #aaa; padding:12px 0; }}
.audit p {{ margin:.45rem 0 0; line-height:1.55; }}
details {{ margin-top:28px; }} summary {{ cursor:pointer; font-weight:850; padding:16px 0; }}
@media(max-width:760px) {{ .editor,.impact {{ grid-template-columns:1fr; }}
  textarea {{ min-height:420px; }} .audit {{ grid-template-columns:1fr; }} }}
</style></head><body><main><nav><strong>dodai / origin workbench</strong>
<span><a href="/?lang={language}">Showcase</a> ·
<a href="/workbench?lang={switch_language}">{switch_label}</a></span></nav>
<h1>Change intent.<br>See consequences.</h1>
<p class="lede">The current origin remains authoritative until a complete candidate is valid
and explicitly approved. Approval regenerates every active projection as one governed change.</p>
{f'<p class="message">{escape(message)}</p>' if message else ""}
{work_area}{impact}{history}</main></body></html>"""
    return _localize(html, language)


def create_showcase_application(
    root: Path, *, provider_factory: ProviderFactory = OpenAIContentProvider
) -> Application:
    root = root.resolve()
    projection = _projection_application(root)

    def application(environ: dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
        path = str(environ.get("PATH_INFO", "/"))
        query = parse_qs(str(environ.get("QUERY_STRING", "")))
        language = select_language(query.get("lang", [None])[0])
        if path == "/projection":
            return _serve_projection(projection, environ, start_response)
        workbench = None
        workbench_status = "200 OK"
        if path == "/workbench" and environ.get("REQUEST_METHOD", "GET").upper() == "GET":
            selected_layer = query.get("layer", ["02-user-stories.yaml"])[0]
            if selected_layer not in LAYER_COLLECTIONS:
                selected_layer = "02-user-stories.yaml"
            workbench = _render_workbench(root, layer_file=selected_layer, language=language)
        elif path == "/candidate" and environ.get("REQUEST_METHOD") == "POST":
            form = _read_form(environ)
            language = select_language(form.get("lang"))
            candidate = prepare_candidate(root, form["layer_file"], form["proposed_text"])
            workbench = _render_workbench(root, candidate, language=language)
        elif path == "/candidate/approve" and environ.get("REQUEST_METHOD") == "POST":
            form = _read_form(environ)
            language = select_language(form.get("lang"))
            try:
                result = approve_candidate(
                    root, form["candidate_id"], provider_factory(), approved_by="local human"
                )
            except Exception:
                workbench_status = "422 Unprocessable Entity"
                workbench = _render_workbench(
                    root,
                    message="Approval failed; the authoritative origin is unchanged.",
                    language=language,
                )
            else:
                workbench = _render_workbench(
                    root,
                    message="Revision approved and every projection regenerated.",
                    history_path=result.history_path,
                    language=language,
                )
        if workbench is not None:
            body = workbench.encode("utf-8")
            start_response(
                workbench_status,
                [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))],
            )
            return [body]
        outcome = None
        if path == "/guardrail" and environ.get("REQUEST_METHOD", "GET").upper() == "POST":
            form = _read_form(environ)
            language = select_language(form.get("lang"))
            outcome = _guardrail_demonstration(root)
        elif path != "/":
            body = b"Not found"
            start_response("404 Not Found", [("Content-Type", "text/plain")])
            return [body]
        body = _render_showcase(root, outcome, language=language).encode("utf-8")
        start_response(
            "200 OK",
            [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))],
        )
        return [body]

    return application


def serve_showcase(root: Path, host: str, port: int, *, sample: bool = False) -> None:
    from dodai.portal import create_portal_application

    url = f"http://{host}:{port}"
    print(f"dodai showcase: {url}")
    if sample:
        print("Sample mode: no OpenAI API request is made.")
    else:
        print("GPT-5.6 is called at most once after explicit generation consent.")
    provider_factory: ProviderFactory = SampleContentProvider if sample else OpenAIContentProvider
    audit_application = create_showcase_application(root, provider_factory=provider_factory)
    application = create_portal_application(
        root, provider_factory=provider_factory, audit_application=audit_application
    )
    with make_server(host, port, application) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShowcase stopped.")
