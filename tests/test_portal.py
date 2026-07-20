from __future__ import annotations

from io import BytesIO
from pathlib import Path
from threading import Thread
from time import sleep
from urllib.parse import urlencode

import yaml

from dodai.portal import create_portal_application
from dodai.product import ProductStore
from dodai.projection import ProjectionContent, SampleContentProvider


class RecordingProvider:
    def __init__(self) -> None:
        self.requests = 0

    def derive(self, origin_text: str) -> ProjectionContent:
        self.requests += 1
        return ProjectionContent(
            product_name="地域イベント",
            audience="地域の参加者",
            headline="見逃さず、地域とつながる",
            value_proposition="関心のあるイベントへ参加意思を残せます。",
            call_to_action="参加する",
            stakeholder_summary="参加者が価値を理解し、参加意思を残せる最小の体験です。",
        )


class FailOnceProvider(RecordingProvider):
    def derive(self, origin_text: str) -> ProjectionContent:
        self.requests += 1
        if self.requests == 1:
            raise RuntimeError("temporary failure")
        return ProjectionContent(
            product_name="再開できる賭け",
            audience="利用者",
            headline="失敗から再開する",
            value_proposition="承認済み判断を失わず再開できます。",
            call_to_action="参加する",
            stakeholder_summary="失敗後も同じ原点から生成を再開します。",
        )


class SlowProvider(RecordingProvider):
    def derive(self, origin_text: str) -> ProjectionContent:
        sleep(0.08)
        return super().derive(origin_text)


def request(
    application,
    path: str = "/",
    method: str = "GET",
    form: dict[str, str] | None = None,
) -> tuple[str, dict[str, str], str]:
    payload = urlencode(form or {}).encode() if method == "POST" else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "CONTENT_LENGTH": str(len(payload)),
        "wsgi.input": BytesIO(payload),
    }
    response: dict[str, object] = {}

    def start_response(status, headers):
        response["status"] = status
        response["headers"] = dict(headers)

    body = b"".join(application(environ, start_response)).decode()
    return str(response["status"]), dict(response["headers"]), body


def create_bet(application) -> str:
    status, headers, _ = request(application, "/projects", "POST", {"name": "地域イベント"})
    assert status == "303 See Other"
    return headers["Location"].split("/")[-1]


def advance_to_generation(application, project_id: str) -> None:
    request(
        application,
        f"/projects/{project_id}/problem",
        "POST",
        {"actor": "地域の参加者", "pain": "関心のある催しを見逃してしまう"},
    )
    request(
        application,
        f"/projects/{project_id}/outcomes",
        "POST",
        {
            "outcome": "参加者が関心のある催しへ参加意思を残せる。",
            "journey": "価値を理解し、参加を選び、後から参加済みだと分かる。",
        },
    )
    status, _, verification = request(application, f"/projects/{project_id}")
    assert status == "200 OK"
    assert "承認すると始まること" in verification
    request(application, f"/projects/{project_id}/verification", "POST")


def wait_for(application, project_id: str, text: str) -> str:
    page = ""
    for _ in range(100):
        _, _, page = request(application, f"/projects/{project_id}")
        if text in page:
            return page
        sleep(0.01)
    raise AssertionError(f"Timed out waiting for {text}: {page[:500]}")


def test_home_starts_and_resumes_multiple_product_bets(project: Path) -> None:
    application = create_portal_application(project)

    _, _, empty = request(application)
    first = create_bet(application)
    second = request(application, "/projects", "POST", {"name": "別の賭け"})[1]["Location"].split(
        "/"
    )[-1]
    restarted = create_portal_application(project)
    _, _, resumed = request(restarted)

    assert "まだプロダクトはありません" in empty
    assert first != second
    assert "地域イベント" in resumed
    assert "別の賭け" in resumed
    assert resumed.count("続きから始める") == 2
    assert "課題を整理中" in resumed
    assert "誰が何に困っているかを言葉にする" in resumed
    assert "触れるプロダクト" in resumed
    assert "テスト結果" in resumed
    assert "説明資料" in resumed
    assert "AIへ開発を任せても、事業の意図を見失わない" in resumed
    assert "PM・エンジニア" in resumed
    assert "コード・テスト・説明のずれ" in resumed
    assert "何を作ったかではなく、なぜ正しいと言えるか" in resumed


