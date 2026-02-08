"""HTTP client for the assessment backend APIs."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Dict, Optional


class BackendClientError(RuntimeError):
    pass


class AssessmentBackendClient:
    def __init__(self, base_url: str, timeout_seconds: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _request(self, method: str, path: str, payload: Optional[Dict] = None) -> Dict:
        url = f"{self.base_url}{path}"
        body = None
        headers = {}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url=url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8")
            raise BackendClientError(
                f"{method} {path} failed ({exc.code}): {detail or exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise BackendClientError(f"{method} {path} failed: {exc.reason}") from exc
        if not raw:
            return {}
        return json.loads(raw)

    def list_questions(self) -> list[str]:
        data = self._request("GET", "/api/questions")
        return data.get("questions", [])

    def get_question(self, question_name: str) -> Dict:
        return self._request("GET", f"/api/questions/{question_name}")

    def start_assessment(
        self,
        question_name: str,
        duration_minutes: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> Dict:
        payload: Dict[str, object] = {"question_name": question_name}
        if duration_minutes is not None:
            payload["duration_minutes"] = duration_minutes
        if user_id:
            payload["user_id"] = user_id
        return self._request("POST", "/api/assessment/start", payload)

    def execute_tests(self, session_id: str, question_name: str, files: Dict[str, str]) -> Dict:
        payload = {
            "session_id": session_id,
            "question_name": question_name,
            "files": files,
        }
        return self._request("POST", "/api/execute", payload)

