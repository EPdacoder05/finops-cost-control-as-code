"""
AI-Era Security Patterns (2026)
Pattern 28: Prompt Injection Detection
Pattern 29: AI Package Hallucination Protection  
Pattern 30: AI Agent Identity & Access Control
"""

import re
import hashlib
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from .redos_protection import validate_with_timeout


@dataclass
class PromptInjectionResult:
    """Result from prompt injection detection"""
    is_suspicious: bool
    risk_score: float
    detected_patterns: List[str]
    reason: str


class PromptInjectionDetector:
    """
    Detects prompt injection attacks in AI/LLM systems.
    Patterns: Direct injection, indirect injection, jailbreak attempts, system override.
    """
    
    # Prompt injection patterns
    INJECTION_PATTERNS = {
        "system_override": [
            r"ignore (previous|all|above) instructions",
            r"disregard (previous|all|system) (instructions|rules|prompts)",
            r"you are now",
            r"new (instructions|rules|system prompt)",
            r"forget (everything|all|previous)",
        ],
        "jailbreak": [
            r"(act|pretend|roleplay) as",
            r"developer mode",
            r"sudo mode",
            r"admin mode",
            r"unrestricted mode",
            r"DAN\s+(mode|\d+)",  # "Do Anything Now"
        ],
        "prompt_leakage": [
            r"show (me )?(your|the) (system )?prompt",
            r"what are your instructions",
            r"print your prompt",
            r"reveal your (instructions|system prompt|rules)",
        ],
        "indirect_injection": [
            r"<\|.*?\|>",  # Special tokens
            r"\[SYSTEM\]",
            r"\[INST\]",
            r"<\s*script",  # HTML injection
        ],
    }
    
    def __init__(self, risk_threshold: float = 0.3):
        """
        Initialize prompt injection detector.
        
        Args:
            risk_threshold: Risk score threshold (0-1) for flagging suspicious input
        """
        self.risk_threshold = risk_threshold
    
    def detect(self, user_input: str) -> PromptInjectionResult:
        """
        Detect prompt injection attempts in user input.
        
        Args:
            user_input: User-provided input to check
            
        Returns:
            PromptInjectionResult with detection details
        """
        if not user_input or not isinstance(user_input, str):
            return PromptInjectionResult(
                is_suspicious=False,
                risk_score=0.0,
                detected_patterns=[],
                reason="Empty or invalid input"
            )
        
        detected = []
        risk_score = 0.0
        input_lower = user_input.lower()
        
        # Check each category of injection patterns
        for category, patterns in self.INJECTION_PATTERNS.items():
            for pattern in patterns:
                if validate_with_timeout(pattern, input_lower, timeout=0.5):
                    detected.append(f"{category}: {pattern}")
                    risk_score += 0.3
        
        # Additional heuristics
        if len(user_input) > 5000:
            risk_score += 0.1
            detected.append("excessive_length")
        
        if user_input.count("[") > 10 or user_input.count("{") > 10:
            risk_score += 0.1
            detected.append("excessive_brackets")
        
        # Normalize risk score
        risk_score = min(risk_score, 1.0)
        is_suspicious = risk_score >= self.risk_threshold
        
        reason = "Clean input"
        if is_suspicious:
            reason = f"Potential prompt injection: {', '.join(detected[:3])}"
        
        return PromptInjectionResult(
            is_suspicious=is_suspicious,
            risk_score=risk_score,
            detected_patterns=detected,
            reason=reason
        )
    
    @staticmethod
    def sanitize_user_input(user_input: str) -> str:
        """
        Sanitize user input to remove potential injection vectors.
        
        Args:
            user_input: User input to sanitize
            
        Returns:
            Sanitized input
        """
        if not user_input:
            return ""
        
        # Remove special tokens
        sanitized = re.sub(r"<\|.*?\|>", "", user_input)
        sanitized = re.sub(r"\[SYSTEM\]", "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"\[INST\]", "", sanitized, flags=re.IGNORECASE)
        
        # Limit length
        if len(sanitized) > 5000:
            sanitized = sanitized[:5000]
        
        return sanitized.strip()


class AIPackageValidator:
    """
    Validates AI-suggested packages to prevent package hallucination attacks.
    Detects: Fake packages, typosquatting, suspicious names.
    """
    
    SUSPICIOUS_PATTERNS = [
        r"test-.*-test",  # Suspicious test packages
        r".*-internal",   # Internal-sounding packages
        r".*-temp",       # Temporary packages
        r".*-dev-.*",     # Development packages
        r"\d{4,}",        # Packages with many numbers
    ]
    
    # Common typosquatting techniques
    COMMON_PACKAGES = {
        "requests", "numpy", "pandas", "django", "flask", 
        "tensorflow", "pytorch", "boto3", "pulumi", "pytest"
    }
    
    def __init__(self, whitelist: Optional[Set[str]] = None):
        """
        Initialize package validator.
        
        Args:
            whitelist: Set of approved package names (optional)
        """
        self.whitelist = whitelist or set()
    
    def validate_package_name(self, package_name: str) -> bool:
        """
        Validate if a package name looks legitimate.
        
        Args:
            package_name: Package name to validate
            
        Returns:
            True if package name looks safe
        """
        if not package_name or not isinstance(package_name, str):
            return False
        
        # Check whitelist first
        if self.whitelist and package_name in self.whitelist:
            return True
        
        # Check for suspicious patterns
        for pattern in self.SUSPICIOUS_PATTERNS:
            if validate_with_timeout(pattern, package_name, timeout=0.5):
                return False
        
        # Package name should be reasonable length
        if len(package_name) < 2 or len(package_name) > 100:
            return False
        
        # Should only contain alphanumeric, hyphens, underscores, dots
        if not validate_with_timeout(r"^[a-zA-Z0-9._-]+$", package_name, timeout=0.5):
            return False
        
        return True
    
    def check_typosquatting(self, package_name: str) -> Optional[str]:
        """
        Check if package name is typosquatting a popular package.
        
        Args:
            package_name: Package name to check
            
        Returns:
            Likely target package name if typosquatting detected, None otherwise
        """
        if not package_name:
            return None
        
        package_lower = package_name.lower()
        
        # Check for similar names in common packages
        for common_pkg in self.COMMON_PACKAGES:
            # Exact match (case-insensitive) - not typosquatting
            if package_lower == common_pkg.lower():
                continue
            
            # Check for common typo patterns
            # 1. One character different
            if self._levenshtein_distance(package_lower, common_pkg) == 1:
                return common_pkg
            
            # 2. Added/removed hyphen or underscore
            normalized_input = package_lower.replace("-", "").replace("_", "")
            normalized_common = common_pkg.replace("-", "").replace("_", "")
            if normalized_input == normalized_common:
                return common_pkg
        
        return None
    
    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return AIPackageValidator._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]


