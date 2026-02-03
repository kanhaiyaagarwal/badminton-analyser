# Badminton Analyzer - Deployment Guide

## Table of Contents
- [Local Development](#local-development)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [AWS Deployment](#aws-deployment)
- [Environment Variables](#environment-variables)

---

## Local Development

### Prerequisites
- Python 3.9+
- Node.js 18+
- npm or yarn

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

## Production Deployment

### Backend (FastAPI)

#### Option 1: Systemd Service (Linux)

```bash
# 1. Install dependencies system-wide or in venv
pip install -r requirements-web.txt gunicorn

# 2. Create systemd service file
sudo nano /etc/systemd/system/badminton-api.service
```

```ini
[Unit]
Description=Badminton Analyzer API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/badminton-analyser
Environment="PATH=/path/to/badminton-analyser/venv/bin"
EnvironmentFile=/path/to/badminton-analyser/.env
ExecStart=/path/to/badminton-analyser/venv/bin/gunicorn api.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile /var/log/badminton-api/access.log \
    --error-logfile /var/log/badminton-api/error.log

[Install]
WantedBy=multi-user.target
```

```bash
# 3. Start and enable service
sudo systemctl daemon-reload
sudo systemctl start badminton-api
sudo systemctl enable badminton-api

# 4. Check status
sudo systemctl status badminton-api
```

#### Option 2: PM2 (Node.js process manager)

```bash
# Install PM2
npm install -g pm2

# Create ecosystem file
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'badminton-api',
    script: 'venv/bin/uvicorn',
    args: 'api.main:app --host 0.0.0.0 --port 8000',
    cwd: '/path/to/badminton-analyser',
    env: {
      NODE_ENV: 'production'
    }
  }]
}
EOF

# Start with PM2
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### Frontend (Vue.js)

#### Build for Production

```bash
cd frontend

# Build static files
npm run build

# Output will be in frontend/dist/
```

#### Serve with Nginx

```bash
# 1. Install Nginx
sudo apt install nginx

# 2. Create Nginx config
sudo nano /etc/nginx/sites-available/badminton-analyzer
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend (Vue.js static files)
    root /path/to/badminton-analyser/frontend/dist;
    index index.html;

    # Handle Vue Router (SPA)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # WebSocket proxy
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # Static uploads (if not using S3)
    location /uploads/ {
        alias /path/to/badminton-analyser/uploads/;
    }
}
```

```bash
# 3. Enable site and restart Nginx
sudo ln -s /etc/nginx/sites-available/badminton-analyzer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Add SSL with Certbot

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## Docker Deployment

### Dockerfile (Backend)

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OpenCV and MediaPipe
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt gunicorn

# Copy application
COPY api/ ./api/
COPY v2_court_bounded_analyzer.py .

# Create directories
RUN mkdir -p uploads analysis_output

# Expose port
EXPOSE 8000

# Run with Gunicorn
CMD ["gunicorn", "api.main:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000"]
```

### Dockerfile (Frontend)

Create `frontend/Dockerfile`:

```dockerfile
# Build stage
FROM node:18-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: .
    container_name: badminton-api
    env_file: .env
    volumes:
      - ./uploads:/app/uploads
      - ./analysis_output:/app/analysis_output
    ports:
      - "8000:8000"
    depends_on:
      - db
    restart: unless-stopped

  frontend:
    build: ./frontend
    container_name: badminton-frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

  db:
    image: mysql:8.0
    container_name: badminton-db
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD:-rootpass}
      MYSQL_DATABASE: badminton_analyzer
      MYSQL_USER: ${DB_USER:-badminton}
      MYSQL_PASSWORD: ${DB_PASSWORD:-badminton123}
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"
    restart: unless-stopped

volumes:
  mysql_data:
