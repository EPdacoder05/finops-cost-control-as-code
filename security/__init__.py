"""
Security Framework for FinOps Cost Control
Production-grade security patterns for AWS Lambda and IAC
"""

__version__ = "1.0.0"

from .input_validator import InputValidator, SecureValidator
from .redos_protection import SafeRegexMatcher, validate_with_timeout
from .ai_security import (
    PromptInjectionDetector,
    AIPackageValidator,
    AgentAccessControl,
)
from .crypto_utils import SecureHasher, SecureTokenGenerator, SecureEncryption
from .webhook_validator import WebhookValidator

__all__ = [
    "InputValidator",
    "SecureValidator",
    "SafeRegexMatcher",
    "validate_with_timeout",
    "PromptInjectionDetector",
    "AIPackageValidator",
    "AgentAccessControl",
    "SecureHasher",
    "SecureTokenGenerator",
    "SecureEncryption",
    "WebhookValidator",
]
