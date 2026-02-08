"""Concept lookup with Browserbase web search fallback.

Uses Browserbase to search Python docs / Stack Overflow when a concept
isn't in the local static KB. Falls back gracefully if Browserbase is unavailable.
"""

from __future__ import annotations

import os
import re
from typing import Dict, Optional

try:
    from browserbase import Browserbase
except ImportError:
    Browserbase = None

try:
    import httpx
except ImportError:
    httpx = None


class ConceptLookup:
    _STATIC_KB: Dict[str, str] = {
        "forward chaining": (
            "Forward-chaining engines evaluate rules against current facts and "
            "fire each matching rule; conflict resolution decides order."
        ),
        "first-match-wins": (
            "First-match-wins means pick one winning rule from a group after sorting "
            "by priority and tie-breakers, then ignore the rest of that group."
        ),
        "snapshot": (
            "Snapshot/restore usually stores a deep copy of mutable state at a timestamp "
            "and restores that copy later."
        ),
        "restore": (
            "Restore should replace current rule state from a stored snapshot, while "
            "leaving audit history untouched unless explicitly rolled back."
        ),
        "deepcopy": (
            "deepcopy recursively copies nested containers so future mutations do not "
            "affect saved snapshots."
        ),
        "rule engine": (
            "A rule engine evaluates a set of rules against input data. Each rule has "
            "a condition (predicate) and an action. The engine iterates through rules, "
            "checks conditions against the data, and fires actions for matching rules. "
            "Common patterns include forward chaining, first-match-wins, and priority-based ordering."
        ),
        "operator": (
            "Comparison operators for rule conditions: eq (equal), neq (not equal), "
            "gt (greater than), lt (less than), gte (greater than or equal), "
            "lte (less than or equal). Implement each as a callable that takes "
            "(actual_value, expected_value) and returns a boolean."
        ),
        "compound condition": (
            "Compound conditions combine multiple simple conditions using logical "
            "operators AND and OR. AND requires all sub-conditions to be true; "
            "OR requires at least one. They can be nested for complex logic. "
            "Represent them as a tree with 'all' (AND) and 'any' (OR) nodes."
        ),
        "priority": (
            "Rule priority determines evaluation order. Higher-priority rules are "
            "evaluated first. When multiple rules match, priority decides which fires. "
            "Use numeric priority (higher number = higher priority) and support "
            "tie-breaking by rule insertion order or name."
        ),
        "group": (
            "Rule groups partition rules into named sets. Within a group, rules are "
            "sorted by priority and the first matching rule wins (first-match-wins). "
            "Groups can be evaluated independently or in sequence. Each group acts "
            "as an isolated decision unit."
        ),
        "audit": (
            "Audit trails record every rule evaluation: which rules were checked, "
            "which matched, which fired, the input data, and timestamps. Store "
            "evaluation history as a list of records with rule_id, matched (bool), "
            "fired (bool), and the data snapshot at evaluation time."
        ),
        "evaluate": (
            "Rule evaluation checks each rule's condition against the input data. "
            "For simple conditions, extract the field from data, apply the operator, "
            "and compare to the expected value. For compound conditions, recursively "
            "evaluate sub-conditions. Return the list of matching/fired rules."
        ),
    }

    def __init__(self):
        self._bb_client: Optional[object] = None
        self._bb_project_id: Optional[str] = None
        api_key = os.environ.get("BROWSERBASE_API_KEY")
        project_id = os.environ.get("BROWSERBASE_PROJECT_ID")
        if Browserbase and api_key and project_id:
            try:
                self._bb_client = Browserbase(api_key=api_key)
                self._bb_project_id = project_id
            except Exception:
                pass

    def lookup(self, query: str) -> str:
        normalized = query.lower().strip()

        # Check static KB first
        for key, summary in self._STATIC_KB.items():
            if key in normalized:
                return summary

        # Try Browserbase web search, fall back to plain DuckDuckGo
        if httpx:
            try:
                if self._bb_client:
                    result = self._browserbase_search(query)
                else:
                    result = self._fallback_ddg_search(query)
                if result:
                    return result
            except Exception:
                pass

        return (
            "I could not find a direct match in the local concept cache. "
            "For this project, prefer concise explanations focused on rule evaluation, "
            "ordering, grouping, and snapshot semantics."
        )

    def _browserbase_search(self, query: str) -> Optional[str]:
        """Use Browserbase session to search Python docs via DuckDuckGo."""
        if not self._bb_client or not httpx:
            return None

        session_id = None
        try:
            session = self._bb_client.sessions.create(project_id=self._bb_project_id)
            session_id = session.id

            search_q = f"python {query} site:docs.python.org"
            headers = {
                "User-Agent": "Mozilla/5.0",
                "x-bb-session-id": session_id,
                "x-bb-api-key": os.environ.get("BROWSERBASE_API_KEY", ""),
            }
            response = httpx.get(
                "https://html.duckduckgo.com/html/",
                params={"q": search_q},
                headers=headers,
                timeout=10.0,
                follow_redirects=True,
            )

            if response.status_code == 200:
                snippets = self._extract_ddg_snippets(response.text, max_results=3)
                if snippets:
                    return " | ".join(snippets)

        except Exception:
            result = self._fallback_ddg_search(query)
            if result:
                return result
        finally:
            if session_id:
                try:
                    self._bb_client.sessions.update(session_id, status="REQUEST_RELEASE")
                except Exception:
                    pass

        return None

    def _fallback_ddg_search(self, query: str) -> Optional[str]:
        """Plain httpx DuckDuckGo search when Browserbase is unavailable."""
        if not httpx:
            return None
        try:
            search_q = f"python {query} site:docs.python.org"
            response = httpx.get(
                "https://html.duckduckgo.com/html/",
                params={"q": search_q},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=8.0,
                follow_redirects=True,
            )
            if response.status_code == 200:
                snippets = self._extract_ddg_snippets(response.text, max_results=3)
                if snippets:
                    return " | ".join(snippets)
        except Exception:
            pass
        return None

    @staticmethod
    def _extract_ddg_snippets(html: str, max_results: int = 3) -> list[str]:
        snippets: list[str] = []
        marker = 'class="result__snippet"'
        pos = 0
        while len(snippets) < max_results:
            idx = html.find(marker, pos)
            if idx == -1:
                break
            tag_close = html.find(">", idx)
            if tag_close == -1:
                break
            end_tag = html.find("</", tag_close)
            if end_tag == -1:
                break
            raw = html[tag_close + 1 : end_tag]
            text = re.sub(r"<[^>]+>", "", raw).strip()
            if text:
                snippets.append(text)
            pos = end_tag
        return snippets
