"""
Input Validation & Sanitization
Patterns: SQL Injection, XSS, Command Injection, Path Traversal, etc.
"""

import re
import html
from typing import Any, Optional, Dict, List
from urllib.parse import urlparse, parse_qs
from .redos_protection import validate_with_timeout


class InputValidator:
    """
    Comprehensive input validation for common attack patterns.
    Validates against: SQL injection, XSS, command injection, path traversal, etc.
    """
    
    # Attack pattern signatures
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION)\b)",
        r"(--|#|/\*|\*/)",
        r"('|\"|;|\\)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$(){}[\]<>]",
        r"\$\(",
        r"`.*`",
        r"\|\|",
        r"&&",
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.",
        r"%2e%2e",
        r"\.\.\\",
    ]
    
    @staticmethod
    def sanitize_sql(value: str) -> str:
        """
        Sanitize input for SQL queries (basic - USE PARAMETERIZED QUERIES instead!).
        
        Args:
            value: Input string to sanitize
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return str(value)
        
        # Escape single quotes
        sanitized = value.replace("'", "''")
        # Remove SQL comments
        sanitized = re.sub(r"--.*$", "", sanitized, flags=re.MULTILINE)
        sanitized = re.sub(r"/\*.*?\*/", "", sanitized, flags=re.DOTALL)
        
        return sanitized
    
    @staticmethod
    def sanitize_html(value: str) -> str:
        """
        Sanitize HTML to prevent XSS attacks.
        
        Args:
            value: Input string to sanitize
            
        Returns:
            HTML-escaped string
        """
        if not isinstance(value, str):
            return str(value)
        
        return html.escape(value, quote=True)
    
    @staticmethod
    def sanitize_shell(value: str) -> str:
        """
        Sanitize input for shell commands (AVOID SHELL COMMANDS if possible!).
        
        Args:
            value: Input string to sanitize
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return str(value)
        
        # Remove dangerous characters
        dangerous_chars = ";|&$`<>(){}[]!*?"
        for char in dangerous_chars:
            value = value.replace(char, "")
        
        return value
    
    @staticmethod
    def sanitize_path(value: str) -> str:
        """
        Sanitize file paths to prevent path traversal attacks.
        
        Args:
            value: Path string to sanitize
            
        Returns:
            Sanitized path
        """
        if not isinstance(value, str):
            return str(value)
        
        # Remove path traversal attempts
        sanitized = value.replace("../", "").replace("..\\", "")
        sanitized = sanitized.replace("..", "")
        
        # Remove null bytes
        sanitized = sanitized.replace("\x00", "")
        
        return sanitized
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email address format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid email format
        """
        if not email or not isinstance(email, str):
            return False
        
        # Simple email regex (RFC 5322 simplified)
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return validate_with_timeout(pattern, email, timeout=0.5)
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate URL format and safety.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid and safe URL
        """
        if not url or not isinstance(url, str):
            return False
        
        try:
            parsed = urlparse(url)
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            # Only allow http/https
            if parsed.scheme not in ["http", "https"]:
                return False
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_integer(value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None) -> bool:
        """
        Validate integer value with optional range check.
        
        Args:
            value: Value to validate
            min_val: Minimum allowed value (optional)
            max_val: Maximum allowed value (optional)
            
        Returns:
            True if valid integer in range
        """
        try:
            int_value = int(value)
            if min_val is not None and int_value < min_val:
                return False
            if max_val is not None and int_value > max_val:
                return False
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def contains_sql_injection(value: str) -> bool:
        """
        Check if input contains SQL injection patterns.
        
        Args:
            value: Input to check
            
        Returns:
            True if SQL injection detected
        """
        if not isinstance(value, str):
            return False
        
        value_upper = value.upper()
        for pattern in InputValidator.SQL_INJECTION_PATTERNS:
            if validate_with_timeout(pattern, value_upper, timeout=0.5):
                return True
        return False
    
    @staticmethod
    def contains_xss(value: str) -> bool:
        """
        Check if input contains XSS patterns.
        
        Args:
            value: Input to check
            
        Returns:
            True if XSS detected
        """
        if not isinstance(value, str):
            return False
        
        value_lower = value.lower()
        for pattern in InputValidator.XSS_PATTERNS:
            if validate_with_timeout(pattern, value_lower, timeout=0.5):
                return True
        return False
    
    @staticmethod
    def contains_command_injection(value: str) -> bool:
        """
        Check if input contains command injection patterns.
        
        Args:
            value: Input to check
            
        Returns:
            True if command injection detected
        """
        if not isinstance(value, str):
            return False
        
        for pattern in InputValidator.COMMAND_INJECTION_PATTERNS:
            if validate_with_timeout(pattern, value, timeout=0.5):
                return True
        return False


class SecureValidator:
    """
    High-level validator with ReDoS protection for common validation scenarios.
    """
    
    @staticmethod
    def validate_aws_resource_name(name: str) -> bool:
        """
        Validate AWS resource name format.
        
        Args:
            name: Resource name to validate
            
        Returns:
            True if valid AWS resource name
        """
        if not name or not isinstance(name, str):
            return False
        
        # AWS resource names: alphanumeric, hyphens, underscores, 1-255 chars
        pattern = r"^[a-zA-Z0-9_-]{1,255}$"
        return validate_with_timeout(pattern, name, timeout=0.5)
    
    @staticmethod
    def validate_lambda_arn(arn: str) -> bool:
        """
        Validate AWS Lambda ARN format.
        
        Args:
            arn: ARN to validate
            
        Returns:
            True if valid Lambda ARN
        """
        if not arn or not isinstance(arn, str):
            return False
        
        # Lambda ARN format: arn:aws:lambda:region:account:function:name
        pattern = r"^arn:aws:lambda:[a-z0-9-]+:\d{12}:function:[a-zA-Z0-9_-]+$"
        return validate_with_timeout(pattern, arn, timeout=0.5)
    
    @staticmethod
    def validate_webhook_url(url: str) -> bool:
        """
        Validate webhook URL (Discord, Slack, etc).
        
        Args:
            url: Webhook URL to validate
            
        Returns:
            True if valid webhook URL
        """
        if not url or not isinstance(url, str):
            return False
        
        # Must be valid HTTPS URL
        if not InputValidator.validate_url(url):
            return False
        
        # Must be HTTPS
        if not url.startswith("https://"):
            return False
        
        # Check for known webhook domains
        allowed_domains = [
            "discord.com",
            "discordapp.com",
            "slack.com",
            "hooks.slack.com",
        ]
        
        parsed = urlparse(url)
        for domain in allowed_domains:
            if domain in parsed.netloc:
                return True
        
        # Allow other HTTPS URLs but warn
        return True
    
    @staticmethod
    def validate_json_safe(data: Any, max_depth: int = 10) -> bool:
        """
        Check if data is safe JSON (no deeply nested structures).
        
        Args:
            data: Data to validate
            max_depth: Maximum nesting depth allowed
            
        Returns:
            True if safe JSON structure
        """
        def check_depth(obj, current_depth):
            if current_depth > max_depth:
                return False
            
            if isinstance(obj, dict):
                for value in obj.values():
                    if not check_depth(value, current_depth + 1):
                        return False
            elif isinstance(obj, list):
                for item in obj:
                    if not check_depth(item, current_depth + 1):
                        return False
            
            return True
        
        return check_depth(data, 0)
