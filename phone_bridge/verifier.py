"""
Nexus TPM Verifier
Self-learning layer. Verifies every action, records results, improves over time.
After each action: screenshot → read screen → verify → learn → improve.
"""

import json
import time
import os
import sys
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phone_bridge.bridge import PhoneBridge
from phone_bridge.screen_reader import ScreenReader


class ActionRecord:
    """A single recorded action with its result."""

    def __init__(self, action_name: str, params: dict, success: bool, details: dict = None):
        self.action_name = action_name
        self.params = params
        self.success = success
        self.timestamp = datetime.now().isoformat()
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "action": self.action_name,
            "params": self.params,
            "success": self.success,
            "timestamp": self.timestamp,
            "details": self.details,
        }


class TPMVerifier:
    """
    Verifies actions by checking the screen after execution.
    Learns what works and what doesn't. Updates confidence scores.
    """

    def __init__(self, bridge: PhoneBridge = None):
        self.bridge = bridge or PhoneBridge()
        self.reader = ScreenReader()
        self.history_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "action_history.json"
        )
        self.learned_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "learned_patterns.json"
        )
        self.history = self._load(self.history_path, [])
        self.learned = self._load(self.learned_path, {})

    def _load(self, path: str, default) -> any:
        """Load JSON file or return default."""
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return default

    def _save(self, path: str, data):
        """Save data to JSON file."""
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    # ─── VERIFICATION ────────────────────────────

    def verify_screen_changed(self, before_elements: list, after_elements: list) -> dict:
        """
        Compare screen before and after an action.
        Returns verdict: did the screen change meaningfully?
        """
        before_count = len(before_elements)
        after_count = len(after_elements)

        # Count changed elements
        before_labels = {e.label for e in before_elements if e.label}
        after_labels = {e.label for e in after_elements if e.label}

        new_elements = after_labels - before_labels
        removed_elements = before_labels - after_labels

        changed = len(new_elements) > 0 or len(removed_elements) > 0 or before_count != after_count

        return {
            "changed": changed,
            "before_count": before_count,
            "after_count": after_count,
            "new_elements": list(new_elements)[:10],
            "removed_elements": list(removed_elements)[:10],
        }

    def verify_element_appeared(self, label_contains: str, timeout: float = 3.0) -> bool:
        """
        Wait for an element to appear on screen.
        Returns True if it appeared within timeout.
        """
        start = time.time()
        while time.time() - start < timeout:
            elements = self.reader.find_by_text(label_contains)
            if elements:
                return True
            time.sleep(0.3)
        return False

    def verify_element_gone(self, label_contains: str) -> bool:
        """Check that an element is NO LONGER on screen."""
        elements = self.reader.find_by_text(label_contains)
        return len(elements) == 0

    # ─── ACTION EXECUTION WITH VERIFICATION ───────

    def execute_and_verify(
        self, action_name: str, action_func, params: dict = None,
        expected_element: str = None, expected_gone: str = None
    ) -> ActionRecord:
        """
        Execute an action, verify it worked, and record the result.
        
        Args:
            action_name: Name of the action (e.g., "send_whatsapp")
            action_func: Function to call (no arguments)
            params: Parameters passed to the action
            expected_element: Label of element that should appear after success
            expected_gone: Label of element that should disappear after success
        
        Returns:
            ActionRecord with success/failure and details
        """
        params = params or {}

        # Capture screen BEFORE
        before_elements = self.reader.get_clickable_elements()

        # Execute the action
        try:
            result = action_func()
        except Exception as e:
            record = ActionRecord(action_name, params, False, {"error": str(e)})
            self.history.append(record.to_dict())
            self._save(self.history_path, self.history)
            return record

        # Small wait for UI to respond
        time.sleep(0.5)

        # Capture screen AFTER
        after_elements = self.reader.get_clickable_elements()

        # Verify
        verification = self.verify_screen_changed(before_elements, after_elements)

        # Check specific expectations
        element_appeared = True
        if expected_element:
            element_appeared = self.verify_element_appeared(expected_element)

        element_gone = True
        if expected_gone:
            element_gone = self.verify_element_gone(expected_gone)

        success = verification["changed"] and element_appeared and element_gone

        # Build record
        details = {
            "verification": verification,
            "element_appeared": element_appeared,
            "element_gone": element_gone,
        }

        record = ActionRecord(action_name, params, success, details)
        self.history.append(record.to_dict())
        self._save(self.history_path, self.history)

        # Learn from this action
        if success:
            self._learn_success(action_name, params, verification)
        else:
            self._learn_failure(action_name, params, verification)

        return record

    # ─── LEARNING ─────────────────────────────────

    def _learn_success(self, action_name: str, params: dict, verification: dict):
        """Record a successful action pattern."""
        if action_name not in self.learned:
            self.learned[action_name] = {
                "successes": 0,
                "failures": 0,
                "last_success": None,
                "confidence": 0.0,
                "best_params": None,
            }

        entry = self.learned[action_name]
        entry["successes"] += 1
        entry["last_success"] = datetime.now().isoformat()
        entry["confidence"] = entry["successes"] / (entry["successes"] + entry["failures"])
        entry["best_params"] = params

        self._save(self.learned_path, self.learned)

    def _learn_failure(self, action_name: str, params: dict, verification: dict):
        """Record a failed action for future improvement."""
        if action_name not in self.learned:
            self.learned[action_name] = {
                "successes": 0,
                "failures": 0,
                "last_failure": None,
                "confidence": 0.0,
            }

        entry = self.learned[action_name]
        entry["failures"] += 1
        entry["last_failure"] = datetime.now().isoformat()
        entry["confidence"] = entry["successes"] / (entry["successes"] + entry["failures"]) if (entry["successes"] + entry["failures"]) > 0 else 0.0

        self._save(self.learned_path, self.learned)

    # ─── QUERIES ──────────────────────────────────

    def get_confidence(self, action_name: str) -> float:
        """Get confidence score for an action (0.0 to 1.0)."""
        entry = self.learned.get(action_name, {})
        return entry.get("confidence", 0.0)

    def get_best_params(self, action_name: str) -> Optional[dict]:
        """Get the best-known parameters for an action."""
        entry = self.learned.get(action_name, {})
        return entry.get("best_params")

    def get_recent_history(self, limit: int = 10) -> list:
        """Get recent action history."""
        return self.history[-limit:]

    def get_stats(self) -> dict:
        """Get overall learning statistics."""
        total = len(self.history)
        successes = sum(1 for h in self.history if h.get("success"))
        return {
            "total_actions": total,
            "successes": successes,
            "failures": total - successes,
            "success_rate": successes / total if total > 0 else 0.0,
            "learned_actions": len(self.learned),
        }

    def print_stats(self):
        """Print learning statistics."""
        stats = self.get_stats()
        print("\n   📊 TPM LEARNING STATS")
        print(f"   Total actions: {stats['total_actions']}")
        print(f"   Successes: {stats['successes']}")
        print(f"   Failures: {stats['failures']}")
        print(f"   Success rate: {stats['success_rate']:.0%}")
        print(f"   Learned actions: {stats['learned_actions']}")
        print()
        for action, data in self.learned.items():
            conf = data.get("confidence", 0.0)
            bar = "█" * int(conf * 10) + "░" * (10 - int(conf * 10))
            print(f"   {action:25s} [{bar}] {conf:.0%}")


# ─── Quick Test ────────────────────────────────────
if __name__ == "__main__":
    print("TPM Verifier loaded.")
    print("Learning from every action. Getting smarter every time.")
    print()
    print("Usage:")
    print("  verifier = TPMVerifier(bridge)")
    print("  record = verifier.execute_and_verify('open_app',")
    print("      lambda: bridge.open_app('com.whatsapp'),")
    print("      expected_element='Chats')")
    print("  verifier.print_stats()")
