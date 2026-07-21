from __future__ import annotations

# ruff: noqa: E501
import importlib.util
import mimetypes
import re
from collections.abc import Callable, Iterable
from hashlib import sha256
from html import escape
from pathlib import Path
from threading import Thread
from typing import Any, cast
from urllib.parse import parse_qs

import yaml

from dodai.delegation import (
    CodexCliRunner,
    DelegationExecutionError,
    DelegationRunner,
    collect_delegation_evidence,
    load_delegation_attempts,
    load_delegation_evidence,
    prepare_repository,
    write_delegation_evidence,
)
from dodai.evidence import diagnose_failure
from dodai.evolution import (
    approve_candidate,
    candidate_from_proposal,
    load_candidate,
    prepare_candidate,
    reject_candidate,
)
from dodai.learning import (
    load_interaction_evidence,
    origin_snapshot_digest,
    prepare_reverification_candidate,
    prepare_story_rediscovery_candidate,
    record_interaction_evidence,
)
from dodai.outer_loop import evaluate_telemetry
from dodai.product import (
    ProductBet,
    ProductStore,
    approve_verification,
    generation_plan,
    record_outcomes,
    record_problem,
    solution_terms,
    verify_generated_projection,
)
from dodai.projection import (
    ContentProvider,
    OpenAIContentProvider,
    ProjectionEngine,
    SampleContentProvider,
)

StartResponse = Callable[[str, list[tuple[str, str]]], Any]
Application = Callable[[dict[str, Any], StartResponse], Iterable[bytes]]
ProviderFactory = Callable[[], ContentProvider]
DelegationRunnerFactory = Callable[[], DelegationRunner]


def _form(environ: dict[str, Any]) -> dict[str, str]:
    length = int(environ.get("CONTENT_LENGTH") or 0)
    payload = environ["wsgi.input"].read(length).decode("utf-8")
    return {key: values[0] for key, values in parse_qs(payload).items()}


def _respond(start_response: StartResponse, body: str, status: str = "200 OK") -> Iterable[bytes]:
    encoded = body.encode("utf-8")
    start_response(
        status,
        [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(encoded)))],
    )
    return [encoded]


def _redirect(start_response: StartResponse, location: str) -> Iterable[bytes]:
    start_response("303 See Other", [("Location", location), ("Content-Length", "0")])
    return [b""]