```

### Run with Docker Compose

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## AWS Deployment

### Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ CloudFront  │────▶│   S3        │     │   RDS       │
│ (CDN)       │     │ (Frontend)  │     │ (MySQL)     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                       │
       ▼                                       │
┌─────────────┐     ┌─────────────┐            │
│   ALB       │────▶│   ECS/EC2   │────────────┘
│             │     │ (Backend)   │
└─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   S3        │
                    │ (Uploads)   │
                    └─────────────┘
```

### Step 1: Create RDS MySQL Database

```bash
# Using AWS CLI
aws rds create-db-instance \
    --db-instance-identifier badminton-db \
    --db-instance-class db.t3.micro \
    --engine mysql \
    --master-username admin \
    --master-user-password YOUR_PASSWORD \
    --allocated-storage 20
```

### Step 2: Create S3 Buckets

```bash
# Create bucket for uploads/outputs
aws s3 mb s3://badminton-analyzer-storage

# Create bucket for frontend (static hosting)
aws s3 mb s3://badminton-analyzer-frontend

# Enable static website hosting for frontend
aws s3 website s3://badminton-analyzer-frontend \
    --index-document index.html \
    --error-document index.html
```

### Step 3: Deploy Backend to ECS

Create `task-definition.json`:

```json
{
  "family": "badminton-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "badminton-api",
      "image": "YOUR_ECR_REPO/badminton-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "USE_S3", "value": "true"},
        {"name": "S3_BUCKET", "value": "badminton-analyzer-storage"},
        {"name": "AWS_REGION", "value": "us-east-1"}
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:db-url"
        },
        {
          "name": "JWT_SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:jwt-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/badminton-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

```bash
# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create ECS service
aws ecs create-service \
    --cluster your-cluster \
    --service-name badminton-api \
    --task-definition badminton-api \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

### Step 4: Deploy Frontend to S3 + CloudFront

```bash
# Build frontend
cd frontend
npm run build

# Upload to S3
aws s3 sync dist/ s3://badminton-analyzer-frontend --delete

# Create CloudFront distribution (via console or CLI)
# Point to S3 bucket with custom origin for /api/* to ALB
```

### Step 5: Configure Environment Variables

In AWS, use **Secrets Manager** or **Parameter Store**:

```bash
# Store secrets
aws secretsmanager create-secret \
    --name badminton/prod/db-url \
    --secret-string "mysql+pymysql://user:pass@rds-host:3306/badminton"

aws secretsmanager create-secret \
    --name badminton/prod/jwt-secret \
    --secret-string "your-super-secret-jwt-key"
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `mysql+pymysql://user:pass@host:3306/db` |
| `JWT_SECRET_KEY` | Secret for JWT tokens | `your-secret-key-min-32-chars` |

### Optional Variables (S3)

| Variable | Description | Example |
|----------|-------------|---------|
| `USE_S3` | Enable S3 storage | `true` |
| `S3_BUCKET` | S3 bucket name | `my-bucket` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `AWS_ACCESS_KEY_ID` | AWS access key | (use IAM roles on AWS) |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | (use IAM roles on AWS) |
| `CLOUDFRONT_DOMAIN` | CloudFront domain for CDN | `d123.cloudfront.net` |

### Optional Variables (Other)

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5173` |
| `MAX_UPLOAD_SIZE_MB` | Max upload size | `500` |
| `MAX_CONCURRENT_JOBS` | Max concurrent analysis jobs | `2` |

---

## Health Checks

### Backend Health Check

```bash
curl http://localhost:8000/health
# Response: {"status": "healthy"}
```

### Frontend Health Check

```bash
curl http://localhost/
# Should return index.html
```

---

## Troubleshooting

### Common Issues

1. **CORS errors**: Check `CORS_ORIGINS` in `.env`
2. **WebSocket not connecting**: Ensure Nginx/ALB supports WebSocket upgrade
3. **S3 upload fails**: Check IAM permissions and bucket policy
4. **Database connection fails**: Verify `DATABASE_URL` and network access

### Logs

```bash
# Backend logs (systemd)
sudo journalctl -u badminton-api -f

# Backend logs (Docker)
docker logs badminton-api -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```
