"""Session log structure with Notion page upload via Notion API.

Creates rich Notion pages with session data: mode switches, struggle moments,
test timeline, and final code.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class SessionJournal:
    question_name: str
    mode_switches: List[Dict[str, object]] = field(default_factory=list)
    struggle_moments: List[Dict[str, object]] = field(default_factory=list)
    browserbase_lookups: List[Dict[str, str]] = field(default_factory=list)
    test_timeline: List[Dict[str, object]] = field(default_factory=list)
    final_code: Optional[str] = None

    def log_mode_switch(self, previous: str, current: str, trigger: str, timestamp: float) -> None:
        self.mode_switches.append(
            {
                "timestamp": timestamp,
                "previous": previous,
                "current": current,
                "trigger": trigger,
            }
        )

    def log_struggle(self, kind: str, timestamp: float, context: Dict[str, object]) -> None:
        self.struggle_moments.append(
            {
                "timestamp": timestamp,
                "kind": kind,
                "context": context,
            }
        )

    def log_lookup(self, query: str, summary: str) -> None:
        self.browserbase_lookups.append({"query": query, "summary": summary})

    def log_test_result(self, stage_index: int, visible_passed: int, visible_total: int) -> None:
        self.test_timeline.append(
            {
                "stage_index": stage_index,
                "visible_passed": visible_passed,
                "visible_total": visible_total,
            }
        )

    def set_final_code(self, code: str) -> None:
        self.final_code = code

    def to_dict(self) -> Dict[str, object]:
        return {
            "question_name": self.question_name,
            "mode_switches": self.mode_switches,
            "struggle_moments": self.struggle_moments,
            "browserbase_lookups": self.browserbase_lookups,
            "test_timeline": self.test_timeline,
            "final_code": self.final_code,
        }

    def save(self, output_path: str | Path) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    def upload_to_notion(self) -> Optional[str]:
        """Upload session journal as a Notion page. Returns the page URL or None."""
        api_key = os.environ.get("NOTION_API_KEY")
        parent_page_id = os.environ.get("NOTION_PARENT_PAGE_ID")
        if not api_key or not parent_page_id:
            return None

        try:
            from notion_client import Client
            notion = Client(auth=api_key)

            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            title = f"Session: {self.question_name} — {now}"

            # Build content blocks
            children = []

            # Header
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Session Summary"}}]
                }
            })

            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {
                        "content": f"Question: {self.question_name} | Logged: {now}"
                    }}]
                }
            })

            # Test Timeline
            if self.test_timeline:
                children.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "Test Timeline"}}]
                    }
                })
                for entry in self.test_timeline:
                    stage = entry.get("stage_index", 0)
                    passed = entry.get("visible_passed", 0)
                    total = entry.get("visible_total", 0)
                    status = "passed" if passed == total else f"{passed}/{total}"
                    children.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {
                                "content": f"Level {stage + 1}: {status}"
                            }}]
                        }
                    })

            # Struggle Moments
            if self.struggle_moments:
                children.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "Struggle Moments"}}]
                    }
                })
                for moment in self.struggle_moments:
                    ts = moment.get("timestamp", 0)
                    kind = moment.get("kind", "unknown")
                    time_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "—"
                    children.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {
                                "content": f"[{time_str}] {kind}"
                            }}]
                        }
                    })

            # Mode Switches
            if self.mode_switches:
                children.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "Mode Switches"}}]
                    }
                })
                for switch in self.mode_switches:
                    prev = switch.get("previous", "?")
                    curr = switch.get("current", "?")
                    trigger = switch.get("trigger", "?")
                    children.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {
                                "content": f"{prev} → {curr} (trigger: {trigger})"
                            }}]
                        }
                    })

            # Concept Lookups
            if self.browserbase_lookups:
                children.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "Concept Lookups"}}]
                    }
                })
                for lookup in self.browserbase_lookups:
                    children.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {
                                "content": f"Q: {lookup.get('query', '')} → {lookup.get('summary', '')[:100]}"
                            }}]
                        }
                    })

            # Final Code
            if self.final_code:
                children.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "Final Code"}}]
                    }
                })
                # Notion code blocks have a 2000 char limit per block
                code = self.final_code
                for i in range(0, len(code), 1900):
                    chunk = code[i:i+1900]
                    children.append({
                        "object": "block",
                        "type": "code",
                        "code": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}],
                            "language": "python"
                        }
                    })

            # Create the page
            page = notion.pages.create(
                parent={"page_id": parent_page_id},
                properties={
                    "title": {
                        "title": [{"type": "text", "text": {"content": title}}]
                    }
                },
                children=children,
            )

            return page.get("url", None)

        except Exception as e:
            print(f"Notion upload failed: {e}")
            return None
