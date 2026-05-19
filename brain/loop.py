"""
Nexus Loop Agent
Single-purpose: Execute an action, judge the result, retry if failed.
Max 3 attempts. Each retry tries a different approach.
Inspired by Google's LoopAgent with EscalationChecker.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LoopResult:
    """Structured output from the Loop Agent."""
    
    def __init__(self, success: bool, attempts: int, verdicts: list, final_output: any = None):
        self.success = success
        self.attempts = attempts
        self.verdicts = verdicts
        self.final_output = final_output
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "attempts": self.attempts,
            "verdicts": [v.to_dict() for v in self.verdicts],
        }
    
    def __repr__(self):
        status = "✅" if self.success else "❌"
        return f"<Loop: {status} {self.attempts} attempt(s)>"


class SimpleVerdict:
    """Simple verdict when no Judge agent is provided."""
    def __init__(self, changed, expected, after_labels=None):
        self._changed = changed
        self._expected = expected
        self._after_labels = after_labels or []
    
    def is_pass(self):
        if self._expected and "appeared" in self._expected:
            return any(
                any(e_label.lower() in a.lower() for a in self._after_labels)
                for e_label in self._expected["appeared"]
            )
        return self._changed
    
    @property
    def status(self):
        return "pass" if self.is_pass() else "fail"
    
    @property
    def feedback(self):
        return "Screen changed" if self._changed else "No change"
    
    def to_dict(self):
        return {"status": self.status, "feedback": self.feedback}
    
    def __repr__(self):
        icon = "✅" if self.is_pass() else "❌"
        return f"<Judge: {icon} {self.feedback}>"


class FailedVerdict:
    """Verdict for when execution crashes."""
    def __init__(self, error_msg):
        self._error = error_msg
    
    def is_pass(self):
        return False
    
    @property
    def status(self):
        return "fail"
    
    @property
    def feedback(self):
        return str(self._error)
    
    def to_dict(self):
        return {"status": "fail", "feedback": str(self._error)}
    
    def __repr__(self):
        return f"<Judge: ❌ {self._error}>"


class LoopAgent:
    """
    Executes an action, judges the result, retries with alternatives if failed.
    Max 3 attempts. Stops immediately on first success.
    
    Usage:
        loop = LoopAgent(judge, max_attempts=3)
        result = loop.execute_with_retry(
            action_name="open_whatsapp",
            action_func=lambda: bridge.open_app("com.whatsapp"),
            verifier_func=lambda: judge.capture_screen(),
            expected={"appeared": ["Chats", "Updates"]}
        )
    """
    
    def __init__(self, judge=None, max_attempts: int = 3):
        self.judge = judge
        self.max_attempts = max_attempts
    
    def execute_with_retry(self, action_name: str, action_func, 
                          verifier_func, expected: dict = None,
                          alternative_funcs: list = None) -> LoopResult:
        """
        Try to execute an action. If it fails, try alternatives.
        
        Args:
            action_name: Name of the action for logging
            action_func: Function to execute (no arguments)
            verifier_func: Function that returns list of element labels
            expected: Dict passed to Judge.evaluate()
            alternative_funcs: List of alternative functions to try on failure
        
        Returns:
            LoopResult with success status and attempt history
        """
        verdicts = []
        after_labels = []
        
        # Capture BEFORE state
        before_labels = verifier_func()
        
        for attempt in range(self.max_attempts):
            print(f"   🔄 Attempt {attempt + 1}/{self.max_attempts}")
            
            # Choose which function to execute
            if attempt == 0:
                func = action_func
            elif alternative_funcs and attempt <= len(alternative_funcs):
                func = alternative_funcs[attempt - 1]
                print(f"      Trying alternative approach...")
            else:
                print(f"      No more alternatives.")
                break
            
            # Execute
            try:
                func()
                time.sleep(0.5)
            except Exception as e:
                verdicts.append(FailedVerdict(e))
                continue
            
            # Verify
            after_labels = verifier_func()
            
            if self.judge:
                verdict = self.judge.evaluate(before_labels, after_labels, expected)
            else:
                verdict = SimpleVerdict(
                    len(set(after_labels) - set(before_labels)) > 0,
                    expected,
                    after_labels
                )
            
            verdicts.append(verdict)
            
            if verdict.is_pass():
                print(f"      ✅ Passed!")
                return LoopResult(True, attempt + 1, verdicts)
            else:
                print(f"      ❌ Failed: {verdict.feedback}")
                # Update before_labels for next attempt
                before_labels = after_labels
        
        return LoopResult(False, attempt + 1, verdicts)


# ─── Independent Test ──────────────────────────────
if __name__ == "__main__":
    print("🔄 Loop Agent - Independent Test\n")
    
    # Test 1: First attempt succeeds
    print("Test 1: First attempt succeeds")
    attempts = [0]
    def succeed_first():
        attempts[0] += 1
        print(f"      Executing action (attempt {attempts[0]})...")
    
    def get_labels():
        if attempts[0] == 0:
            return ["Folder", "Calendar", "Clock"]
        else:
            return ["Chats", "Updates", "Calls", "New chat"]
    
    loop = LoopAgent(max_attempts=3)
    result = loop.execute_with_retry(
        "test_success",
        succeed_first,
        get_labels,
        expected={"appeared": ["Chats"]}
    )
    print(f"   Result: {result}")
    print()
    
    # Test 2: Succeeds on third attempt
    print("Test 2: Succeeds on third attempt")
    attempts2 = [0]
    
    def fail_twice():
        attempts2[0] += 1
    
    def get_labels2():
        if attempts2[0] < 3:
            return ["Folder", "Calendar"]
        else:
            return ["Chats", "Updates", "Messages"]
    
    def alt1(): print("      Alt 1: Trying different method...")
    def alt2(): print("      Alt 2: Trying yet another method...")
    
    loop2 = LoopAgent(max_attempts=3)
    result2 = loop2.execute_with_retry(
        "test_retry",
        fail_twice,
        get_labels2,
        expected={"appeared": ["Chats"]},
        alternative_funcs=[alt1, alt2]
    )
    print(f"   Result: {result2}")
    print()
    
    # Test 3: All attempts fail
    print("Test 3: All attempts fail")
    attempts3 = [0]
    
    def always_fail():
        attempts3[0] += 1
    
    def get_labels3():
        return ["Folder", "Calendar"]
    
    loop3 = LoopAgent(max_attempts=3)
    result3 = loop3.execute_with_retry(
        "test_fail",
        always_fail,
        get_labels3,
        expected={"appeared": ["WhatsApp"]}
    )
    print(f"   Result: {result3}")