def test_invalid_inputs_are_explained_without_losing_progress(project: Path) -> None:
    application = create_portal_application(project)

    status, _, home = request(application, "/projects", "POST", {"name": ""})
    project_id = create_bet(application)
    request(
        application,
        f"/projects/{project_id}/problem",
        "POST",
        {"actor": "", "pain": ""},
    )
    _, _, problem = request(application, f"/projects/{project_id}")

    assert status == "422 Unprocessable Entity"
    assert "プロダクト名を入力" in home
    assert "誰が、何に困っているか" in problem


def test_solution_vocabulary_returns_discovery_to_intended_outcome(project: Path) -> None:
    application = create_portal_application(project)
    project_id = create_bet(application)

    request(
        application,
        f"/projects/{project_id}/problem",
        "POST",
        {"actor": "地域の参加者", "pain": "イベント用アプリが必要"},
    )
    _, _, warning = request(application, f"/projects/{project_id}")
    request(
        application,
        f"/projects/{project_id}/problem",
        "POST",
        {
            "actor": "地域の参加者",
            "pain": "イベント用アプリが必要",
            "intended_outcome": "関心のある催しを見逃さない",
        },
    )
    _, _, outcomes = request(application, f"/projects/{project_id}")

    assert "Howを検出しました" in warning
    assert "それによって実現したい成果" in warning
    assert "成功した状態を描く" in outcomes
    state = (project / ".dodai/workspaces" / f"{project_id}.yaml").read_text()
    assert "アプリ" not in state
    assert "関心のある催しを見逃さない" in state


def test_verification_review_shows_approved_meaning_and_can_return_for_revision(
    project: Path,
) -> None:
    application = create_portal_application(project)
    project_id = create_bet(application)
    request(
        application,
        f"/projects/{project_id}/problem",
        "POST",
        {"actor": "地域の参加者", "pain": "催しを見逃す"},
    )
    request(
        application,
        f"/projects/{project_id}/outcomes",
        "POST",
        {
            "outcome": "参加意思を残せる。",
            "journey": "価値を理解して参加する。",
            "term_name": "参加意思",
            "term_definition": "催しへの参加を希望する状態",
        },
    )

    _, _, verification = request(application, f"/projects/{project_id}")
    request(application, f"/projects/{project_id}/back/outcomes", "POST")
    _, _, revised = request(application, f"/projects/{project_id}")

    assert "あなたが決めたこと" in verification
    assert "Dodaiが確かめること" in verification
    assert "承認すると始まること" in verification
    assert "参加意思" in verification
    assert "催しへの参加を希望する状態" in verification
    assert "spec_primary_outcome_is_observable" not in verification
    assert "前提:" not in verification
    assert "再生成 120秒" not in verification
    assert "不一致が 3改訂" not in verification
    assert "成功した状態を描く" in revised


def test_outcome_questions_are_lightweight_and_operational_defaults_are_internal(
    project: Path,
) -> None:
    application = create_portal_application(project)
    project_id = create_bet(application)
    request(
        application,
        f"/projects/{project_id}/problem",
        "POST",
        {"actor": "地域の参加者", "pain": "催しを見逃す"},
    )

    _, _, page = request(application, f"/projects/{project_id}")
    request(
        application,
        f"/projects/{project_id}/outcomes",
        "POST",
        {
            "outcome": "関心のある催しへ参加意思を残せる。",
            "journey": "開催情報を見る → 参加を選ぶ → 参加済みだと確認できる",
        },
    )
    _, _, verification = request(application, f"/projects/{project_id}")

    assert "再生成の上限時間" not in page
    assert "何回不一致" not in page
    assert "利用者は最初に何をして、最後にどうなる？" in page
    assert "言葉の意味を補足する（任意）" in page
    assert "この賭け" not in page
    assert "業務用語" not in page
    assert "運用条件は、Dodaiが管理" in verification
    criteria = (
        project / ".dodai/workspaces" / project_id / "origin/03-acceptance-criteria.yaml"
    ).read_text()
    assert "threshold: 120" in criteria
    assert "threshold: 3" in criteria


