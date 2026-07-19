from __future__ import annotations

import importlib.util
import shutil
import tempfile
from collections.abc import Callable, Iterable
from html import escape
from pathlib import Path
from typing import Any, cast
from wsgiref.simple_server import make_server

import yaml

from dodai.outer_loop import evaluate_telemetry

StartResponse = Callable[[str, list[tuple[str, str]]], Any]
Application = Callable[[dict[str, Any], StartResponse], Iterable[bytes]]


def _mapping(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a mapping in {path}.")
    return value


def _projection_application(root: Path) -> Application:
    path = root / "projections/developer/waitlist.py"
    spec = importlib.util.spec_from_file_location("dodai_generated_waitlist", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load generated projection from {path}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    create_application = module.create_application
    return cast(Application, create_application(root / ".dodai/demo/registrations.json"))


def _guardrail_demonstration(root: Path) -> tuple[str, str]:
    with tempfile.TemporaryDirectory(prefix="dodai-showcase-") as directory:
        isolated = Path(directory)
        shutil.copytree(root / "origin", isolated / "origin")
        telemetry = root / "examples/telemetry/guardrail-breach.yaml"
        result = evaluate_telemetry(isolated, telemetry)
        if result.proposal_path is None:
            return result.reason, "No proposal was produced."
        proposal = _mapping(result.proposal_path)["proposed_test_specification"]
        action = result.action.replace("_", " ")
        return result.reason, f"{action}: {proposal['id']} — {proposal['then']}"


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


def _render_showcase(root: Path, outcome: tuple[str, str] | None = None) -> str:
    manifest = _mapping(root / "projections/manifest.yaml")
    cache_path = root / ".dodai/cache" / f"{manifest['origin_digest']}.yaml"
    semantic = _mapping(cache_path)
    origin_layers = sorted((root / "origin").glob("0*.yaml"))
    projection_files = manifest.get("files", [])
    developer_files = [path for path in projection_files if str(path).startswith("developer/")]
    result = ""
    if outcome:
        result = f"""
        <section class="result" id="result" aria-live="polite">
          <div><span class="result-label">Observed telemetry</span>
            <strong>{escape(outcome[0])}</strong></div>
          <div><span class="result-label">Dodai response</span>
            <strong>{escape(outcome[1])}</strong></div>
          <p>The demonstration ran in an isolated copy.
            The authoritative origin stayed unchanged.</p>
        </section>"""
    return f"""<!doctype html>
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
    <span class="verified">Repository aligned</span></header>
  <main>
    <section class="hero">
      <div><span class="kicker">Origin-driven development</span>
        <h1>From intent<br>to evidence.</h1>
        <p class="intro">One auditable origin becomes executable software, verification,
          and stakeholder meaning—without prescribing technical How.</p></div>
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
        <p>{escape(str(semantic["stakeholder_summary"]))}</p>
        <span class="metric">1 aligned brief ✓</span></article>
    </section>
    <section class="actions">
      <article class="action"><h2>Touch the projection</h2>
        <p>Open the generated waitlist, register, and observe persistent behavior.</p>
        <a class="button" href="/projection">Open generated product →</a></article>
      <article class="action"><h2>Break a guardrail</h2>
        <p>Feed slow regeneration telemetry into the outer learning loop.</p>
        <form method="post" action="/guardrail#result">
          <button type="submit">Run isolated scenario →</button></form></article>
    </section>
    {result}
  </main>
  <footer><span>Manage agents by outcomes, not methods.</span>
    <span>No API request · Local only</span></footer>
</body>
</html>"""


def create_showcase_application(root: Path) -> Application:
    root = root.resolve()
    projection = _projection_application(root)

    def application(environ: dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
        path = str(environ.get("PATH_INFO", "/"))
        if path == "/projection":
            return _serve_projection(projection, environ, start_response)
        outcome = None
        if path == "/guardrail" and environ.get("REQUEST_METHOD", "GET").upper() == "POST":
            outcome = _guardrail_demonstration(root)
        elif path != "/":
            body = b"Not found"
            start_response("404 Not Found", [("Content-Type", "text/plain")])
            return [body]
        body = _render_showcase(root, outcome).encode("utf-8")
        start_response(
            "200 OK",
            [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))],
        )
        return [body]

    return application


def serve_showcase(root: Path, host: str, port: int) -> None:
    url = f"http://{host}:{port}"
    print(f"dodai showcase: {url}")
    print("No OpenAI API request is made.")
    with make_server(host, port, create_showcase_application(root)) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShowcase stopped.")
