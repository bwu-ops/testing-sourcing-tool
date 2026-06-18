from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Coroutine
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from tornado.testing import AsyncHTTPTestCase

from api.auth.providers import peek_code_for_test
from api.auth.rate_limit import rate_limiter
from api.db import dispose_db
from api.main import create_app
from api.settings import clear_settings_cache


def _run_async(coro: Coroutine[Any, Any, object]) -> None:
    try:
        asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(coro)
        loop.close()


class TestGraphQLSourcing(AsyncHTTPTestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory(prefix="scaffold-sourcing-")
        self.db_path = Path(self.temp_dir.name) / "app.db"
        os.environ["APP_ENV"] = "test"
        os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{self.db_path}"
        os.environ["SESSION_SECRET"] = "test-session-secret"
        os.environ["AUTH_ALLOWED_EMAIL_DOMAINS"] = "example.com"
        os.environ["AUTH_PROVIDER"] = "console"
        os.environ["LLM_PROVIDER"] = "mock"
        clear_settings_cache()
        rate_limiter.clear()
        _run_async(dispose_db())
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()
        clear_settings_cache()
        rate_limiter.clear()
        _run_async(dispose_db())
        self.temp_dir.cleanup()

    def get_app(self):  # type: ignore[no-untyped-def]
        return create_app()

    def _authenticate(self, email: str) -> str:
        start_response = self.fetch(
            "/api/auth/start",
            method="POST",
            body=json.dumps({"email": email}),
        )
        assert start_response.code == 200
        code = peek_code_for_test(email)
        assert code is not None
        verify_response = self.fetch(
            "/api/auth/verify",
            method="POST",
            body=json.dumps({"email": email, "code": code}),
        )
        assert verify_response.code == 200
        cookie_header = verify_response.headers.get("Set-Cookie")
        assert cookie_header is not None
        return cookie_header.split(";", maxsplit=1)[0]

    def _graphql(self, cookie: str, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.fetch(
            "/graphql",
            method="POST",
            headers={"Cookie": cookie},
            body=json.dumps({"query": query, "variables": variables or {}}),
        )
        assert response.code == 200
        payload = json.loads(response.body.decode("utf-8"))
        assert "errors" not in payload, payload.get("errors")
        return payload["data"]

    def test_create_project_generates_calibration_strategy(self) -> None:
        cookie = self._authenticate("builder@example.com")

        data = self._graphql(
            cookie,
            """
            mutation CreateSourcingProject($input: CreateSourcingProjectInput!) {
              createSourcingProject(input: $input) {
                id
                name
                status
                generatedTargetCompanies
                generatedScorecard
                searchKeywords
              }
            }
            """,
            {
                "input": {
                    "jobDescription": "Backend software engineer for a seed-stage stablecoin payments company in NYC.",
                    "companyWebsite": "https://example-fintech.test",
                    "notes": "Prioritize payments infrastructure and stablecoin experience.",
                }
            },
        )

        project = data["createSourcingProject"]
        assert project["status"] == "awaiting_calibration"
        assert "Stripe" in project["generatedTargetCompanies"]
        assert "Circle" in project["generatedTargetCompanies"]
        assert "Software engineering experience" in project["generatedScorecard"]
        assert "stablecoin" in project["searchKeywords"]

    def test_approve_and_run_search_creates_linkedin_backed_candidates(self) -> None:
        cookie = self._authenticate("builder@example.com")
        project = self._graphql(
            cookie,
            """
            mutation CreateSourcingProject($input: CreateSourcingProjectInput!) {
              createSourcingProject(input: $input) { id }
            }
            """,
            {
                "input": {
                    "jobDescription": "Software engineer for payments infrastructure in New York City.",
                    "companyWebsite": "https://portfolio.example",
                    "notes": "",
                }
            },
        )["createSourcingProject"]

        approved = self._graphql(
            cookie,
            """
            mutation Approve($input: ApproveSourcingCalibrationInput!) {
              approveSourcingProjectCalibration(input: $input) {
                id
                status
                approvedTargetCompanies
                approvedScorecard
              }
            }
            """,
            {
                "input": {
                    "projectId": project["id"],
                    "targetCompanies": ["Stripe", "Circle"],
                    "scorecard": [
                        "Software engineering experience",
                        "Payments or stablecoin domain experience",
                        "NYC location signal",
                    ],
                }
            },
        )["approveSourcingProjectCalibration"]
        assert approved["status"] == "calibrated"
        assert approved["approvedTargetCompanies"] == ["Stripe", "Circle"]

        searched = self._graphql(
            cookie,
            """
            mutation RunSearch($projectId: String!) {
              runSourcingProjectSearch(projectId: $projectId) {
                id
                status
                projectCandidates {
                  candidate {
                    fullName
                    linkedinUrl
                    currentCompany
                  }
                  fitScore
                  mustHaveScore
                  sourceConfidence
                  rationale
                }
              }
            }
            """,
            {"projectId": project["id"]},
        )["runSourcingProjectSearch"]

        assert searched["status"] == "ready_for_review"
        assert len(searched["projectCandidates"]) == 2
        for project_candidate in searched["projectCandidates"]:
            candidate = project_candidate["candidate"]
            assert candidate["linkedinUrl"].startswith("https://www.linkedin.com/in/")
            assert candidate["currentCompany"] in {"Stripe", "Circle"}
            assert project_candidate["fitScore"] >= 70
            assert project_candidate["mustHaveScore"] == "3/5"
            assert project_candidate["sourceConfidence"] in {"medium", "high"}

    def test_candidate_records_are_deduplicated_across_projects(self) -> None:
        cookie = self._authenticate("builder@example.com")

        def create_approved_project() -> str:
            project = self._graphql(
                cookie,
                """
                mutation CreateSourcingProject($input: CreateSourcingProjectInput!) {
                  createSourcingProject(input: $input) { id }
                }
                """,
                {
                    "input": {
                        "jobDescription": "Software engineer with payments experience in NYC.",
                        "companyWebsite": "https://portfolio.example",
                    }
                },
            )["createSourcingProject"]
            self._graphql(
                cookie,
                """
                mutation Approve($input: ApproveSourcingCalibrationInput!) {
                  approveSourcingProjectCalibration(input: $input) { id }
                }
                """,
                {
                    "input": {
                        "projectId": project["id"],
                        "targetCompanies": ["Stripe"],
                        "scorecard": ["Software engineering experience", "Payments domain experience"],
                    }
                },
            )
            return str(project["id"])

        first_project_id = create_approved_project()
        second_project_id = create_approved_project()
        self._graphql(
            cookie,
            "mutation RunSearch($projectId: String!) { runSourcingProjectSearch(projectId: $projectId) { id } }",
            {"projectId": first_project_id},
        )
        self._graphql(
            cookie,
            "mutation RunSearch($projectId: String!) { runSourcingProjectSearch(projectId: $projectId) { id } }",
            {"projectId": second_project_id},
        )

        data = self._graphql(
            cookie,
            """
            query SourcingData {
              sourcingProjects {
                id
                projectCandidates { candidate { linkedinSlug } }
              }
              candidates { id linkedinSlug associatedProjectCount }
            }
            """,
        )

        assert len(data["sourcingProjects"]) == 2
        assert len(data["candidates"]) == 1
        assert data["candidates"][0]["linkedinSlug"] == "alex-stripe-nyc"
        assert data["candidates"][0]["associatedProjectCount"] == 2