class AgentPermission(Enum):
    """Agent permission levels"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


class AgentAction(Enum):
    """High-regret actions requiring human approval"""
    DELETE_DATA = "delete_data"
    MODIFY_PRODUCTION = "modify_production"
    SPEND_MONEY = "spend_money"
    EXTERNAL_API_CALL = "external_api_call"


@dataclass
class AgentIdentity:
    """Agent identity information"""
    agent_id: str
    agent_type: str  # e.g., "code-generator", "data-analyzer"
    permissions: List[AgentPermission]
    created_at: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()


class AgentAccessControl:
    """
    Access control for AI agents.
    Implements agent-specific OIDC and human-in-the-loop for high-regret actions.
    """
    
    HIGH_REGRET_ACTIONS = {
        AgentAction.DELETE_DATA,
        AgentAction.MODIFY_PRODUCTION,
        AgentAction.SPEND_MONEY,
    }
    
    def __init__(self):
        """Initialize agent access control."""
        self.registered_agents: Dict[str, AgentIdentity] = {}
        self.action_log: List[Dict] = []
        self.pending_approvals: Dict[str, Dict] = {}
    
    def register_agent(self, identity: AgentIdentity) -> bool:
        """
        Register a new agent.
        
        Args:
            identity: Agent identity information
            
        Returns:
            True if registration successful
        """
        if identity.agent_id in self.registered_agents:
            return False
        
        self.registered_agents[identity.agent_id] = identity
        return True
    
    def check_permission(self, agent_id: str, permission: AgentPermission) -> bool:
        """
        Check if agent has specific permission.
        
        Args:
            agent_id: Agent identifier
            permission: Permission to check
            
        Returns:
            True if agent has permission
        """
        if agent_id not in self.registered_agents:
            return False
        
        agent = self.registered_agents[agent_id]
        return permission in agent.permissions or AgentPermission.ADMIN in agent.permissions
    
    def request_action(self, agent_id: str, action: AgentAction, resource: str) -> Dict:
        """
        Request permission to perform an action.
        High-regret actions require human approval.
        
        Args:
            agent_id: Agent identifier
            action: Action to perform
            resource: Resource being acted upon
            
        Returns:
            Dict with 'approved' status and 'approval_id' if pending
        """
        if agent_id not in self.registered_agents:
            return {"approved": False, "reason": "Agent not registered"}
        
        # High-regret actions require human approval
        if action in self.HIGH_REGRET_ACTIONS:
            approval_id = self._generate_approval_id(agent_id, action, resource)
            self.pending_approvals[approval_id] = {
                "agent_id": agent_id,
                "action": action,
                "resource": resource,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "approved": False,
            }
            return {
                "approved": False,
                "requires_human_approval": True,
                "approval_id": approval_id,
                "reason": f"High-regret action {action.value} requires human approval"
            }
        
        # Low-risk actions can proceed
        self._log_action(agent_id, action, resource, "auto-approved")
        return {"approved": True, "reason": "Auto-approved low-risk action"}
    
    def approve_action(self, approval_id: str, human_approver: str) -> bool:
        """
        Human approves a pending action.
        
        Args:
            approval_id: Approval request ID
            human_approver: Identifier of human approver
            
        Returns:
            True if approval successful
        """
        if approval_id not in self.pending_approvals:
            return False
        
        request = self.pending_approvals[approval_id]
        request["approved"] = True
        request["approved_by"] = human_approver
        request["approved_at"] = datetime.now(timezone.utc).isoformat()
        
        self._log_action(
            request["agent_id"],
            request["action"],
            request["resource"],
            f"approved by {human_approver}"
        )
        
        return True
    
    def _generate_approval_id(self, agent_id: str, action: AgentAction, resource: str) -> str:
        """Generate unique approval ID."""
        data = f"{agent_id}:{action.value}:{resource}:{datetime.now(timezone.utc).isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _log_action(self, agent_id: str, action: AgentAction, resource: str, result: str):
        """Log agent action."""
        self.action_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "action": action.value if isinstance(action, AgentAction) else action,
            "resource": resource,
            "result": result,
        })
