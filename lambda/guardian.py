import json
import boto3
import os
from datetime import datetime

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
    
    try:
        # Handle EC2 Instance Events
        if source == 'aws.ec2' and 'EC2 Instance' in detail_type:
            instance_id = detail.get('instance-id')
            state = detail.get('state')
            
            if state == 'running' and instance_id:
                # Get instance details
                response = ec2.describe_instances(InstanceIds=[instance_id])
                instance = response['Reservations'][0]['Instances'][0]
                instance_type = instance.get('InstanceType', 'unknown')
                
                allowed_types = os.environ.get('ALLOWED_INSTANCE_TYPES', 't2.micro,t3.micro').split(',')
                
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

TIME: {datetime.utcnow().isoformat()}Z
REGION: {os.environ.get('HOME_REGION', 'us-east-1')}

Your free tier is PROTECTED! 💰
            """
            
            sns.publish(
                TopicArn=os.environ['SNS_TOPIC_ARN'],
                Subject="🚨 FinOps Prevention - Expensive Resource Blocked",
                Message=alert_message
            )
            
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Guardian scan completed',
                'prevented_actions': prevented_actions,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        error_msg = f"Guardian error: {str(e)}"
        print(error_msg)
        
        # Alert on guardian failure
        sns.publish(
            TopicArn=os.environ['SNS_TOPIC_ARN'],
            Subject="⚠️ FinOps Guardian Error",
            Message=f"Guardian Lambda failed: {error_msg}"
        )
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        }