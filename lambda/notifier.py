import os
import json
import urllib.request

def handler(event, context):
    discord_webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    
    if not discord_webhook_url and not slack_webhook_url:
        print("Neither DISCORD_WEBHOOK_URL nor SLACK_WEBHOOK_URL are configured")
        return
    
    for record in event.get("Records", []):
        message = record["Sns"]["Message"]
        
        # Discord Notification
        if discord_webhook_url:
            discord_payload = {"content": message}
            discord_data = json.dumps(discord_payload).encode("utf-8")
            discord_req = urllib.request.Request(discord_webhook_url, data=discord_data, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(discord_req) as r:
                    r.read()
            except Exception as e:
                print("Failed to post to Discord webhook:", e)
        
        # Slack Notification
        if slack_webhook_url:
            slack_payload = {"text": message}
            slack_data = json.dumps(slack_payload).encode("utf-8")
            slack_req = urllib.request.Request(slack_webhook_url, data=slack_data, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(slack_req) as r:
                    r.read()
            except Exception as e:
                print("Failed to post to Slack webhook:", e)
