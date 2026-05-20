"""
Nexus Judge Agent
Single-purpose: Evaluate if an action succeeded or failed.
Returns structured Pass/Fail with feedback.
Inspired by Google's Judge with Pydantic schema.
No LLM. Pure Python logic comparing screen states.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phone_bridge.screen_reader import ScreenReader
from phone_bridge.bridge import PhoneBridge


class JudgeVerdict:
    """Structured output from the Judge Agent."""
    
    def __init__(self, status: str, feedback: str, details: dict = None):
        self.status = status      # "pass" or "fail"
        self.feedback = feedback  # Human-readable explanation
        self.details = details or {}
    
    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "feedback": self.feedback,
            "details": self.details,
        }
    
    def is_pass(self) -> bool:
        return self.status == "pass"
    
    def __repr__(self):
        icon = "✅" if self.is_pass() else "❌"
        return f"<Judge: {icon} {self.feedback[:50]}>"


class JudgeAgent:
    """
    Evaluates if an action succeeded by comparing screen states.
    
    Usage:
        judge = JudgeAgent(bridge)
        verdict = judge.evaluate(before_elements, after_elements, expected_change)
        if verdict.is_pass():
            print("Action succeeded!")
    """
    
    def __init__(self, bridge: PhoneBridge = None):
        self.bridge = bridge or PhoneBridge()
        self.reader = ScreenReader()
    
    def capture_screen(self) -> list:
        """Capture current screen state as a list of element labels."""
        elements = self.reader.get_clickable_elements()
        return [e.label for e in elements if e.label]
    
    def evaluate(self, before_labels: list, after_labels: list, 
                 expected: dict = None) -> JudgeVerdict:
        """
        Compare screen before and after an action.
        
        Args:
            before_labels: List of element labels before action
            after_labels: List of element labels after action
            expected: Optional dict with:
                - appeared: List of labels that SHOULD appear
                - disappeared: List of labels that SHOULD disappear
                - min_new_elements: Minimum new elements expected
                - screen_type: Expected screen type after action
        
        Returns:
            JudgeVerdict with pass/fail and feedback
        """
        expected = expected or {}
        
        before_set = set(before_labels)
        after_set = set(after_labels)
        
        new_elements = after_set - before_set
        removed_elements = before_set - after_set
        
        details = {
            "before_count": len(before_set),
            "after_count": len(after_set),
            "new_elements": list(new_elements)[:10],
            "removed_elements": list(removed_elements)[:10],
        }
        
        # Check: Screen didn't change at all
        if len(new_elements) == 0 and len(removed_elements) == 0:
            # BUT: if element count changed, screen DID change (state change)
            if details["before_count"] != details["after_count"]:
                return JudgeVerdict(
                    "pass",
                    f"Screen state changed ({details['before_count']} → {details['after_count']} elements).",
                    details
                )
            return JudgeVerdict(
                "fail",
                "Screen did not change. Action may not have executed.",
                details
            )
        
        # Check: Expected elements appeared
        if "appeared" in expected:
            for label in expected["appeared"]:
                found = any(label.lower() in e.lower() for e in after_set)
                if not found:
                    return JudgeVerdict(
                        "fail",
                        f"Expected element '{label}' did not appear on screen.",
                        details
                    )
        
        # Check: Expected elements disappeared
        if "disappeared" in expected:
            for label in expected["disappeared"]:
                found = any(label.lower() in e.lower() for e in after_set)
                if found:
                    return JudgeVerdict(
                        "fail",
                        f"Expected element '{label}' is still on screen.",
                        details
                    )
        
        # Check: Minimum new elements
        min_new = expected.get("min_new_elements", 0)
        if len(new_elements) < min_new:
            return JudgeVerdict(
                "fail",
                f"Only {len(new_elements)} new elements. Expected at least {min_new}.",
                details
            )
        
        # All checks passed
        return JudgeVerdict(
            "pass",
            f"Screen changed correctly. {len(new_elements)} new elements.",
            details
        )
    
    def verify_action(self, action_name: str, before_labels: list, 
                      expected: dict = None) -> JudgeVerdict:
        """
        Full verification: capture after state, evaluate, return verdict.
        """
        time.sleep(0.5)  # Wait for UI to settle
        after_labels = self.capture_screen()
        
        return self.evaluate(before_labels, after_labels, expected)


# ─── Independent Test ──────────────────────────────
if __name__ == "__main__":
    print("⚖️  Judge Agent - Independent Test\n")
    
    # Test 1: Simulate a successful action
    print("Test 1: Successful screen change")
    before = ["Folder", "Calendar", "Clock", "Camera", "Settings"]
    after = ["Chats", "Updates", "Calls", "Communities", "New chat", "Camera", "Search"]
    judge = JudgeAgent()
    verdict = judge.evaluate(before, after, {"appeared": ["Chats", "Updates"]})
    print(f"   {verdict}")
    print(f"   Details: {verdict.details}")
    print()
    
    # Test 2: Simulate a failed action (no change)
    print("Test 2: No screen change (failed action)")
    before2 = ["Folder", "Calendar", "Clock"]
    after2 = ["Folder", "Calendar", "Clock"]
    verdict2 = judge.evaluate(before2, after2)
    print(f"   {verdict2}")
    print()
    
    # Test 3: Simulate missing expected element
    print("Test 3: Missing expected element")
    before3 = ["Folder", "Calendar"]
    after3 = ["Folder", "Calendar", "Weather"]
    verdict3 = judge.evaluate(before3, after3, {"appeared": ["WhatsApp"]})
    print(f"   {verdict3}")
    print()
    
    # Test 4: Live test (if phone connected)
    print("Test 4: Live phone test")
    try:
        bridge = PhoneBridge()
        bridge.device_ip = "192.168.100.10"
        if bridge.connect(port="35543"):
            live_judge = JudgeAgent(bridge)
            before_labels = live_judge.capture_screen()
            print(f"   Captured {len(before_labels)} elements")
            
            # Press home
            bridge.press_key(3)
            time.sleep(0.5)
            
            verdict4 = live_judge.verify_action("go_home", before_labels)
            print(f"   {verdict4}")
    except Exception as e:
        print(f"   Live test skipped: {e}")
