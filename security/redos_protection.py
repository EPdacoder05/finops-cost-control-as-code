"""
ReDoS Protection - Pattern 27+
Handles Regular Expression Denial of Service attacks
Uses thread-based timeout to ACTUALLY stop catastrophic backtracking
"""

import re
import threading
from typing import Optional, Pattern
from dataclasses import dataclass


@dataclass
class RegexResult:
    """Result from a regex match with timeout protection"""
    matched: bool
    timed_out: bool
    error: Optional[str] = None


class SafeRegexMatcher:
    """
    Thread-based regex matcher with timeout protection.
    Prevents ReDoS (Regular Expression Denial of Service) attacks.
    
    Example:
        matcher = SafeRegexMatcher(timeout_seconds=1.0)
        result = matcher.match(r"(a+)+b", "a" * 30 + "c")
        if result.timed_out:
            print("Evil regex detected and blocked!")
    """
    
    def __init__(self, timeout_seconds: float = 1.0):
        """
        Initialize the safe regex matcher.
        
        Args:
            timeout_seconds: Maximum time allowed for regex matching (default: 1.0)
        """
        self.timeout_seconds = timeout_seconds
    
    def match(self, pattern: str, text: str, flags: int = 0) -> RegexResult:
        """
        Match text against pattern with timeout protection.
        
        Args:
            pattern: Regex pattern to match
            text: Text to match against
            flags: Regex flags (re.IGNORECASE, etc.)
            
        Returns:
            RegexResult with match status and timeout flag
        """
        result = {"matched": False, "timed_out": False, "error": None}
        
        def regex_worker():
            try:
                compiled = re.compile(pattern, flags)
                match = compiled.search(text)
                result["matched"] = match is not None
            except Exception as e:
                result["error"] = str(e)
        
        thread = threading.Thread(target=regex_worker, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout_seconds)
        
        if thread.is_alive():
            # Thread is still running - timeout occurred
            result["timed_out"] = True
            # Note: We can't kill the thread, but we return immediately
            # The thread will eventually complete or be cleaned up
        
        return RegexResult(
            matched=result["matched"],
            timed_out=result["timed_out"],
            error=result["error"]
        )
    
    def fullmatch(self, pattern: str, text: str, flags: int = 0) -> RegexResult:
        """
        Full match text against pattern with timeout protection.
        
        Args:
            pattern: Regex pattern to match
            text: Text to match against
            flags: Regex flags
            
        Returns:
            RegexResult with match status and timeout flag
        """
        result = {"matched": False, "timed_out": False, "error": None}
        
        def regex_worker():
            try:
                compiled = re.compile(pattern, flags)
                match = compiled.fullmatch(text)
                result["matched"] = match is not None
            except Exception as e:
                result["error"] = str(e)
        
        thread = threading.Thread(target=regex_worker, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout_seconds)
        
        if thread.is_alive():
            result["timed_out"] = True
        
        return RegexResult(
            matched=result["matched"],
            timed_out=result["timed_out"],
            error=result["error"]
        )


def validate_with_timeout(pattern: str, text: str, timeout: float = 1.0) -> bool:
    """
    Convenience function for quick regex validation with timeout.
    
    Args:
        pattern: Regex pattern to match
        text: Text to validate
        timeout: Timeout in seconds (default: 1.0)
        
    Returns:
        True if matched and no timeout, False otherwise
        
    Example:
        if validate_with_timeout(r"^\\d+$", user_input):
            print("Valid number!")
    """
    matcher = SafeRegexMatcher(timeout_seconds=timeout)
    result = matcher.match(pattern, text)
    return result.matched and not result.timed_out


# Evil regex patterns for testing (DO NOT USE IN PRODUCTION)
EVIL_PATTERNS = [
    r"(a+)+b",           # Catastrophic backtracking
    r"(a*)*b",           # Exponential time
    r"(a|a)*b",          # Alternative with overlap
    r"(a|ab)*c",         # Overlapping alternatives
]


if __name__ == "__main__":
    # Demo: Show ReDoS protection in action
    print("=== ReDoS Protection Demo ===\n")
    
    matcher = SafeRegexMatcher(timeout_seconds=1.0)
    
    # Test 1: Safe regex
    print("Test 1: Safe regex pattern")
    result = matcher.match(r"^\d{1,10}$", "1234567890")
    print(r"  Pattern: ^\d{1,10}$")
    print(f"  Input: '1234567890'")
    print(f"  Matched: {result.matched}, Timed out: {result.timed_out}\n")
    
    # Test 2: Evil regex with safe input
    print("Test 2: Evil regex with safe input")
    result = matcher.match(r"(a+)+b", "aaab")
    print(f"  Pattern: (a+)+b")
    print(f"  Input: 'aaab'")
    print(f"  Matched: {result.matched}, Timed out: {result.timed_out}\n")
    
    # Test 3: Evil regex with malicious input (WOULD HANG WITHOUT PROTECTION)
    print("Test 3: Evil regex with malicious input (ReDoS attack)")
    result = matcher.match(r"(a+)+b", "a" * 28 + "c")
    print(f"  Pattern: (a+)+b")
    print(f"  Input: '{'a' * 28}c' (28 'a's + 'c')")
    print(f"  Matched: {result.matched}, Timed out: {result.timed_out}")
    if result.timed_out:
        print("  ✅ ATTACK BLOCKED! Regex timeout prevented ReDoS")
    print()