def test_hidden_operational_conditions_preserve_existing_project_decisions(
    project: Path,
) -> None:
    application = create_portal_application(project)
    project_id = create_bet(application)
    request(
        application,
        f"/projects/{project_id}/problem",
        "POST",
        {"actor": "地域の参加者", "pain": "催しを見逃す"},
    )
    ProductStore(project).update(project_id, guardrail_seconds=90, exit_revisions=5)

    request(
        application,
        f"/projects/{project_id}/outcomes",
        "POST",
        {
            "outcome": "関心のある催しへ参加意思を残せる。",
            "journey": "開催情報を見る → 参加を選ぶ → 参加済みだと確認できる",
        },
    )

    criteria = (
        project / ".dodai/workspaces" / project_id / "origin/03-acceptance-criteria.yaml"
    ).read_text()
    assert "threshold: 90" in criteria
    assert "threshold: 5" in criteria


def test_generation_requires_consent_and_never_requests_same_identity_twice(
    project: Path,
) -> None:
    provider = RecordingProvider()
    application = create_portal_application(project, provider_factory=lambda: provider)
    project_id = create_bet(application)
    advance_to_generation(application, project_id)

    _, _, plan = request(application, f"/projects/{project_id}")
    request(application, f"/projects/{project_id}/generate", "POST")
    _, _, stopped = request(application, f"/projects/{project_id}")
    request(
        application,
        f"/projects/{project_id}/generate",
        "POST",
        {"consent": "yes"},
    )
    ready = wait_for(application, project_id, "動く成果を、触って判断する")
    request(
        application,
        f"/projects/{project_id}/generate",
        "POST",
        {"consent": "yes"},
    )
    wait_for(application, project_id, "動く成果を、触って判断する")

    assert "この内容から、3つの成果を作ります" in plan
    assert "触れるプロダクト" in plan
    assert "テスト結果" in plan
    assert "関係者向けの説明資料" in plan
    assert "最大APIリクエスト" in plan and "1回" in plan
    assert "生成前の明示承認が必要" in stopped
    assert "動く成果を、触って判断する" in ready
    assert provider.requests == 1


def test_concurrent_generation_submissions_claim_one_model_request(project: Path) -> None:
    provider = SlowProvider()
    application = create_portal_application(project, provider_factory=lambda: provider)
    project_id = create_bet(application)
    advance_to_generation(application, project_id)

    submissions = [
        Thread(
            target=request,
            args=(application, f"/projects/{project_id}/generate", "POST", {"consent": "yes"}),
        )
        for _ in range(2)
    ]
    for submission in submissions:
        submission.start()
    for submission in submissions:
        submission.join()
    wait_for(application, project_id, "動く成果を、触って判断する")

    assert provider.requests == 1


def test_generation_progress_is_visible_and_survives_navigation(project: Path) -> None:
    provider = SlowProvider()
    application = create_portal_application(project, provider_factory=lambda: provider)
    project_id = create_bet(application)
    advance_to_generation(application, project_id)

    request(
        application,
        f"/projects/{project_id}/generate",
        "POST",
        {"consent": "yes"},
    )
    _, _, progress = request(application, f"/projects/{project_id}")
    home_status, _, home = request(application)
    ready = wait_for(application, project_id, "動く成果を、触って判断する")

    assert "3つの成果を作っています" in progress
    assert "この画面を閉じても" in progress
    assert home_status == "200 OK" and "3つの成果を作成中" in home
    assert "動く成果を、触って判断する" in ready


