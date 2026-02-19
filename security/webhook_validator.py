"""
Webhook Validator
Validates webhook URLs for Discord, Slack, and other services
"""

from urllib.parse import urlparse
from typing import Optional
from .input_validator import InputValidator


class WebhookValidator:
    """
    Validates webhook URLs to prevent SSRF and other attacks.
    """
    
    # Allowed webhook domains
    ALLOWED_DOMAINS = {
        "discord.com",
        "discordapp.com",
        "discord.gg",
        "ptb.discord.com",
        "ptb.discordapp.com",
        "canary.discord.com",
        "canary.discordapp.com",
        "hooks.slack.com",
        "slack.com",
        "api.slack.com",
    }
    
    # Blocked IP ranges (private/internal networks)
    BLOCKED_HOSTS = {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "169.254.169.254",  # AWS metadata endpoint
        "metadata.google.internal",  # GCP metadata
    }
    
    @staticmethod
    def validate_webhook_url(url: str, allow_custom_domains: bool = False) -> tuple[bool, Optional[str]]:
        """
        Validate webhook URL for security issues.
        
        Args:
            url: Webhook URL to validate
            allow_custom_domains: Allow domains not in whitelist (default: False)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url or not isinstance(url, str):
            return False, "URL is empty or invalid type"
        
        # Must be valid URL
        if not InputValidator.validate_url(url):
            return False, "Invalid URL format"
        
        # Must be HTTPS
        if not url.startswith("https://"):
            return False, "Webhook URL must use HTTPS"
        
        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            return False, f"Failed to parse URL: {str(e)}"
        
        # Check for blocked hosts
        hostname = parsed.hostname or parsed.netloc
        if hostname in WebhookValidator.BLOCKED_HOSTS:
            return False, f"Blocked host: {hostname}"
        
        # Check for private IP addresses
        if WebhookValidator._is_private_ip(hostname):
            return False, "Private IP addresses not allowed (SSRF protection)"
        
        # Check domain whitelist
        domain_allowed = any(
            allowed_domain in hostname
            for allowed_domain in WebhookValidator.ALLOWED_DOMAINS
        )
        
        if not domain_allowed and not allow_custom_domains:
            return False, f"Domain not in whitelist: {hostname}"
        
        # Check URL length (prevent extremely long URLs)
        if len(url) > 2048:
            return False, "URL too long (max 2048 characters)"
        
        return True, None
    
    @staticmethod
    def validate_discord_webhook(url: str) -> bool:
        """
        Validate Discord webhook URL format.
        
        Args:
            url: Discord webhook URL
            
        Returns:
            True if valid Discord webhook
        """
        if not url:
            return False
        
        # Discord webhook format
        is_valid, _ = WebhookValidator.validate_webhook_url(url)
        if not is_valid:
            return False
        
        # Must contain /api/webhooks/
        if "/api/webhooks/" not in url:
            return False
        
        return True
    
    @staticmethod
    def validate_slack_webhook(url: str) -> bool:
        """
        Validate Slack webhook URL format.
        
        Args:
            url: Slack webhook URL
            
        Returns:
            True if valid Slack webhook
        """
        if not url:
            return False
        
        is_valid, _ = WebhookValidator.validate_webhook_url(url)
        if not is_valid:
            return False
        
        # Must be hooks.slack.com
        if "hooks.slack.com" not in url:
            return False
        
        # Must contain /services/
        if "/services/" not in url:
            return False
        
        return True
    
    @staticmethod
    def _is_private_ip(hostname: str) -> bool:
        """
        Check if hostname is a private IP address.
        
        Args:
            hostname: Hostname to check
            
        Returns:
            True if private IP
        """
        if not hostname:
            return False
        
        # Try using ipaddress module if available
        try:
            import ipaddress
            ip = ipaddress.ip_address(hostname)
            return ip.is_private
        except (ImportError, ValueError):
            pass
        
        # Fallback: Check for IPv4 private ranges manually
        private_ranges = [
            "10.",          # 10.0.0.0/8
            "192.168.",     # 192.168.0.0/16
        ]
        
        # Check 172.16.0.0/12 range (172.16.0.0 - 172.31.255.255)
        if hostname.startswith("172."):
            parts = hostname.split(".")
            if len(parts) >= 2:
                try:
                    second_octet = int(parts[1])
                    if 16 <= second_octet <= 31:
                        return True
                except ValueError:
                    pass
        
        for prefix in private_ranges:
            if hostname.startswith(prefix):
                return True
        
        return False
    
    @staticmethod
    def sanitize_webhook_url(url: str) -> str:
        """
        Sanitize webhook URL (remove query parameters, fragments).
        
        Args:
            url: Webhook URL to sanitize
            
        Returns:
            Sanitized URL
        """
        if not url:
            return ""
        
        try:
            parsed = urlparse(url)
            # Keep only scheme, netloc, and path
            sanitized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            return sanitized
        except Exception:
            return url
