# 🛡️ FinOps Cost Control as Code 💸

**Infrastructure-as-Code project for AWS cost monitoring and free-tier protection using Pulumi, Lambda, and automated notifications.**

---

## 🎯 Project Objective

Build a production-ready **FinOps automation system** that:
- Monitors AWS spending with $0.01 billing alerts
- Hunts for cost-inefficient resources (unused EBS, EIPs, etc.)
- Sends real-time notifications to Discord/Slack
- Deploys across multiple environments (dev/staging/prod)
- Operates within AWS free-tier limits

---

## 🏗️ Architecture

```
EventBridge (12h schedule) → Hunter Lambda → SNS Topic → Notifier Lambda → Discord/Slack
                                ↓
                         CloudWatch Billing Alarm ($0.01)
```

**Components:**
- **Hunter Lambda**: Scans for unused/expensive resources
- **Notifier Lambda**: Sends formatted alerts to webhooks  
- **SNS Topic**: Message routing between components
- **EventBridge**: Scheduled execution every 12 hours
- **CloudWatch Alarms**: Billing threshold monitoring

---

## ✨ Features

- 🚨 **Billing Alerts**: Trip at $0.01 spending threshold
- 🔍 **Resource Hunter**: Detects NAT Gateways, unattached EIPs, orphaned EBS volumes
- 📱 **Multi-Channel Notifications**: Discord + Slack webhook support
- 🔄 **Multi-Stack Deployment**: Dev, Staging, Production environments
- ⚙️ **Feature Flags**: Toggle anomaly detection, CUR reports
- 🤖 **CI/CD Ready**: GitHub Actions automation
- 🏷️ **Tagging Strategy**: Consistent resource organization

---

## 🚀 Quick Start