def test_ready_journey_previews_changes_and_evaluates_learning(project: Path) -> None:
    provider = RecordingProvider()
    application = create_portal_application(project, provider_factory=lambda: provider)
    project_id = create_bet(application)
    advance_to_generation(application, project_id)
    request(
        application,
        f"/projects/{project_id}/generate",
        "POST",
        {"consent": "yes"},
    )
    wait_for(application, project_id, "動く成果を、触って判断する")

    preview_status, _, preview = request(application, f"/projects/{project_id}/preview")
    _, _, candidate = request(
        application,
        f"/projects/{project_id}/change",
        "POST",
        {"request": "参加意思を後から把握できること。"},
    )
    _, _, rejected = request(application, f"/projects/{project_id}/change/reject", "POST")
    _, _, candidate = request(
        application,
        f"/projects/{project_id}/change",
        "POST",
        {"request": "参加意思を後から把握できること。"},
    )
    approved_status, _, approved = request(
        application, f"/projects/{project_id}/change/approve", "POST"
    )
    _, _, continuing = request(
        application,
        f"/projects/{project_id}/telemetry",
        "POST",
        {"elapsed_time": "30", "variable_model_cost": "0.1", "representation_revision": "0"},
    )
    _, _, revising = request(
        application,
        f"/projects/{project_id}/telemetry",
        "POST",
        {"elapsed_time": "150", "variable_model_cost": "0.1", "representation_revision": "0"},
    )
    adopted_status, _, adopted = request(
        application, f"/projects/{project_id}/learning/adopt", "POST"
    )
    _, _, ending = request(
        application,
        f"/projects/{project_id}/telemetry",
        "POST",
        {
            "elapsed_time": "30",
            "variable_model_cost": "0.1",
            "representation_revision": "3",
            "rebuild_mismatch": "yes",
            "evidence": "三回の改訂でも一致しなかった",
        },
    )

    assert preview_status == "200 OK" and "地域イベント" in preview
    assert "変更する最上位層" in candidate and "第3層" in candidate
    assert "ac_primary_outcome" in candidate
    assert "developer/waitlist.py" in candidate
    assert "最大APIリクエスト: 1回" in candidate
    assert "変更候補を却下しました" in rejected
    assert approved_status == "200 OK"
    assert "全射影を再生成" in approved
    assert "続行:" in continuing
    assert "検証変更:" in revising
    assert adopted_status == "200 OK"
    assert "第4層の検証変更を承認" in adopted
    assert "撤退:" in ending
    assert provider.requests == 3
    story = (project / ".dodai/workspaces" / project_id / "origin/02-user-stories.yaml").read_text()
    assert "三回の改訂でも一致しなかった" in story
    decisions = list(
        (project / ".dodai/workspaces" / project_id / ".dodai/decisions").glob("*.yaml")
    )
    assert len(decisions) == 3
    _, _, blocked = request(
        application,
        f"/projects/{project_id}/change",
        "POST",
        {"request": "地域イベントという同じHowをもう一度試す。"},
    )
    assert "過去に撤退したHow" in blocked
    assert "敗戦記録を確認" in blocked


def test_failed_generation_is_visible_and_resumable_without_losing_decisions(
    project: Path,
) -> None:
    provider = FailOnceProvider()
    application = create_portal_application(project, provider_factory=lambda: provider)
    project_id = create_bet(application)
    advance_to_generation(application, project_id)

    request(
        application,
        f"/projects/{project_id}/generate",
        "POST",
        {"consent": "yes"},
    )
    restarted = create_portal_application(project, provider_factory=lambda: provider)
    failed = wait_for(restarted, project_id, "生成に失敗")
    request(
        restarted,
        f"/projects/{project_id}/generate",
        "POST",
        {"consent": "yes"},
    )
    ready = wait_for(restarted, project_id, "動く成果を、触って判断する")

    assert "生成に失敗" in failed and "再開できます" in failed
    assert "この内容から、3つの成果を作ります" in failed
    assert "動く成果を、触って判断する" in ready
    assert "2回のモデル要求を記録" in ready
    assert provider.requests == 2


