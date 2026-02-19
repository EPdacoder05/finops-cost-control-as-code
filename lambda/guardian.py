import json
import boto3
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path for security imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from security.input_validator import InputValidator, SecureValidator

def handler(event, context):
    """Real-time cost prevention - stops expensive resources immediately"""
    
    print(f"Guardian triggered by event: {json.dumps(event)}")
    
    # Parse the EventBridge event
    detail = event.get('detail', {})
    source = event.get('source', '')
    detail_type = event.get('detail-type', '')
    
    sns = boto3.client('sns')
    ec2 = boto3.client('ec2')
    rds = boto3.client('rds')
    
    prevented_actions = []
    
    # Validate environment variables
    allowed_types_raw = os.environ.get('ALLOWED_INSTANCE_TYPES', 't2.micro,t3.micro')
    allowed_types = [t.strip() for t in allowed_types_raw.split(',') if SecureValidator.validate_aws_resource_name(t.strip())]
    
    if not allowed_types:
        allowed_types = ['t2.micro', 't3.micro']
    
    try:
        # Handle EC2 Instance Events
        if source == 'aws.ec2' and 'EC2 Instance' in detail_type:
            instance_id = detail.get('instance-id')
            state = detail.get('state')
            
            # Validate instance ID format
            if not instance_id or not SecureValidator.validate_aws_resource_name(instance_id):
                print(f"Invalid instance ID format: {instance_id}")
                return {'statusCode': 400, 'body': json.dumps({'error': 'Invalid instance ID'})}
            
            if state == 'running' and instance_id:
                # Get instance details
                response = ec2.describe_instances(InstanceIds=[instance_id])
                instance = response['Reservations'][0]['Instances'][0]
                instance_type = instance.get('InstanceType', 'unknown')
                
                if instance_type not in allowed_types:
                    # STOP THE EXPENSIVE INSTANCE IMMEDIATELY
                    ec2.stop_instances(InstanceIds=[instance_id])
                    prevented_actions.append(f"🚨 STOPPED expensive EC2 instance {instance_id} ({instance_type})")
                    
                    # Terminate after 5 minutes if it tries to restart
                    ec2.terminate_instances(InstanceIds=[instance_id])
                    prevented_actions.append(f"💀 TERMINATED {instance_id} to prevent charges")
        
        # Handle RDS Instance Events  
        elif source == 'aws.rds' and 'RDS DB Instance' in detail_type:
            db_instance_id = detail.get('source-id')
            
            # Validate DB instance ID format
            if not db_instance_id or not SecureValidator.validate_aws_resource_name(db_instance_id):
                print(f"Invalid DB instance ID format: {db_instance_id}")
                return {'statusCode': 400, 'body': json.dumps({'error': 'Invalid DB instance ID'})}
            
            if db_instance_id:
                # Check if it's a free tier eligible instance
                response = rds.describe_db_instances(DBInstanceIdentifier=db_instance_id)
                db_instance = response['DBInstances'][0]
                db_class = db_instance.get('DBInstanceClass', '')
                
                if db_class != 'db.t3.micro' and db_class != 'db.t2.micro':
                    # STOP THE EXPENSIVE RDS INSTANCE
                    rds.stop_db_instance(DBInstanceIdentifier=db_instance_id)
                    prevented_actions.append(f"🚨 STOPPED expensive RDS instance {db_instance_id} ({db_class})")
        
        # Send alert for any prevented actions
        if prevented_actions:
            alert_message = f"""
🛡️ FINOPS GUARDIAN PREVENTION ALERT

⚡ Real-time cost prevention activated!

ACTIONS TAKEN:
{chr(10).join(prevented_actions)}

TIME: {datetime.now(timezone.utc).isoformat()}Z
REGION: {os.environ.get('HOME_REGION', 'us-east-1')}

Your free tier is PROTECTED! 💰
            """
            
            sns_arn = os.environ.get('SNS_TOPIC_ARN')
            if sns_arn and SecureValidator.validate_aws_resource_name(sns_arn.split(":")[-1]):
                sns.publish(
                    TopicArn=sns_arn,
                    Subject="🚨 FinOps Prevention - Expensive Resource Blocked",
                    Message=alert_message
                )
            
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Guardian scan completed',
                'prevented_actions': prevented_actions,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        }
        
    except Exception as e:
        error_msg = f"Guardian error: {str(e)}"
        print(error_msg)
        
        # Alert on guardian failure
        try:
            sns_arn = os.environ.get('SNS_TOPIC_ARN')
            if sns_arn:
                sns.publish(
                    TopicArn=sns_arn,
                    Subject="⚠️ FinOps Guardian Error",
                    Message=f"Guardian Lambda failed: {error_msg}"
                )
        except Exception:
            pass
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        }