### Prerequisites
- AWS Account with free-tier access
- [Pulumi CLI](https://www.pulumi.com/docs/get-started/install/) installed
- [AWS CLI](https://aws.amazon.com/cli/) configured
- Python 3.11+

### 1. Clone & Setup
```bash
git clone https://github.com/yourusername/finops-cost-control-as-code.git
cd finops-cost-control-as-code/infra
pip install -r requirements.txt
```

### 2. Configure Stack
```bash
# Initialize stack
pulumi stack init dev

# Set configuration
pulumi config set aws:region us-east-1
pulumi config set home_region us-east-1  
pulumi config set max_free_ebs_gb 30
pulumi config set enable_cur false
pulumi config set enable_anomaly_detection false

# Set webhook URLs (use test URLs for dev)
pulumi config set discord_webhook_url "https://discord.com/api/webhooks/test"
pulumi config set slack_webhook_url "https://hooks.slack.com/services/test"
```

### 3. Deploy Infrastructure
```bash
pulumi up --yes
```

### 4. Verify Deployment
```bash
# Check Lambda functions
aws lambda list-functions --region us-east-1 | grep finops

# Check SNS topics  
aws sns list-topics --region us-east-1 | grep finops

# Check billing alarms
aws cloudwatch describe-alarms --region us-east-1 | grep Billing
```

---

## 🔧 Configuration Options

| Config Key | Default | Description |
|------------|---------|-------------|
| `home_region` | `us-east-1` | Primary AWS region |
| `max_free_ebs_gb` | `30` | EBS free-tier limit (GB) |
| `enable_cur` | `false` | Enable Cost & Usage Reports |
| `enable_anomaly_detection` | `false` | Enable AWS Cost Anomaly Detection |
| `discord_webhook_url` | - | Discord webhook for notifications |
| `slack_webhook_url` | - | Slack webhook for notifications |

---

## 🌍 Multi-Environment Setup

### Development
```bash
pulumi stack select dev
pulumi config set max_free_ebs_gb 30
pulumi config set enable_cur false
```

### Staging  
```bash
pulumi stack select staging
pulumi config set max_free_ebs_gb 5
pulumi config set enable_cur true
pulumi config set enable_anomaly_detection true
```

### Production
```bash
pulumi stack select prod
pulumi config set max_free_ebs_gb 20
pulumi config set enable_cur true
pulumi config set enable_anomaly_detection true
```

---

## 🔄 CI/CD with GitHub Actions

The project includes automated deployment via GitHub Actions:

**Triggers:**
- Push to `main`, `staging`, `dev` branches
- Bi-weekly scheduled runs
- Manual dispatch

**Required Secrets:**
- `PULUMI_ACCESS_TOKEN`
- `AWS_ACCESS_KEY_ID` 
- `AWS_SECRET_ACCESS_KEY`
- `DISCORD_WEBHOOK_URL`
- `SLACK_WEBHOOK_URL`

---

## 🛡️ Security Considerations

- **Webhook URLs**: Store in GitHub Secrets, not in code
- **IAM Permissions**: Use least-privilege principle
- **Pulumi Secrets**: Encrypt sensitive configuration
- **Resource Tagging**: Enable proper cost allocation

---

## 📊 Monitoring & Logging

### CloudWatch Logs
```bash
# Hunter Lambda logs
aws logs tail /aws/lambda/hunterLambda-dev --follow

# Notifier Lambda logs  
aws logs tail /aws/lambda/notifierLambda-dev --follow
```

### SNS Message Testing
```bash
# Publish test message
aws sns publish \
  --topic-arn "arn:aws:sns:us-east-1:ACCOUNT:finops-alerts-dev" \
  --message "Test FinOps Alert"
```

---

## 🛣️ Development Journey & Challenges

### Key Issues Encountered & Solutions

#### 1. **IAM Permission Complexity**
**Problem**: Multiple permission denied errors for S3, Lambda, CloudWatch
```
AccessDenied: s3:GetBucketVersioning, logs:FilterLogEvents
```

**Solution**: Created comprehensive IAM policy with full S3 and CloudWatch access
- Iterative permission testing across 13 policy versions
- Added wildcard resources for development flexibility

#### 2. **Pulumi Secret Management**  
**Problem**: Encrypted webhook URLs in YAML causing decryption failures
```
failed to decrypt configuration key: invalid ciphertext
```

**Solution**: Moved sensitive config to environment variables and CI/CD secrets
- Removed hardcoded webhook URLs from version control
- Implemented proper secret management workflow

#### 3. **Multi-Stack Configuration**
**Problem**: Stack isolation and environment-specific settings
**Solution**: Created separate Pulumi stack configs per environment
- Dev: Basic testing with placeholder webhooks
- Staging: Full features enabled with test data
- Prod: Production webhooks and conservative limits

#### 4. **Lambda Deployment Dependencies**
**Problem**: Lambda functions failing to deploy due to missing environment variables
**Solution**: Proper dependency chaining in Pulumi code
- Ensured SNS topic creation before Lambda environment setup
- Added proper error handling in Lambda code

---

## 🚀 Future Roadmap

### Phase 2 - Enhanced Monitoring
- [ ] **Cost & Usage Reports (CUR)** with Athena queries
- [ ] **Grafana dashboards** for cost visualization  
- [ ] **Predictive cost modeling** using historical data
- [ ] **Multi-account support** for organizations

### Phase 3 - Advanced Automation
- [ ] **Auto-remediation** for unused resources
- [ ] **Reserved Instance optimization**
- [ ] **Spot instance management**
- [ ] **Resource rightsizing recommendations**

### Phase 4 - Multi-Cloud
- [ ] **Google Cloud Platform** cost monitoring
- [ ] **Azure** cost management integration
- [ ] **Unified dashboard** across cloud providers

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🎉 Acknowledgments

- **Pulumi Community** for excellent IaC tooling
- **AWS Free Tier** for enabling cost-effective learning
- **FinOps Foundation** for cost optimization best practices

---

**Built with ❤️ for the DevOps and FinOps communities**