def test_keyless_sample_provider_completes_the_same_product_journey(project: Path) -> None:
    application = create_portal_application(project, provider_factory=SampleContentProvider)
    project_id = create_bet(application)
    advance_to_generation(application, project_id)

    _, _, plan = request(application, f"/projects/{project_id}")

    request(
        application,
        f"/projects/{project_id}/generate",
        "POST",
        {"consent": "yes"},
    )
    wait_for(application, project_id, "動く成果を、触って判断する")
    status, _, result = request(application, f"/projects/{project_id}/result")

    assert status == "200 OK"
    assert "最大APIリクエスト" in plan and "0回" in plan
    assert "API利用なし" in plan
    assert "外部モデル利用" not in plan
    assert "振る舞い検証: PASS" in result
    assert "地域イベント" in result
    assert "参加者が関心のある催しへ参加意思を残せる" in result


def test_approved_story_remains_visible_from_verification_through_result(project: Path) -> None:
    application = create_portal_application(project, provider_factory=SampleContentProvider)
    project_id = create_bet(application)
    actor = "AIへ開発を任せるPM"
    pain = "意図と成果物がずれ、何を正とすべきか判断できない"
    outcome = "委譲した成果を事業意図に照らして判断できる"
    request(application, f"/projects/{project_id}/problem", "POST", {"actor": actor, "pain": pain})
    request(
        application,
        f"/projects/{project_id}/outcomes",
        "POST",
        {"outcome": outcome, "journey": "意図を伝える → 委譲する → 証拠で判断する"},
    )

    _, _, verification = request(application, f"/projects/{project_id}")
    request(application, f"/projects/{project_id}/verification", "POST")
    _, _, generation = request(application, f"/projects/{project_id}")
    request(application, f"/projects/{project_id}/generate", "POST", {"consent": "yes"})
    wait_for(application, project_id, "委譲結果と証拠")
    _, _, ready = request(application, f"/projects/{project_id}")
    _, _, result = request(application, f"/projects/{project_id}/result")

    for page in (verification, generation, ready, result):
        assert actor in page
        assert pain in page
        assert outcome in page
        assert "この開発が解決すること" in page


def test_delegation_result_distinguishes_proof_sample_and_reports_origin_evidence(
    project: Path,
) -> None:
    application = create_portal_application(project, provider_factory=SampleContentProvider)
    project_id = create_bet(application)
    advance_to_generation(application, project_id)
    request(application, f"/projects/{project_id}/generate", "POST", {"consent": "yes"})
    wait_for(application, project_id, "委譲結果と証拠")

    _, _, result = request(application, f"/projects/{project_id}/result")
    evidence = yaml.safe_load(
        (project / ".dodai/workspaces" / project_id / "projections/evidence.yaml").read_text()
    )

    assert "委譲結果と証拠" in result
    assert "満たした検証" in result
    assert "満たしていない検証" in result
    assert "証明用サンプル" in result
    assert "待機リストを作ることがDodaiの価値ではありません" in result
    assert {item["path"] for item in evidence["presentations"]} == {
        "developer/waitlist.py",
        "developer/test_waitlist.py",
        "stakeholder/brief.md",
    }
    assert all(item["story"] == "story_primary_pain" for item in evidence["presentations"])
    assert all(item["criterion"] == "ac_primary_outcome" for item in evidence["presentations"])
    assert all(
        item["specification"] == "spec_primary_outcome_is_observable"
        for item in evidence["presentations"]
    )


def test_outcome_evidence_identifies_the_failed_layer_and_next_change(project: Path) -> None:
    application = create_portal_application(project, provider_factory=SampleContentProvider)
    project_id = create_bet(application)
    advance_to_generation(application, project_id)
    request(application, f"/projects/{project_id}/generate", "POST", {"consent": "yes"})
    wait_for(application, project_id, "委譲結果と証拠")

    expected = {
        "problem_not_observed": ("課題の見立て", "第2層"),
        "behavior_passed_outcome_failed": ("確かめ方", "第4層"),
        "behavior_failed": ("生成された成果", "Presentation"),
        "insufficient_evidence": ("判断不能", "追加の証拠"),
    }
    for evidence_kind, phrases in expected.items():
        _, _, page = request(
            application,
            f"/projects/{project_id}/telemetry",
            "POST",
            {"evidence_kind": evidence_kind, "evidence": "観測した事実"},
        )
        assert all(phrase in page for phrase in phrases)
        assert "固定するもの" in page
        assert "次に変えるもの" in page