def _layout(title: str, content: str) -> str:
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} · dodai</title>
<style>
:root{{--ink:#14231d;--paper:#f5f1e7;--lime:#c9ff5b;--muted:#607069;--line:#b9b5aa}}
*{{box-sizing:border-box}}html,body{{overflow-x:hidden}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,system-ui,sans-serif}}
header,main{{width:min(1120px,calc(100% - 36px));margin:auto}}header{{display:flex;justify-content:space-between;padding:22px 0;border-bottom:1px solid var(--line)}}
a{{color:var(--ink)}}.brand{{font-weight:900;font-size:1.2rem;text-decoration:none}}main{{padding:48px 0 80px}}
h1{{font-size:clamp(2.8rem,7vw,6rem);line-height:.92;letter-spacing:-.065em;margin:0 0 22px}}h2{{letter-spacing:-.04em}}
.lede{{font-size:1.18rem;line-height:1.65;color:var(--muted);max-width:720px}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:18px;margin-top:32px}}
.card,.panel{{border:1px solid var(--ink);padding:24px;background:#faf7ef}}.card h2{{margin-top:0}}.empty{{border:1px dashed var(--line);padding:42px;margin-top:32px}}
.promise{{display:grid;grid-template-columns:repeat(3,1fr);border:1px solid var(--ink);margin:28px 0 34px;background:#faf7ef}}
.promise article{{padding:24px;border-right:1px solid var(--line)}}.promise article:last-child{{border-right:0}}
.promise strong{{display:block;font-size:1.15rem;margin:8px 0}}.number{{font-size:.78rem;font-weight:900;color:var(--muted)}}
.check-list{{display:grid;gap:12px;margin:24px 0}}.check{{display:grid;grid-template-columns:42px 1fr;gap:14px;align-items:start;border:1px solid var(--line);padding:18px;background:white}}
.check-mark{{display:grid;place-items:center;width:36px;height:36px;border-radius:50%;background:var(--lime);font-weight:900}}.check h3{{margin:0 0 5px}}.check p{{margin:0;color:var(--muted);line-height:1.55}}
details{{margin-top:22px;border-top:1px solid var(--line);padding-top:18px}}summary{{cursor:pointer;font-weight:800}}
label{{display:block;font-weight:800;margin:18px 0 7px}}input,textarea,select{{width:100%;padding:13px;border:1px solid var(--line);background:white;font:inherit}}
textarea{{min-height:110px}}button,.button{{display:inline-block;border:0;background:var(--ink);color:white;padding:14px 18px;font:inherit;font-weight:850;text-decoration:none;cursor:pointer}}
.primary{{background:var(--lime);color:var(--ink)}}.actions{{display:flex;gap:10px;flex-wrap:wrap;margin-top:24px}}.notice{{background:#e5ffc2;border:1px solid var(--ink);padding:16px;margin:20px 0}}
.error{{background:#ffe0d8}}.steps{{display:flex;gap:8px;flex-wrap:wrap;margin:28px 0}}.step{{border:1px solid var(--line);padding:8px 11px;font-size:.78rem}}.step.current{{background:var(--ink);color:white}}
.meta{{color:var(--muted);font-size:.9rem}}.metric{{font-size:2rem;font-weight:900}}dl{{display:grid;grid-template-columns:180px 1fr;gap:10px}}dt{{font-weight:850}}dd{{margin:0}}code{{font-size:.82rem;overflow-wrap:anywhere}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}
iframe{{width:100%;height:650px;border:1px solid var(--ink);background:white}}.history li{{margin:9px 0}}
@media(max-width:760px){{.grid,.promise{{grid-template-columns:1fr}}.promise article{{border-right:0;border-bottom:1px solid var(--line)}}.promise article:last-child{{border-bottom:0}}dl{{grid-template-columns:1fr}}}}
</style></head><body><header><a class="brand" href="/">dodai / 土台</a><nav><a href="/proof">仕組みを見る</a> · <a href="/workbench">監査モード</a></nav></header><main>{content}</main></body></html>"""


STAGES = (
    ("problem", "課題"),
    ("outcomes", "成果"),
    ("verification", "検証"),
    ("generation", "生成"),
    ("ready", "利用・学習"),
)
STAGE_LABELS = {
    "problem": ("課題を整理中", "誰が何に困っているかを言葉にする"),
    "outcomes": ("成功を整理中", "成功と利用者の体験を書く"),
    "verification": ("確かめ方を確認中", "Dodaiの確認方法を見る"),
    "generation": ("生成を承認待ち", "API回数と費用上限を確認する"),
    "generating": ("3つの成果を作成中", "プロダクト・テスト・説明資料を作る"),
    "ready": ("利用・学習", "生成物を試し、変更または学習する"),
}


def _steps(stage: str) -> str:
    current = next((index for index, item in enumerate(STAGES) if item[0] == stage), 4)
    return (
        '<div class="steps">'
        + "".join(
            f'<span class="step {"current" if index == current else ""}">{index + 1}. {label}</span>'
            for index, (_, label) in enumerate(STAGES)
        )
        + "</div>"
    )


def _intent(bet: ProductBet) -> str:
    if not bet.actor or not bet.pain or not bet.outcome:
        return ""
    return (
        '<section class="intent"><span class="number">この開発が解決すること</span>'
        f'<div class="grid"><div><strong>誰</strong><p>{escape(bet.actor)}</p></div>'
        f"<div><strong>困りごと</strong><p>{escape(bet.pain)}</p></div>"
        f"<div><strong>成功</strong><p>{escape(bet.outcome)}</p></div></div></section>"
    )


def _home(store: ProductStore, error: str = "") -> str:
    projects = store.list()
    cards = "".join(
        f'<article class="card"><p class="meta">{escape(STAGE_LABELS[bet.stage][0])}</p><h2>{escape(bet.name)}</h2>'
        f"<p>{escape(bet.actor or '課題の入力を待っています')}</p>"
        f"<p><strong>次:</strong> {escape(STAGE_LABELS[bet.stage][1])}</p>"
        f'<a class="button" href="/projects/{bet.project_id}">続きから始める →</a></article>'
        for bet in projects
    )
    listing = (
        f'<section class="grid">{cards}</section>'
        if cards
        else (
            '<section class="empty"><h2>まだプロダクトはありません</h2>'
            "<p>技術や画面を決める前に、誰のどんな課題を解くかから始めます。</p></section>"
        )
    )
    return _layout(
        "プロダクト",
        "<h1>AIへ開発を任せても、事業の意図を見失わない。</h1>"
        '<p class="lede">Dodaiは、AIへ実装を委譲するPM・エンジニアのための開発基盤です。'
        "誰の何を解決し、どうなれば成功かを正本にして、Codexへの実装委譲から証拠回収までをつなぎ、コード・テスト・説明のずれを防ぎます。</p>"
        '<section class="promise"><article><span class="number">01 / あなたが決める</span><strong>事業の意図</strong><span>誰の困りごとを、どう良くしたいか</span></article>'
        '<article><span class="number">02 / AIへ委譲する</span><strong>検証と実装</strong><span>技術的な作り方はDodaiが引き受ける</span></article>'
        '<article><span class="number">03 / 証拠で判断する</span><strong>実リポジトリの委譲結果</strong><span>変更内容・触れるプロダクト・テスト結果・説明資料</span></article></section>'
        '<section class="panel"><span class="number">Dodaiが返すもの</span>'
        "<h2>何を作ったかではなく、なぜ正しいと言えるか。</h2>"
        "<p>Codexが案件専用リポジトリへ作ったすべての成果を、元のユーザーストーリー・成功条件・確かめ方へ結び付けます。"
        "失敗時は、課題の見立て・確かめ方・生成結果のどこを見直すべきか切り分けます。</p></section>"
        + (f'<p class="notice error">{escape(error)}</p>' if error else "")
        + '<form class="panel" method="post" action="/projects"><label for="name">新しいプロダクト名</label>'
        '<input id="name" name="name" placeholder="例: 地域イベントの待機リスト" required>'
        '<div class="actions"><button class="primary" type="submit">課題から始める →</button></div></form>'
        + listing,
    )


def _problem(bet: ProductBet) -> str:
    recovery = ""
    if bet.pending_solution:
        recovery = (
            f'<div class="notice error"><strong>Howを検出しました: {escape(bet.pending_solution)}</strong>'
            f'<p>{escape(bet.error)}</p></div><label for="intended_outcome">その方法で実現したい成果</label>'
            '<textarea id="intended_outcome" name="intended_outcome" required></textarea>'
        )
    return _layout(
        bet.name,
        f'<p class="meta">{escape(bet.name)}</p><h1>誰の、どんな痛み？</h1>{_steps("problem")}'
        '<p class="lede">作りたい機能ではなく、今起きている困りごとを教えてください。Howが混ざった場合は、意図へ戻す質問をします。</p>'
        f"{f'<p class="notice error">{escape(bet.error)}</p>' if bet.error and not bet.pending_solution else ''}"
        f'<form class="panel" method="post" action="/projects/{bet.project_id}/problem">'
        '<label for="actor">困っている人</label>'
        f'<input id="actor" name="actor" value="{escape(bet.actor)}" placeholder="例: AIへ実装を委譲するPM" required>'
        '<label for="pain">現在起きている困りごと</label>'
        '<textarea id="pain" name="pain" placeholder="例: 仕様とコードがずれ、何が正しいか分からない" required></textarea>'
        f'{recovery}<div class="actions"><button class="primary">意図を整理する →</button></div></form>',
    )


def _outcomes(bet: ProductBet) -> str:
    return _layout(
        bet.name,
        f'<p class="meta">{escape(bet.name)}</p><h1>成功した状態を描く。</h1>{_steps("outcomes")}'
        f'<div class="notice"><strong>{escape(bet.actor)}</strong><p>{escape(bet.pain)}</p></div>'
        + (f'<p class="notice error">{escape(bet.error)}</p>' if bet.error else "")
        + '<form class="panel" method="post" action="/projects/'
        + bet.project_id
        + '/outcomes">'
        '<p class="lede">この2つをもとに、Dodaiが確認方法を提案します。技術や運用値を決める必要はありません。</p>'
        '<label for="outcome">利用者がどうなれば「良くなった」と言える？</label>'
        '<textarea id="outcome" name="outcome" placeholder="例: 関心のあるイベントへ参加意思を残せる" required></textarea>'
        '<label for="journey">利用者は最初に何をして、最後にどうなる？</label>'
        '<textarea id="journey" name="journey" placeholder="例: 開催情報を見る → 参加を選ぶ → 参加済みだと確認できる" required></textarea>'
        "<details><summary>言葉の意味を補足する（任意）</summary><p>このプロダクトだけで特別な意味を持つ言葉があれば補足できます。空のままで構いません。</p>"
        '<div class="grid"><div><label for="term_name">補足したい言葉</label>'
        '<input id="term_name" name="term_name" placeholder="例: 参加意思"></div>'
        '<div><label for="term_definition">ここでの意味</label>'
        '<input id="term_definition" name="term_definition" placeholder="例: イベントへの参加を希望している状態"></div></div></details>'
        '<div class="actions"><button class="primary">Dodaiの確認方法を見る →</button></div></form>',
    )


def _verification(store: ProductStore, bet: ProductBet) -> str:
    checks = (
        ("利用者の成功", f"実際の体験を通して「{bet.outcome}」を確認します。"),
        (
            "生成した成果の品質",
            "動く成果・テスト・説明が同じ意図を表し、実用範囲で作れることを確認します。",
        ),
        (
            "行き詰まりの検知",
            "改善を繰り返しても一致しない場合は、別の方式を選ぶべき状態として記録します。",
        ),
    )
    rows = "".join(
        f'<article class="check"><span class="check-mark">✓</span><div><h3>{escape(title)}</h3><p>{escape(description)}</p></div></article>'
        for title, description in checks
    )
    context = (
        f"<p><strong>{escape(bet.term_name)}</strong> — {escape(bet.term_definition)}</p>"
        if bet.term_name and bet.term_definition
        else ""
    )
    return _layout(
        bet.name,
        f'<p class="meta">{escape(bet.name)}</p><h1>作る前に、確かめ方を合わせる。</h1>{_steps("verification")}{_intent(bet)}'
        '<p class="lede">あなたは「何を良くしたいか」を決めました。Dodaiは、完成後に何を確かめれば正しいと言えるかを提案します。</p>'
        '<section class="panel"><span class="number">01 / あなたが決めたこと</span><h2>課題と成功</h2><dl>'
        f"<dt>誰</dt><dd>{escape(bet.actor)}</dd><dt>痛み</dt><dd>{escape(bet.pain)}</dd>"
        f"<dt>成功</dt><dd>{escape(bet.outcome)}</dd><dt>体験</dt><dd>{escape(bet.journey)}</dd></dl>{context}</section>"
        f'<section class="panel"><span class="number">02 / Dodaiが確かめること</span><h2>完成後のチェック</h2><div class="check-list">{rows}</div>'
        '<p class="meta">品質や停止判断に必要な運用条件は、Dodaiが管理します。</p></section>'
        '<section class="panel"><span class="number">03 / 承認すると始まること</span><h2>触れる成果を作る準備</h2>'
        "<p>次の画面でAPI利用と費用を確認したあと、触れるプロダクト・テスト結果・説明資料をまとめて生成します。</p></section>"
        f'<div class="actions"><form method="post" action="/projects/{bet.project_id}/verification">'
        '<button class="primary">この確かめ方で進む →</button></form>'
        f'<form method="post" action="/projects/{bet.project_id}/back/outcomes"><button>成果を修正する</button></form></div>',
    )


def _generation(store: ProductStore, bet: ProductBet, *, uses_external_model: bool) -> str:
    plan = generation_plan(store, bet.project_id, uses_external_model=uses_external_model)
    notice = f'<p class="notice error">{escape(bet.error)}</p>' if bet.error else ""
    source_message = (
        "承認済みキャッシュを再利用"
        if plan.cache_hit
        else (
            "GPT-5.6が意味を一度だけ導出"
            if uses_external_model
            else "鍵なしサンプルが原点から意味を導出（API利用なし）"
        )
    )
    consent_message = (
        "この計画で外部モデル利用と生成を承認する"
        if uses_external_model and not plan.cache_hit
        else "この計画で生成を承認する"
    )
    return _layout(
        bet.name,
        f'<p class="meta">{escape(bet.name)}</p><h1>この内容から、3つの成果を作ります。</h1>{_steps("generation")}{_intent(bet)}{notice}'
        '<p class="lede">開始すると、同じ課題と成功条件から、実際に触れるものと判断材料をまとめて作ります。</p>'
        '<section class="promise"><article><span class="number">01</span><strong>触れるプロダクト</strong><span>利用者の体験をその場で試せます</span></article>'
        '<article><span class="number">02</span><strong>テスト結果</strong><span>期待した振る舞いか確認できます</span></article>'
        '<article><span class="number">03</span><strong>関係者向けの説明資料</strong><span>同じ意図を共有できます</span></article></section>'
        '<section class="grid"><article class="card"><p class="meta">最大APIリクエスト</p>'
        f'<div class="metric">{plan.maximum_requests}回</div><p>{source_message}</p></article>'
        '<article class="card"><p class="meta">変動費の上限</p>'
        f'<div class="metric">${plan.maximum_cost_usd:.2f}</div><p>実際の請求額ではなく、この生成で許可する上限です。</p></article></section>'
        '<section class="panel"><h2>開始前の確認</h2><p>ボタンを押すまで生成は始まりません。完了後は、3つの成果を同じ画面で確認できます。</p>'
        f'<form method="post" action="/projects/{bet.project_id}/generate"><label>'
        f'<input style="width:auto" type="checkbox" name="consent" value="yes" required> {consent_message}</label>'
        '<div class="actions"><button class="primary">生成を開始する →</button></div></form>'
        '<div class="actions">'
        f'<form method="post" action="/projects/{bet.project_id}/back/verification"><button>検証へ戻る</button></form></div></section>',
    )


def _generating(bet: ProductBet, *, uses_external_model: bool) -> str:
    generation_source = (
        "GPT-5.6による共有意味の導出または承認済みキャッシュの再利用後"
        if uses_external_model
        else "鍵なしサンプルによる共有意味の導出後（API利用なし）"
    )
    return _layout(
        bet.name,
        '<meta http-equiv="refresh" content="1">'
        f'<p class="meta">{escape(bet.name)}</p><h1>3つの成果を作っています。</h1>'
        f'{_steps("generation")}{_intent(bet)}<section class="panel"><h2>現在の処理</h2>'
        f"<p>{generation_source}、"
        "触れるプロダクト・テスト結果・関係者向け説明をまとめて生成しています。</p>"
        "<p>この画面を閉じても判断と進捗は保存されます。後から同じ案件を開いて再開できます。</p></section>",
    )


def _history(workspace: Path) -> str:
    paths: list[Path] = []
    for name in ("history", "decisions"):
        directory = workspace / ".dodai" / name
        if directory.exists():
            paths.extend(directory.glob("*.yaml"))
    if not paths:
        return "<p>まだ承認済み変更はありません。</p>"
    rendered = []
    for path in sorted(paths):
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        if "action" in value:
            rendered.append(
                f"<li><strong>{escape(str(value['action']))}</strong> — "
                f"{escape(str(value.get('reason', '')))}</li>"
            )
        else:
            rendered.append(
                f"<li><strong>{escape(str(value.get('layer_file', '原点変更')))}</strong> — "
                f"承認者 {escape(str(value.get('approval', {}).get('actor', 'human')))} / "
                f"射影 {escape(str(value.get('after', {}).get('projection_digest', '')))[:12]}</li>"
            )
    items = "".join(rendered)
    return f'<ul class="history">{items}</ul>'


def _delegation_origin_summary(bet: ProductBet) -> str:
    return (
        f"# Approved product intent\n\n"
        f"Actor: {bet.actor}\n\nPain: {bet.pain}\n\nOutcome: {bet.outcome}\n\n"
        f"Minimal journey: {bet.journey}\n"
    )


def _delegation_prompt(bet: ProductBet) -> str:
    feedback = (
        f"\nPrior-result evidence to address: {bet.delegation_feedback}\n"
        if bet.delegation_feedback
        else ""
    )
    return (
        "Implement one complete, usable vertical journey that satisfies ORIGIN.md. "
        "Choose the technical approach yourself. Add automated verification and a concise "
        "STAKEHOLDER.md that explains the result without implementation detail. Deliver the "
        "immediately usable product as a self-contained static web experience rooted at "
        "product/index.html. Run the "
        "verification before finishing. Do not commit changes. Return only the required "
        "structured result."
        f"{feedback}"
    )


def _delegation_plan(bet: ProductBet, message: str = "") -> str:
    notice = f'<p class="notice">{escape(message)}</p>' if message else ""
    return _layout(
        bet.name,
        f'<p class="meta">{escape(bet.name)}</p><h1>実装をCodexへ委譲する。</h1>{_intent(bet)}{notice}'
        '<p class="lede">承認済みの事業意図を渡し、技術的な作り方はCodexへ任せます。承認済み意図は変更しません。</p>'
        '<section class="grid"><article class="card"><span class="number">作業範囲</span>'
        "<h2>Dodai管理下の隔離リポジトリ</h2><p>この案件専用の領域だけを書き換えます。Dodai本体や他の案件には触れません。</p></article>"
        '<article class="card"><span class="number">最大試行回数</span><div class="metric">1回</div>'
        "<p>この承認では1回だけ開始します。同時送信や再読み込みで重複実行しません。</p></article></section>"
        '<section class="panel"><span class="number">完了後に受け取る証拠</span>'
        "<h2>変更ファイル・検証結果・関係者向け説明</h2>"
        "<p>すべてを同じStory・AC・Test specificationへ接続して表示します。Codexの生ログやSession IDは保存しません。</p>"
        f'<form method="post" action="/projects/{bet.project_id}/delegate"><label>'
        '<input style="width:auto" type="checkbox" name="consent" value="yes" required> '
        "この事業意図と隔離範囲で、Codexへの1回の委譲を承認する</label>"
        '<div class="actions"><button class="primary">Codexへ委譲する →</button>'
        f'<a class="button" href="/projects/{bet.project_id}">判断画面へ戻る</a></div></form></section>',
    )


def _delegation_result(store: ProductStore, bet: ProductBet) -> str:
    workspace = store.workspace(bet.project_id)
    repository = workspace / "delegation" / "repository"
    evidence = load_delegation_evidence(workspace)

    def preview(path: Path) -> str:
        if path.is_symlink() or not path.resolve().is_relative_to(repository.resolve()):
            return "隔離リポジトリ外を参照する成果物は表示できません。"
        content = path.read_bytes()
        if b"\0" in content:
            return "Binary artifact. Inspect it in the isolated repository."
        return content.decode("utf-8", errors="replace")[:4000]

    def change_label(change: object) -> str:
        labels = {
            "??": "新規",
            "A": "追加",
            "M": "変更",
            "D": "削除",
            "R": "移動",
        }
        value = str(change).strip()
        return labels.get(value, value)

    artifacts = "".join(
        "<li><details><summary>"
        f'<code>{escape(str(item["path"]))}</code> <span class="meta">{escape(change_label(item["change"]))}</span>'
        "</summary><pre>"
        f"{escape(preview(repository / str(item['path'])))}"
        "</pre></details></li>"
        for item in evidence["artifacts"]
    )
    origin_evidence = evidence["origin_evidence"]
    accepted = (
        '<p class="notice"><strong>採用済み</strong> この委譲結果を採用しました。</p>'
        if bet.delegation_accepted
        else ""
    )
    attempts = load_delegation_attempts(workspace)
    comparison = ""
    if len(attempts) >= 2:
        previous, current = attempts[-2:]
        observations = []
        for path in sorted((workspace / ".dodai/interactions").glob("*.yaml")):
            value = load_interaction_evidence(path)
            if int(value.get("attempt", 0)) == int(previous["attempt"]):
                observations.append(escape(str(value.get("observation", ""))))
        changed = {str(item["path"]): str(item["digest"]) for item in previous["artifacts"]} != {
            str(item["path"]): str(item["digest"]) for item in current["artifacts"]
        }
        comparison = (
            '<section class="notice"><strong>'
            f"試行{previous['attempt']} → 試行{current['attempt']}</strong>"
            f"<p>成果物: {len(previous['artifacts'])}件 → {len(current['artifacts'])}件 "
            f"（内容は{'変化あり' if changed else '同一'}）</p>"
            f"<p>前回の操作証拠: {' / '.join(observations) or '記録なし'}</p></section>"
        )
        if bet.presentation_repair_status == "completed":
            comparison += (
                '<section class="notice"><strong>動作修復: 検証PASS</strong>'
                "<p>事業成果: 未確認 — 修復後の成果を操作し、新しい事実を記録してください。</p></section>"
            )
    learning_form = (
        '<section class="panel"><span class="number">触って分かったこと</span>'
        "<h3>この成果で、本当に前へ進めましたか？</h3>"
        "<p>専門用語や失敗した層を選ぶ必要はありません。事実だけを教えてください。</p>"
        f'<form method="post" action="/projects/{bet.project_id}/learning/evaluate">'
        '<label>困りごとは今もありましたか？</label><select name="pain_present" required>'
        '<option value="yes">はい</option><option value="no">いいえ</option><option value="unsure">まだ分からない</option></select>'
        '<label>操作は意図した通り完了しましたか？</label><select name="behavior_worked" required>'
        '<option value="yes">はい</option><option value="no">いいえ</option><option value="unsure">まだ分からない</option></select>'
        '<label>望んだ結果になりましたか？</label><select name="outcome_achieved" required>'
        '<option value="yes">はい</option><option value="no">いいえ</option><option value="unsure">まだ分からない</option></select>'
        '<label>実際に見た・起きた事実</label><textarea name="observation" required></textarea>'
        "<button>結果を記録して、次を判断する →</button></form></section>"
    )
    return (
        f'<section class="panel"><span class="number">実リポジトリへの試行 {bet.delegation_attempts}</span>'
        "<h2>Codexの委譲結果</h2>"
        f"<p>{escape(str(evidence['summary']))}</p>{accepted}{comparison}"
        '<section class="notice"><strong>実際に触って判断する</strong><p>Codexが作った成果を隔離された表示領域で操作できます。</p>'
        f'<a class="button primary" href="/projects/{bet.project_id}/delegated-product/" target="_blank">委譲されたプロダクトを開く →</a></section>'
        f'<iframe sandbox="allow-scripts allow-forms" title="委譲されたプロダクト" src="/projects/{bet.project_id}/delegated-product/"></iframe>'
        f'<div class="notice"><strong>検証: {"PASS" if evidence["verification_status"] == "passed" else "FAIL"}</strong>'
        f"<p>{escape(str(evidence['verification_summary']))}</p>"
        f"<p>成功した検証コマンド: {len(evidence.get('verification_commands', []))}件</p></div>"
        f'<div class="grid"><div><h3>変更ファイル</h3><ul>{artifacts}</ul></div>'
        f"<div><h3>関係者向け説明</h3><p>{escape(str(evidence['stakeholder_summary']))}</p></div></div>"
        "<h3>原点への根拠</h3><p>"
        f"<code>{escape(str(origin_evidence['story']))}</code> → "
        f"<code>{escape(str(origin_evidence['criterion']))}</code> → "
        f"<code>{escape(str(origin_evidence['specification']))}</code></p>"
        + (
            ""
            if bet.delegation_accepted
            else (
                f'<div class="actions"><form method="post" action="/projects/{bet.project_id}/delegation/accept">'
                '<button class="primary">この委譲結果を採用する</button></form></div>'
                f'<form method="post" action="/projects/{bet.project_id}/delegation/retry">'
                '<label>再委譲で改善したい観測事実</label><textarea name="feedback" required></textarea>'
                "<button>意図を変えず再委譲を準備する →</button></form>"
            )
        )
        + f"</section>{learning_form}"
    )


def _delegation_status(store: ProductStore, bet: ProductBet) -> str:
    if bet.delegation_status == "running":
        return (
            '<meta http-equiv="refresh" content="1"><section class="panel">'
            '<span class="number">隔離リポジトリで実行中</span><h2>Codexが実装と検証を進めています。</h2>'
            "<p>この画面を閉じても状態は保存されます。同じ承認から重複実行は起きません。</p></section>"
        )
    if bet.delegation_status in {"completed", "accepted"}:
        return _delegation_result(store, bet)
    if bet.delegation_status == "failed":
        return (
            '<section class="panel"><h2>委譲を完了できませんでした</h2>'
            f'<p>{escape(bet.delegation_error)}</p><a class="button" href="/projects/{bet.project_id}/delegate">同じ意図から再開する →</a></section>'
        )
    return (
        '<section class="panel"><span class="number">次の委譲</span><h2>この意図から、実リポジトリへ実装する。</h2>'
        "<p>証明用サンプルではなく、案件専用の隔離リポジトリでCodexへ実際の実装と検証を任せます。</p>"
        f'<a class="button primary" href="/projects/{bet.project_id}/delegate">委譲計画を確認する →</a></section>'
    )


def _complete_delegation(
    store: ProductStore,
    bet: ProductBet,
    runner_factory: DelegationRunnerFactory,
) -> None:
    workspace = store.workspace(bet.project_id)
    repository = workspace / "delegation" / "repository"
    repairing = bet.presentation_repair_status == "approved"
    origin_before = origin_snapshot_digest(workspace) if repairing else ""
    try:
        prepare_repository(repository, origin_summary=_delegation_origin_summary(bet))
        result = runner_factory().run(repository, _delegation_prompt(bet))
        evidence = collect_delegation_evidence(repository, result, attempt=bet.delegation_attempts)
        if repairing and origin_snapshot_digest(workspace) != origin_before:
            raise ValueError("Presentation repair changed the approved origin.")
        write_delegation_evidence(workspace, evidence)
    except DelegationExecutionError as error:
        store.update(
            bet.project_id,
            delegation_status="failed",
            delegation_error=error.public_message,
        )
        return
    except Exception:
        store.update(
            bet.project_id,
            delegation_status="failed",
            delegation_error="委譲は失敗しました。承認済み意図と既存の証拠は維持されています。",
        )
        return
    store.update(
        bet.project_id,
        delegation_status="completed",
        delegation_error="",
        presentation_repair_status=(
            "completed"
            if repairing and evidence.verification_status == "passed"
            else bet.presentation_repair_status
        ),
    )


def _ready(store: ProductStore, bet: ProductBet, message: str = "") -> str:
    workspace = store.workspace(bet.project_id)
    manifest = yaml.safe_load((workspace / "projections/manifest.yaml").read_text(encoding="utf-8"))
    notice = f'<p class="notice">{escape(message)}</p>' if message else ""
    delegation = _delegation_status(store, bet)
    pending = ""
    if bet.pending_candidate:
        candidate = load_candidate(workspace, bet.pending_candidate)
        records = "".join(
            f"<li><code>{escape(item)}</code></li>" for item in candidate.affected_records
        )
        projections = "".join(
            f"<li><code>{escape(item)}</code></li>" for item in candidate.affected_projections
        )
        rediscovery_context = (
            "<p><strong>敗戦記録:</strong> 現在の課題の見立てと、確認できなかった証拠を旧Storyに残します。</p>"
            if bet.problem_rediscovery_status == "candidate"
            else ""
        )
        pending = (
            '<section class="panel"><h2>変更候補の影響</h2>'
            f"<p>変更する最上位層: <strong>{escape(bet.pending_layer)}</strong></p>"
            f"{rediscovery_context}"
            f'<div class="grid"><div><h3>影響する原点レコード</h3><ul>{records}</ul></div>'
            f"<div><h3>再生成する射影</h3><ul>{projections}</ul></div></div>"
            "<p>承認前は正本を変更しません。</p>"
            "<p><strong>最大APIリクエスト: 1回 / 変動費上限: $1.00</strong></p>"
            f'<form method="post" action="/projects/{bet.project_id}/change/approve">'
            '<div class="actions"><button class="primary">影響を承認して再射影 →</button></form>'
            f'<form method="post" action="/projects/{bet.project_id}/change/reject">'
            "<button>変更候補を却下</button></form></div></section>"
        )
    proposal = ""
    if bet.pending_proposal:
        proposal = (
            '<section class="panel"><h2>ガードレールからの検証変更案</h2>'
            "<p>ストーリーとACを固定したまま、第4層だけを変更します。</p>"
            "<p><strong>最大APIリクエスト: 1回 / 変動費上限: $1.00</strong></p>"
            f'<form method="post" action="/projects/{bet.project_id}/learning/adopt">'
            '<button class="primary">検証変更を承認して採用 →</button></form></section>'
        )
    repair = ""
    if bet.presentation_repair_status == "proposed":
        repair = (
            '<section class="panel"><span class="number">Presentation修復案</span>'
            "<h2>原点を変えず、動かなかった成果だけを直す。</h2>"
            "<p>Story・AC・確かめ方を含む原点4層は固定します。操作失敗の事実を添えて、Codexへ1回だけ再委譲します。</p>"
            f'<form method="post" action="/projects/{bet.project_id}/learning/repair">'
            '<label><input style="width:auto" type="checkbox" name="consent" value="yes" required> '
            "原点を変えない1回のPresentation修復を承認する</label>"
            '<button class="primary">Presentationだけを修復する →</button></form></section>'
        )
    rediscovery = ""
    if bet.problem_rediscovery_status == "discovering":
        rediscovery = (
            '<section class="panel"><span class="number">課題を再発見する</span>'
            "<h2>新しく観測した人と困りごとを教えてください。</h2>"
            "<p>現在の課題を自動では書き換えません。新しい観測を第2層の変更候補として影響確認します。</p>"
            f'<form method="post" action="/projects/{bet.project_id}/learning/rediscover">'
            '<label>新しく観測した人</label><input name="actor" required>'
            '<label>その人が実際に困っていたこと</label><textarea name="pain" required></textarea>'
            '<button class="primary">第2層の変更候補を確認する →</button></form></section>'
        )
    return _layout(
        bet.name,
        f'<p class="meta">{escape(bet.name)}</p><h1>開発をCodexへ委譲し、証拠で判断する。</h1>{_steps("ready")}{_intent(bet)}{notice}'
        '<p class="lede">委譲結果と証拠を一緒に確認します。作り方ではなく、承認した事業意図を満たしたかで判断します。</p>'
        f"{delegation}"
        '<section class="panel"><span class="number">原点導出の補助証拠</span><h2>交換可能な待機リストサンプル</h2>'
        "<p>動く成果を、触って判断する補助証拠です。同じ原点から動作・検証・説明を安定再生成できることを示しますが、実委譲の成果ではありません。</p></section>"
        '<section class="grid"><article class="card"><p class="meta">原点ID</p>'
        f"<code>{escape(str(manifest['origin_digest']))}</code><p>{bet.model_requests}回のモデル要求を記録</p></article>"
        f'<article class="card"><p class="meta">振る舞い検証</p><div class="metric">{"PASS" if bet.verification_status == "passed" else "未確認"}</div>'
        "<p>有効な登録、重複、無効入力、永続化境界を生成物そのもので確認します。</p></article></section>"
        f'<div class="actions"><a class="button primary" href="/projects/{bet.project_id}/result">生成物を開く →</a>'
        f'<a class="button" href="/projects/{bet.project_id}/preview">全画面で触る</a></div>'
        '<section class="grid"><form class="panel" method="post" action="/projects/'
        + bet.project_id
        + '/change">'
        "<h2>意図を変更する</h2><p>実装方法ではなく、変えたい意味や成果を日本語で書いてください。</p>"
        '<textarea name="request" required></textarea><button>影響をプレビュー →</button></form></section>'
        f'{pending}{proposal}{repair}{rediscovery}<section class="panel"><h2>承認と学習の履歴</h2>{_history(workspace)}</section>',
    )


def _dashboard(store: ProductStore, project_id: str, *, uses_external_model: bool) -> str:
    bet = store.load(project_id)
    if bet.stage == "problem":
        return _problem(bet)
    if bet.stage == "outcomes":
        return _outcomes(bet)
    if bet.stage == "verification":
        return _verification(store, bet)
    if bet.stage == "generation":
        return _generation(store, bet, uses_external_model=uses_external_model)
    if bet.stage == "generating":
        return _generating(bet, uses_external_model=uses_external_model)
    return _ready(store, bet)


def _complete_generation(
    store: ProductStore,
    bet: ProductBet,
    provider_factory: ProviderFactory,
    maximum_requests: int,
) -> None:
    try:
        ProjectionEngine(store.workspace(bet.project_id), provider_factory()).project()
    except Exception:
        store.update(
            bet.project_id,
            stage="generation",
            error="生成に失敗しました。原点は変更されていません。再開できます。",
            model_requests=bet.model_requests + maximum_requests,
        )
        return
    verified = verify_generated_projection(store.workspace(bet.project_id))
    store.update(
        bet.project_id,
        stage="ready",
        error="",
        model_requests=bet.model_requests + maximum_requests,
        verification_status="passed" if verified else "failed",
    )


def _projection_application(workspace: Path) -> Application:
    manifest = yaml.safe_load((workspace / "projections/manifest.yaml").read_text(encoding="utf-8"))
    filename = "experience.py" if manifest.get("projection_kind") == "brief" else "waitlist.py"
    path = workspace / "projections/developer" / filename
    spec = importlib.util.spec_from_file_location(f"dodai_product_{workspace.name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Generated projection could not be loaded.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if manifest.get("projection_kind") == "brief":
        meaning = module.describe()

        def brief(environ: dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
            return _respond(
                start_response,
                _layout(
                    str(meaning["product_name"]),
                    f'<h1>{escape(meaning["headline"])}</h1><p class="lede">{escape(meaning["value_proposition"])}</p>',
                ),
            )

        return brief
    return cast(Application, module.create_application(workspace / ".dodai/registrations.json"))


def _result_page(store: ProductStore, bet: ProductBet) -> str:
    workspace = store.workspace(bet.project_id)
    brief = (workspace / "projections/stakeholder/brief.md").read_text(encoding="utf-8")
    return _layout(
        bet.name,
        f'<p class="meta">{escape(bet.name)}</p><h1>原点導出の証明用サンプル</h1>{_intent(bet)}'
        '<p class="lede">これはCodexの実委譲結果と証拠ではなく、同じ原点から動作・検証・説明を再生成できることの補助証拠です。</p>'
        f'<div class="notice"><strong>振る舞い検証: {"PASS" if bet.verification_status == "passed" else "未確認"}</strong>'
        "<p><strong>満たした検証:</strong> 承認した最小体験を完了でき、重複と無効入力を期待通り扱える。</p>"
        "<p><strong>満たしていない検証:</strong> なし。未観測の事業成果は、利用後の証拠で判断します。</p></div>"
        '<section class="panel"><span class="number">実行可能Presentationの証明用サンプル</span>'
        "<h2>待機リストは交換可能な証明題材です</h2><p>待機リストを作ることがDodaiの価値ではありません。"
        "1つの原点から、動く成果・検証・説明を一貫して導出できることだけを、この縦一本で証明しています。</p></section>"
        f'<iframe title="生成されたプロダクト" src="/projects/{bet.project_id}/preview"></iframe>'
        f'<section class="panel"><h2>関係者向け説明</h2><pre>{escape(brief)}</pre></section>'
        f'<div class="actions"><a class="button" href="/projects/{bet.project_id}">判断画面へ戻る</a></div>',
    )


def _serve_projection(
    workspace: Path,
    project_id: str,
    environ: dict[str, Any],
    start_response: StartResponse,
) -> Iterable[bytes]:
    app = _projection_application(workspace)
    delegated = dict(environ)
    delegated["PATH_INFO"] = "/"
    response: dict[str, Any] = {}

    def capture(status: str, headers: list[tuple[str, str]]) -> None:
        response["status"] = status
        response["headers"] = headers

    body = b"".join(app(delegated, capture))
    body = body.replace(b'action="/"', f'action="/projects/{project_id}/preview"'.encode())
    headers = [
        (name, str(len(body)) if name.lower() == "content-length" else value)
        for name, value in response["headers"]
    ]
    start_response(response["status"], headers)
    return [body]


def _serve_delegated_product(
    repository: Path,
    relative_path: str,
    start_response: StartResponse,
) -> Iterable[bytes]:
    delivery_root = (repository / "product").resolve()
    requested = relative_path or "index.html"
    path = (delivery_root / requested).resolve()
    if not path.is_relative_to(delivery_root) or path.is_symlink() or not path.is_file():
        return _respond(start_response, "Not found", "404 Not Found")
    body = path.read_bytes()
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if media_type.startswith("text/") or media_type in {"application/javascript", "image/svg+xml"}:
        media_type += "; charset=utf-8"
    start_response(
        "200 OK",
        [
            ("Content-Type", media_type),
            ("Content-Length", str(len(body))),
            (
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'none'",
            ),
            ("X-Content-Type-Options", "nosniff"),
        ],
    )
    return [body]


def _prepare_plain_change(store: ProductStore, bet: ProductBet, request: str) -> ProductBet:
    if solution_terms(request):
        return store.update(bet.project_id, error="Howではなく、変えたい成果を記述してください。")
    workspace = store.workspace(bet.project_id)
    lower = request.lower()
    if any(term in lower for term in ("誰", "困", "課題", "actor", "pain")):
        layer_file, layer_name, collection, field = (
            "02-user-stories.yaml",
            "第2層",
            "stories",
            "pain",
        )
    elif any(term in lower for term in ("検証", "確認", "verify")):
        layer_file, layer_name, collection, field = (
            "04-test-specifications.yaml",
            "第4層",
            "specifications",
            "then",
        )
    else:
        layer_file, layer_name, collection, field = (
            "03-acceptance-criteria.yaml",
            "第3層",
            "criteria",
            "statement",
        )
    path = workspace / "origin" / layer_file
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["revision"] = int(document["revision"]) + 1
    document[collection][0][field] = request.strip()
    proposed = yaml.safe_dump(document, sort_keys=False, allow_unicode=True)
    candidate = prepare_candidate(workspace, layer_file, proposed)
    if not candidate.valid:
        if candidate.blocked_by_losing_records:
            prior = ", ".join(candidate.blocked_by_losing_records)
            return store.update(
                bet.project_id,
                error=f"過去に撤退したHowと重なります: {prior}。敗戦記録を確認してください。",
            )
        return store.update(bet.project_id, error="変更候補が原点の制約を満たしません。")
    return store.update(
        bet.project_id,
        pending_candidate=candidate.candidate_id,
        pending_layer=layer_name,
        error="",
    )


def create_portal_application(
    root: Path,
    *,
    provider_factory: ProviderFactory = OpenAIContentProvider,
    delegation_runner_factory: DelegationRunnerFactory = CodexCliRunner,
    audit_application: Application | None = None,
) -> Application:
    store = ProductStore(root.resolve())
    uses_external_model = provider_factory is not SampleContentProvider

    def app(environ: dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
        path = str(environ.get("PATH_INFO", "/"))
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        if path in ("/proof", "/workbench", "/candidate", "/candidate/approve", "/guardrail"):
            if audit_application is None:
                return _respond(start_response, "Not found", "404 Not Found")
            delegated = dict(environ)
            if path == "/proof":
                delegated["PATH_INFO"] = "/"
            return audit_application(delegated, start_response)
        if path == "/" and method == "GET":
            return _respond(start_response, _home(store))
        if path == "/projects" and method == "POST":
            try:
                bet = store.create(_form(environ).get("name", ""))
            except ValueError as error:
                return _respond(
                    start_response, _home(store, str(error)), "422 Unprocessable Entity"
                )
            return _redirect(start_response, f"/projects/{bet.project_id}")
        match = re.fullmatch(r"/projects/([^/]+)(?:/(.+))?", path)
        if match is None:
            return _respond(start_response, "Not found", "404 Not Found")
        project_id, action = match.group(1), match.group(2) or ""
        try:
            bet = store.load(project_id)
        except (FileNotFoundError, ValueError):
            return _respond(start_response, "Unknown product bet", "404 Not Found")
        if not action and method == "GET":
            return _respond(
                start_response,
                _dashboard(store, project_id, uses_external_model=uses_external_model),
            )
        if action == "problem" and method == "POST":
            values = _form(environ)
            try:
                record_problem(
                    store,
                    project_id,
                    actor=values.get("actor", ""),
                    pain=values.get("pain", ""),
                    intended_outcome=values.get("intended_outcome", ""),
                )
            except ValueError as error:
                store.update(project_id, error=str(error))
            return _redirect(start_response, f"/projects/{project_id}")
        if action == "outcomes" and method == "POST":
            values = _form(environ)
            try:
                record_outcomes(
                    store,
                    project_id,
                    outcome=values.get("outcome", ""),
                    journey=values.get("journey", ""),
                    term_name=values.get("term_name", ""),
                    term_definition=values.get("term_definition", ""),
                )
            except (TypeError, ValueError) as error:
                store.update(project_id, error=str(error))
            return _redirect(start_response, f"/projects/{project_id}")
        if action == "verification" and method == "POST":
            approve_verification(store, project_id)
            return _redirect(start_response, f"/projects/{project_id}")
        if action == "back/outcomes" and method == "POST":
            store.update(project_id, stage="outcomes", error="")
            return _redirect(start_response, f"/projects/{project_id}")
        if action == "back/verification" and method == "POST":
            store.update(project_id, stage="verification", error="")
            return _redirect(start_response, f"/projects/{project_id}")
        if action == "generate" and method == "POST":
            values = _form(environ)
            if values.get("consent") != "yes":
                store.update(project_id, error="生成前の明示承認が必要です。")
                return _redirect(start_response, f"/projects/{project_id}")
            plan = generation_plan(store, project_id, uses_external_model=uses_external_model)
            claimed = store.claim_generation(project_id)
            if claimed is None:
                return _redirect(start_response, f"/projects/{project_id}")
            Thread(
                target=_complete_generation,
                args=(store, claimed, provider_factory, plan.maximum_requests),
                daemon=True,
            ).start()
            return _redirect(start_response, f"/projects/{project_id}")
        if action == "result" and method == "GET":
            if bet.stage != "ready":
                return _respond(start_response, "Projection not ready", "409 Conflict")
            return _respond(start_response, _result_page(store, bet))
        if action == "delegate" and method == "GET":
            if bet.stage != "ready":
                return _respond(start_response, "Delegation not ready", "409 Conflict")
            return _respond(start_response, _delegation_plan(bet))
        if action == "delegate" and method == "POST":
            if bet.stage != "ready":
                return _respond(start_response, "Delegation not ready", "409 Conflict")
            values = _form(environ)
            if values.get("consent") != "yes":
                return _respond(
                    start_response,
                    _delegation_plan(bet, "Codexへ委譲する前に明示承認が必要です。"),
                    "422 Unprocessable Entity",
                )
            claimed = store.claim_delegation(project_id)
            if claimed is not None:
                Thread(
                    target=_complete_delegation,
                    args=(store, claimed, delegation_runner_factory),
                    daemon=True,
                ).start()
            return _redirect(start_response, f"/projects/{project_id}")
        if action == "delegation/accept" and method == "POST":
            if bet.delegation_status != "completed":
                return _respond(start_response, "Delegation result missing", "409 Conflict")
            changed = store.update(
                project_id,
                delegation_status="accepted",
                delegation_accepted=True,
            )
            decision_path = store.workspace(project_id) / ".dodai" / "delegation" / "adoption.yaml"
            decision_path.write_text(
                yaml.safe_dump(
                    {
                        "decision": "accepted",
                        "attempt": changed.delegation_attempts,
                        "origin_evidence": {
                            "story": "story_primary_pain",
                            "criterion": "ac_primary_outcome",
                            "specification": "spec_primary_outcome_is_observable",
                        },
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            return _respond(
                start_response,
                _ready(store, changed, "この委譲結果を採用しました。"),
            )
        if action == "delegation/retry" and method == "POST":
            feedback = _form(environ).get("feedback", "").strip()
            if not feedback:
                return _respond(
                    start_response,
                    _ready(store, bet, "再委譲で改善したい観測事実を入力してください。"),
                    "422 Unprocessable Entity",
                )
            changed = store.update(
                project_id,
                delegation_status="planned",
                delegation_feedback=feedback,
                delegation_accepted=False,
                delegation_error="",
                presentation_repair_status="not_started",
            )
            return _respond(
                start_response,
                _delegation_plan(
                    changed,
                    "前回の証拠を追加しました。承認済み意図は変更しません。",
                ),
            )
        if (
            action == "delegated-product" or action.startswith("delegated-product/")
        ) and method == "GET":
            if bet.delegation_status not in {"completed", "accepted"}:
                return _respond(start_response, "Delegation result missing", "409 Conflict")
            relative = action.removeprefix("delegated-product/")
            if action == "delegated-product":
                relative = ""
            return _serve_delegated_product(
                store.workspace(project_id) / "delegation" / "repository",
                relative,
                start_response,
            )
        if action == "preview":
            if bet.stage != "ready":
                return _respond(start_response, "Projection not ready", "409 Conflict")
            return _serve_projection(
                store.workspace(project_id), project_id, environ, start_response
            )
        if action == "change" and method == "POST":
            changed = _prepare_plain_change(store, bet, _form(environ).get("request", ""))
            return _respond(
                start_response, _ready(store, changed, changed.error or "変更候補を作成しました。")
            )
        if action == "change/approve" and method == "POST":
            if not bet.pending_candidate:
                return _respond(start_response, "Candidate missing", "409 Conflict")
            try:
                approve_candidate(
                    store.workspace(project_id),
                    bet.pending_candidate,
                    provider_factory(),
                    approved_by="local human",
                )
            except Exception:
                changed = store.update(
                    project_id,
                    error="変更の承認に失敗し、正本は維持されました。",
                    model_requests=bet.model_requests + 1,
                )
                return _respond(
                    start_response,
                    _ready(store, changed, changed.error),
                    "422 Unprocessable Entity",
                )
            learning_change = bet.learning_change
            rediscovery_change = bet.problem_rediscovery_status == "candidate"
            changed = store.update(
                project_id,
                pending_candidate="",
                pending_layer="",
                error="",
                model_requests=bet.model_requests + 1,
                delegation_status=(
                    "planned" if learning_change or rediscovery_change else bet.delegation_status
                ),
                delegation_feedback=(
                    ""
                    if rediscovery_change
                    else (
                        load_interaction_evidence(Path(bet.interaction_evidence))["observation"]
                        if learning_change
                        else bet.delegation_feedback
                    )
                ),
                delegation_accepted=False if learning_change else bet.delegation_accepted,
                learning_change=False,
                presentation_repair_status=(
                    "not_started"
                    if learning_change or rediscovery_change
                    else bet.presentation_repair_status
                ),
                actor=bet.rediscovered_actor if rediscovery_change else bet.actor,
                pain=bet.rediscovered_pain if rediscovery_change else bet.pain,
                problem_rediscovery_status=(
                    "completed" if rediscovery_change else bet.problem_rediscovery_status
                ),
            )
            return _respond(
                start_response,
                _ready(
                    store,
                    changed,
                    (
                        "第4層を承認しました。StoryとACは固定したまま再委譲できます。"
                        if learning_change
                        else "新しい課題の見立てを承認し、全射影を再生成しました。"
                    )
                    if learning_change or rediscovery_change
                    else "変更を承認し、全射影を再生成しました。",
                ),
            )
        if action == "change/reject" and method == "POST":
            if bet.pending_candidate:
                reject_candidate(store.workspace(project_id), bet.pending_candidate)
            changed = store.update(
                project_id,
                pending_candidate="",
                pending_layer="",
                error="",
                problem_rediscovery_status=(
                    "discovering"
                    if bet.problem_rediscovery_status == "candidate"
                    else bet.problem_rediscovery_status
                ),
            )
            return _respond(start_response, _ready(store, changed, "変更候補を却下しました。"))
        if action == "learning/evaluate" and method == "POST":
            if bet.delegation_status not in {"completed", "accepted"}:
                return _respond(start_response, "Delegation result missing", "409 Conflict")
            values = _form(environ)
            try:
                evidence_path = record_interaction_evidence(
                    store.workspace(project_id),
                    attempt=bet.delegation_attempts,
                    pain_present=values.get("pain_present", ""),
                    behavior_worked=values.get("behavior_worked", ""),
                    outcome_achieved=values.get("outcome_achieved", ""),
                    observation=values.get("observation", ""),
                )
                recorded = load_interaction_evidence(evidence_path)
            except ValueError as error:
                return _respond(
                    start_response, _ready(store, bet, str(error)), "422 Unprocessable Entity"
                )
            diagnosis = recorded["diagnosis"]
            if diagnosis["evidence_kind"] == "behavior_passed_outcome_failed":
                candidate = prepare_reverification_candidate(
                    store.workspace(project_id), evidence_path
                )
                changed = store.update(
                    project_id,
                    pending_candidate=candidate.candidate_id,
                    pending_layer="第4層",
                    interaction_evidence=str(evidence_path),
                    learning_change=True,
                )
                return _respond(
                    start_response,
                    _ready(store, changed, "第4層の確かめ方を見直します。StoryとACは固定します。"),
                )
            if diagnosis["evidence_kind"] == "behavior_failed":
                changed = store.update(
                    project_id,
                    interaction_evidence=str(evidence_path),
                    presentation_repair_status="proposed",
                    repair_origin_digest=origin_snapshot_digest(store.workspace(project_id)),
                )
                return _respond(
                    start_response,
                    _ready(
                        store,
                        changed,
                        "操作失敗の証拠からPresentationだけを修復します。原点4層は変更しません。",
                    ),
                )
            if diagnosis["evidence_kind"] == "problem_not_observed":
                changed = store.update(
                    project_id,
                    interaction_evidence=str(evidence_path),
                    problem_rediscovery_status="discovering",
                )
                return _respond(
                    start_response,
                    _ready(
                        store,
                        changed,
                        "現在の課題を自動では書き換えません。新しく観測した人と困りごとから再発見します。",
                    ),
                )
            changed = store.update(project_id, interaction_evidence=str(evidence_path))
            message = (
                "実際の操作で成果が確認できました。採用するか判断できます。"
                if diagnosis["evidence_kind"] == "outcome_achieved"
                else f"{diagnosis['failure_layer']}を次の学習対象として記録しました。"
            )
            return _respond(start_response, _ready(store, changed, message))
        if action == "learning/rediscover" and method == "POST":
            if bet.problem_rediscovery_status != "discovering":
                return _respond(start_response, "Discovery evidence missing", "409 Conflict")
            values = _form(environ)
            try:
                candidate = prepare_story_rediscovery_candidate(
                    store.workspace(project_id),
                    Path(bet.interaction_evidence),
                    actor=values.get("actor", ""),
                    pain=values.get("pain", ""),
                )
            except ValueError as error:
                return _respond(
                    start_response,
                    _ready(store, bet, str(error)),
                    "422 Unprocessable Entity",
                )
            changed = store.update(
                project_id,
                pending_candidate=candidate.candidate_id,
                pending_layer="第2層",
                problem_rediscovery_status="candidate",
                rediscovered_actor=values.get("actor", "").strip(),
                rediscovered_pain=values.get("pain", "").strip(),
            )
            return _respond(
                start_response,
                _ready(store, changed, "敗戦記録を残す第2層候補を作成しました。"),
            )
        if action == "learning/repair" and method == "POST":
            values = _form(environ)
            if bet.presentation_repair_status != "proposed":
                return _respond(start_response, "Repair plan missing", "409 Conflict")
            if values.get("consent") != "yes":
                return _respond(
                    start_response,
                    _ready(store, bet, "Presentation修復には明示承認が必要です。"),
                    "422 Unprocessable Entity",
                )
            if origin_snapshot_digest(store.workspace(project_id)) != bet.repair_origin_digest:
                return _respond(start_response, "Approved origin changed", "409 Conflict")
            observation = load_interaction_evidence(Path(bet.interaction_evidence))["observation"]
            changed = store.update(
                project_id,
                presentation_repair_status="approved",
                delegation_status="planned",
                delegation_feedback=str(observation),
                delegation_accepted=False,
                delegation_error="",
            )
            return _respond(
                start_response,
                _delegation_plan(
                    changed,
                    "原点4層を固定し、同じ意図からPresentationだけを直す1回の修復を承認しました。",
                ),
            )
        if action == "telemetry" and method == "POST":
            values = _form(environ)
            if values.get("evidence_kind"):
                diagnosis = diagnose_failure(values["evidence_kind"])
                diagnosis_evidence = {
                    "evidence_kind": values["evidence_kind"],
                    "evidence": values.get("evidence", ""),
                    "failure_layer": diagnosis.layer,
                    "retained": diagnosis.retained,
                    "next_change": diagnosis.next_change,
                }
                decision_id = sha256(
                    yaml.safe_dump(diagnosis_evidence, sort_keys=True).encode()
                ).hexdigest()[:12]
                decision_path = (
                    store.workspace(project_id) / ".dodai/decisions" / f"{decision_id}.yaml"
                )
                decision_path.parent.mkdir(parents=True, exist_ok=True)
                decision_path.write_text(
                    yaml.safe_dump(
                        {
                            "action": "diagnose_failure_layer",
                            "reason": diagnosis.finding,
                            "evidence": diagnosis_evidence,
                        },
                        sort_keys=False,
                        allow_unicode=True,
                    ),
                    encoding="utf-8",
                )
                message = (
                    f"診断: {diagnosis.layer} — {diagnosis.finding} "
                    f"固定するもの: {diagnosis.retained}。次に変えるもの: {diagnosis.next_change}。"
                )
                return _respond(start_response, _ready(store, bet, message))
            telemetry = {
                "elapsed_time": float(values.get("elapsed_time", "0")),
                "variable_model_cost": float(values.get("variable_model_cost", "0")),
                "representation_revision": int(values.get("representation_revision", "0")),
                "rebuild_mismatch": values.get("rebuild_mismatch") == "yes",
                "bet": bet.name,
                "evidence": values.get("evidence", ""),
            }
            telemetry_path = store.workspace(project_id) / ".dodai/telemetry/latest.yaml"
            telemetry_path.parent.mkdir(parents=True, exist_ok=True)
            telemetry_path.write_text(
                yaml.safe_dump(telemetry, sort_keys=False, allow_unicode=True), encoding="utf-8"
            )
            result = evaluate_telemetry(store.workspace(project_id), telemetry_path)
            labels = {
                "continue": "続行: ガードレールと撤退条件には到達していません。",
                "revise_test_specifications": "検証変更: ガードレールを超えたため、第4層の変更を提案しました。",
                "record_loss": "撤退: このHowを敗戦記録へ残しました。",
            }
            decision_id = sha256(yaml.safe_dump(telemetry, sort_keys=True).encode()).hexdigest()[
                :12
            ]
            decision_path = store.workspace(project_id) / ".dodai/decisions" / f"{decision_id}.yaml"
            decision_path.parent.mkdir(parents=True, exist_ok=True)
            decision_path.write_text(
                yaml.safe_dump(
                    {"action": result.action, "reason": result.reason, "evidence": telemetry},
                    sort_keys=False,
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )
            changed = store.update(
                project_id,
                pending_proposal=(
                    result.proposal_path.as_posix() if result.proposal_path is not None else ""
                ),
            )
            return _respond(start_response, _ready(store, changed, labels[result.action]))
        if action == "learning/adopt" and method == "POST":
            if not bet.pending_proposal:
                return _respond(start_response, "Proposal missing", "409 Conflict")
            candidate = candidate_from_proposal(
                store.workspace(project_id), Path(bet.pending_proposal)
            )
            try:
                approve_candidate(
                    store.workspace(project_id),
                    candidate.candidate_id,
                    provider_factory(),
                    approved_by="local human",
                )
            except Exception:
                changed = store.update(
                    project_id,
                    error="検証変更の採用に失敗しました。",
                    model_requests=bet.model_requests + 1,
                )
                return _respond(
                    start_response,
                    _ready(store, changed, changed.error),
                    "422 Unprocessable Entity",
                )
            changed = store.update(
                project_id,
                pending_proposal="",
                model_requests=bet.model_requests + 1,
                error="",
            )
            return _respond(
                start_response,
                _ready(store, changed, "第4層の検証変更を承認し、全射影を再生成しました。"),
            )
        return _respond(start_response, "Not found", "404 Not Found")

    return app
