# Badminton Analyzer - Deployment Guide

## Table of Contents
- [Quick Deployment](#quick-deployment)
- [Local Development](#local-development)
- [Production Deployment (AWS ECS)](#production-deployment-aws-ecs)
- [Database Migrations](#database-migrations)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

---

## Quick Deployment

### Prerequisites
- AWS CLI configured with appropriate credentials
- Docker installed locally
- SSH key for EC2 access (`badminton-analyzer-key.pem`)

### Deploy Backend (ECS)

```bash
# From project root
./deploy.sh
```

This will:
1. Build Docker image
2. Push to ECR
3. Register new ECS task definition
4. Update ECS service with zero-downtime deployment

### Deploy Frontend (EC2/Nginx)

```bash
# From project root
./frontend/deploy.sh
```

This will:
1. Build Vue.js frontend
2. Copy dist files to EC2 via SCP
3. Update nginx served files

### Endpoints

| Service | URL |
|---------|-----|
| Frontend | https://badminton.neymo.ai |
| API | http://13.126.25.28:8002 |
| API Docs | http://13.126.25.28:8002/docs |
| Health Check | http://13.126.25.28:8002/health |

---

## Local Development

### Prerequisites
- Python 3.9+
- Node.js 18+
- npm or yarn
- MySQL (or SQLite for quick testing)

### Backend Setup

```bash
# 1. Clone and navigate to project
cd badminton-analyser

# 2. Create Python virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements-web.txt

# 4. Create .env file
cp .env.example .env
# Edit .env with your settings

# 5. Run backend server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`
API docs at: `http://localhost:8000/docs`

### Frontend Setup

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Run development server
npm run dev
```

Frontend will be available at: `http://localhost:5173`

---

## Production Deployment (AWS ECS)

### Architecture

```
                         ┌─────────────────┐
                         │   Route 53      │
                         │ badminton.neymo.ai
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │     Nginx       │
                         │   (EC2 Host)    │
                         └────────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
     ┌────────▼────────┐ ┌───────▼────────┐ ┌───────▼───────┐
     │  Static Files   │ │   API Proxy    │ │  WS Proxy     │
     │ /var/www/...    │ │   :8002        │ │   :8002       │
     └─────────────────┘ └───────┬────────┘ └───────┬───────┘
                                 │                   │
                         ┌───────▼───────────────────▼───────┐
                         │          ECS Container            │
                         │     badminton-analyzer:latest     │
                         │            :8000                  │
                         └───────────────┬───────────────────┘
                                         │
                         ┌───────────────▼───────────────────┐
                         │           RDS MySQL               │
                         │     badminton_analyzer DB         │
                         └───────────────────────────────────┘
```

### Backend Deployment Process

The `deploy.sh` script handles the full deployment:

```bash
./deploy.sh [image-tag]
```

**What it does:**

1. **Login to ECR**
   ```bash
   aws ecr get-login-password | docker login --username AWS ...
   ```

2. **Build Docker image** (linux/amd64 for EC2)
   ```bash
   docker build --platform linux/amd64 -f Dockerfile.deploy -t badminton-analyzer:tag .
   ```

3. **Push to ECR**
   ```bash
   docker push 453533986084.dkr.ecr.ap-south-1.amazonaws.com/badminton-analyzer:tag
   ```

4. **Register new task definition**
   - Updates image tag in task-definition.json
   - Registers with ECS

5. **Zero-downtime deployment**
   - Scale service to 0
   - Wait for old task to stop
   - Scale back to 1 with new task definition
   - Wait for health check

### Frontend Deployment Process

The `frontend/deploy.sh` script handles frontend deployment:

```bash
./frontend/deploy.sh
```

**What it does:**

1. **Install dependencies** (if needed)
   ```bash
   npm install
   ```

2. **Build production bundle**
   ```bash
   npm run build
   ```

3. **Copy to EC2**
   ```bash
   scp -r dist/* ec2-user@13.126.25.28:/var/www/badminton-analyzer/
   ```

### Manual Deployment (if needed)

**Backend:**
```bash
# SSH into EC2
ssh -i badminton-analyzer-key.pem ec2-user@13.126.25.28

# Check running containers
docker ps

# View logs
docker logs <container-id> -f

# Force new deployment
aws ecs update-service --cluster badminton-analyzer-cluster \
    --service badminton-analyzer-service --force-new-deployment
```

**Frontend:**
```bash
# Build locally
cd frontend && npm run build

# Copy to server
scp -i badminton-analyzer-key.pem -r dist/* ec2-user@13.126.25.28:/var/www/badminton-analyzer/
```

---

## Database Migrations

### Initial Setup (New Database)

Tables are auto-created by SQLAlchemy on app startup. For production, run these migrations:

### Admin Panel Tables (invite codes, whitelist, waitlist)

```sql
-- Invite codes table
CREATE TABLE IF NOT EXISTS invite_codes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    max_uses INT DEFAULT 0,
    times_used INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_by INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    note VARCHAR(255) NULL,
    INDEX idx_invite_code (code),
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Whitelist emails table
CREATE TABLE IF NOT EXISTS whitelist_emails (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    note VARCHAR(255) NULL,
    created_by INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_whitelist_email (email),
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Waitlist table
CREATE TABLE IF NOT EXISTS waitlist (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100) NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP NULL,
    approved_by INT NULL,
    invite_code_id INT NULL,
    INDEX idx_waitlist_email (email),
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (invite_code_id) REFERENCES invite_codes(id) ON DELETE SET NULL
);

-- Add is_admin to users if not exists
ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
```

### Email Verification Tables (OTP)

```sql
-- Add email verification columns to users
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN email_verified_at TIMESTAMP NULL;

-- Mark existing users as verified (grandfathering)
UPDATE users SET email_verified = TRUE;

-- Email OTPs table
CREATE TABLE IF NOT EXISTS email_otps (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    code VARCHAR(6) NOT NULL,
    attempts INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    verified_at TIMESTAMP NULL,
    INDEX idx_otp_user (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### Seed Data

```sql
-- Create default invite code
INSERT INTO invite_codes (code, note, is_active, max_uses, times_used)
VALUES ('BADMINTON2024', 'Default invite code', TRUE, 0, 0);

-- Whitelist an email (optional)
INSERT INTO whitelist_emails (email, note)
VALUES ('admin@example.com', 'Admin user');
```

---

## Environment Variables

### Task Definition (ECS)

Environment variables are set in `task-definition.json`:

```json
{
  "environment": [
    {"name": "ENVIRONMENT", "value": "production"},
    {"name": "DEBUG", "value": "false"},
    ...
  ],
  "secrets": [
    {"name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:..."},
    {"name": "JWT_SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:..."}
  ]
}
```

### Required Variables

| Variable | Description | Source |
|----------|-------------|--------|
| `DATABASE_URL` | MySQL connection string | Secrets Manager |
| `JWT_SECRET_KEY` | JWT signing secret | Secrets Manager |

### App Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `APP_NAME` | Application name | `Badminton Analyzer API` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5173,...` |

### File Storage

| Variable | Description | Default |
|----------|-------------|---------|
| `UPLOAD_DIR` | Upload directory | `/app/uploads` |
| `OUTPUT_DIR` | Analysis output directory | `/app/analysis_output` |
| `MAX_UPLOAD_SIZE_MB` | Max upload size | `500` |
| `USE_S3` | Enable S3 storage | `false` |
| `S3_BUCKET` | S3 bucket name | - |

### Authentication

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL | `7` |

### Email Settings (SES)

| Variable | Description | Default |
|----------|-------------|---------|
| `EMAIL_PROVIDER` | Email provider: `console`, `smtp`, `ses` | `console` |
| `SMTP_FROM_EMAIL` | Sender email address | `noreply@example.com` |
| `SMTP_FROM_NAME` | Sender display name | `Badminton Analyzer` |
| `SES_REGION` | AWS SES region | (uses `AWS_REGION`) |

### OTP Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `REQUIRE_EMAIL_VERIFICATION` | Enable/disable OTP verification | `true` |
| `OTP_EXPIRE_MINUTES` | OTP expiration time | `10` |
| `OTP_MAX_ATTEMPTS` | Max verification attempts | `5` |
| `OTP_RESEND_COOLDOWN_SECONDS` | Cooldown between resends | `60` |

### Adding New Environment Variables

1. **Update `task-definition.json`:**
   ```json
   {"name": "NEW_VAR", "value": "value"}
   ```

2. **Update `api/config.py`:**
   ```python
   new_var: str = "default"
   ```

3. **Update `.env.example`:**
   ```env
   NEW_VAR=default
   ```

4. **Redeploy:**
   ```bash
   ./deploy.sh
   ```

### AWS Secrets Manager

Sensitive values are stored in Secrets Manager:

```bash
# View secrets
aws secretsmanager list-secrets --region ap-south-1

# Get secret value
aws secretsmanager get-secret-value \
    --secret-id badminton-analyzer/database-url \
    --region ap-south-1

# Update secret
aws secretsmanager update-secret \
    --secret-id badminton-analyzer/database-url \
    --secret-string "new-connection-string" \
    --region ap-south-1
```

---

## Troubleshooting

### Check Service Status

```bash
# ECS service status
aws ecs describe-services \
    --cluster badminton-analyzer-cluster \
    --services badminton-analyzer-service \
    --region ap-south-1

# Running tasks
aws ecs list-tasks \
    --cluster badminton-analyzer-cluster \
    --service-name badminton-analyzer-service \
    --region ap-south-1
```

### View Logs

```bash
# CloudWatch logs (via AWS CLI)
aws logs tail /ecs/badminton-analyzer --since 30m --region ap-south-1

# Datadog logs
# https://us5.datadoghq.com/logs?query=service%3Abadminton-analyzer

# SSH into EC2 and check Docker logs
ssh -i badminton-analyzer-key.pem ec2-user@13.126.25.28
docker logs $(docker ps -q --filter "name=badminton") -f
```

### Common Issues

1. **Task fails to start**
   - Check CloudWatch logs for errors
   - Verify secrets are accessible
   - Check memory/CPU limits

2. **Health check failing**
   - Container might still be starting (60s startup)
   - Check if port 8000 is exposed
   - Verify `/health` endpoint works

3. **Database connection error**
   - Verify DATABASE_URL secret
   - Check security group allows MySQL (3306)
   - Verify RDS is running

4. **Email not sending**
   - Check `EMAIL_PROVIDER` is set to `ses`
   - Verify SES domain is verified
   - Check SES is not in sandbox mode (or recipient is verified)
   - Verify IAM role has `ses:SendEmail` permission

5. **Frontend not updating**
   - Clear browser cache
   - Check nginx is serving correct files:
     ```bash
     ssh -i badminton-analyzer-key.pem ec2-user@13.126.25.28 \
         "ls -la /var/www/badminton-analyzer/"
     ```

### Rollback

```bash
# List task definition revisions
aws ecs list-task-definitions \
    --family-prefix badminton-analyzer-task \
    --region ap-south-1

# Deploy specific revision
aws ecs update-service \
    --cluster badminton-analyzer-cluster \
    --service badminton-analyzer-service \
    --task-definition badminton-analyzer-task:5 \
    --region ap-south-1
```

---

## IAM Permissions

### ECS Task Execution Role

The `ecsTaskExecutionRole` needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:ap-south-1:453533986084:secret:badminton-analyzer/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

### Add SES Permission (if missing)

```bash
aws iam put-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-name SES-SendEmail \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": ["ses:SendEmail", "ses:SendRawEmail"],
            "Resource": "*"
        }]
    }'
```
