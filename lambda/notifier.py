import os
import json
import urllib.request
import sys

# Add parent directory to path for security imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from security.webhook_validator import WebhookValidator
from security.input_validator import SecureValidator

def handler(event, context):
    discord_webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    
    if not discord_webhook_url and not slack_webhook_url:
        print("Neither DISCORD_WEBHOOK_URL nor SLACK_WEBHOOK_URL are configured")
        return
    
    # Validate webhook URLs on first use
    if discord_webhook_url:
        is_valid, error = WebhookValidator.validate_webhook_url(discord_webhook_url)
        if not is_valid:
            print(f"Invalid Discord webhook URL: {error}")
            discord_webhook_url = None
    
    if slack_webhook_url:
        is_valid, error = WebhookValidator.validate_webhook_url(slack_webhook_url)
        if not is_valid:
            print(f"Invalid Slack webhook URL: {error}")
            slack_webhook_url = None
    
    for record in event.get("Records", []):
        message = record["Sns"]["Message"]
        
        # Validate message is not malicious (basic check)
        if len(message) > 50000:  # Prevent extremely large messages
            print("Message too large, truncating...")
            message = message[:50000] + "... [truncated]"
        
        # Discord Notification
        if discord_webhook_url:
            discord_payload = {"content": message}
            discord_data = json.dumps(discord_payload).encode("utf-8")
            discord_req = urllib.request.Request(discord_webhook_url, data=discord_data, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(discord_req, timeout=10) as r:
                    r.read()
            except Exception as e:
                print("Failed to post to Discord webhook:", e)
        
        # Slack Notification
        if slack_webhook_url:
            slack_payload = {"text": message}
            slack_data = json.dumps(slack_payload).encode("utf-8")
            slack_req = urllib.request.Request(slack_webhook_url, data=slack_data, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(slack_req, timeout=10) as r:
                    r.read()
            except Exception as e:
                print("Failed to post to Slack webhook:", e)
