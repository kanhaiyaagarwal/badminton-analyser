#!/bin/bash

# Badminton Analyzer - One-time Infrastructure Setup
# Creates ECR repo, ECS cluster, EC2 instance, and secrets
# Run this ONCE before first deployment

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
AWS_REGION="ap-south-1"
AWS_ACCOUNT_ID="453533986084"
ECR_REPO_NAME="badminton-analyzer"
CLUSTER_NAME="badminton-analyzer-cluster"
SERVICE_NAME="badminton-analyzer-service"

# EC2 Configuration
INSTANCE_TYPE="t3.large"
AMI_ID="ami-0f58b397bc5c1f2e8"  # Amazon Linux 2023 ECS-optimized AMI for ap-south-1
KEY_NAME="badminton-analyzer-key"
SECURITY_GROUP_NAME="badminton-analyzer-sg"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Badminton Analyzer Infrastructure Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Create ECR Repository
echo -e "${GREEN}[1/8] Creating ECR Repository...${NC}"
if aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${AWS_REGION} 2>/dev/null; then
    echo "ECR repository already exists"
else
    aws ecr create-repository \
        --repository-name ${ECR_REPO_NAME} \
        --region ${AWS_REGION} \
        --image-scanning-configuration scanOnPush=true
    echo "ECR repository created"
fi

# Step 2: Skipped - Using Datadog for logging instead of CloudWatch
echo -e "${GREEN}[2/8] Skipping CloudWatch (using Datadog)...${NC}"

# Step 3: Create Security Group
echo -e "${GREEN}[3/8] Creating Security Group...${NC}"
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text --region ${AWS_REGION})

SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=${SECURITY_GROUP_NAME}" \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region ${AWS_REGION} 2>/dev/null)

if [ "$SG_ID" = "None" ] || [ -z "$SG_ID" ]; then
    SG_ID=$(aws ec2 create-security-group \
        --group-name ${SECURITY_GROUP_NAME} \
        --description "Security group for Badminton Analyzer" \
        --vpc-id ${VPC_ID} \
        --region ${AWS_REGION} \
        --query 'GroupId' \
        --output text)

    # Add inbound rules
    aws ec2 authorize-security-group-ingress \
        --group-id ${SG_ID} \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0 \
        --region ${AWS_REGION}

    aws ec2 authorize-security-group-ingress \
        --group-id ${SG_ID} \
        --protocol tcp \
        --port 8002 \
        --cidr 0.0.0.0/0 \
        --region ${AWS_REGION}

    aws ec2 authorize-security-group-ingress \
        --group-id ${SG_ID} \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --region ${AWS_REGION}

    aws ec2 authorize-security-group-ingress \
        --group-id ${SG_ID} \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region ${AWS_REGION}

    echo "Security group created: ${SG_ID}"
else
    echo "Security group already exists: ${SG_ID}"
fi

# Step 4: Create Key Pair (if not exists)
echo -e "${GREEN}[4/8] Creating Key Pair...${NC}"
if aws ec2 describe-key-pairs --key-names ${KEY_NAME} --region ${AWS_REGION} 2>/dev/null; then
    echo "Key pair already exists"
else
    aws ec2 create-key-pair \
        --key-name ${KEY_NAME} \
        --query 'KeyMaterial' \
        --output text \
        --region ${AWS_REGION} > ${KEY_NAME}.pem
    chmod 400 ${KEY_NAME}.pem
    echo -e "${YELLOW}Key pair created and saved to ${KEY_NAME}.pem${NC}"
    echo -e "${YELLOW}IMPORTANT: Keep this file safe - you need it to SSH into the instance${NC}"
fi

# Step 5: Create ECS Cluster
echo -e "${GREEN}[5/8] Creating ECS Cluster...${NC}"
if aws ecs describe-clusters --clusters ${CLUSTER_NAME} --region ${AWS_REGION} --query 'clusters[0].status' --output text 2>/dev/null | grep -q "ACTIVE"; then
    echo "ECS cluster already exists and is active"
else
    aws ecs create-cluster \
        --cluster-name ${CLUSTER_NAME} \
        --region ${AWS_REGION}
    echo "ECS cluster created"
fi

# Step 6: Create EC2 Instance with ECS Agent
echo -e "${GREEN}[6/8] Creating EC2 Instance (t3.large)...${NC}"

# Check if instance already exists
EXISTING_INSTANCE=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=badminton-analyzer-ecs" "Name=instance-state-name,Values=running,pending" \
    --query 'Reservations[0].Instances[0].InstanceId' \
    --output text \
    --region ${AWS_REGION} 2>/dev/null)

if [ "$EXISTING_INSTANCE" != "None" ] && [ -n "$EXISTING_INSTANCE" ]; then
    echo "EC2 instance already exists: ${EXISTING_INSTANCE}"
    INSTANCE_ID=${EXISTING_INSTANCE}
else
    # User data script to configure ECS agent
    USER_DATA=$(cat <<'EOF'
#!/bin/bash
echo "ECS_CLUSTER=badminton-analyzer-cluster" >> /etc/ecs/ecs.config
echo "ECS_ENABLE_TASK_IAM_ROLE=true" >> /etc/ecs/ecs.config
echo "ECS_ENABLE_CONTAINER_METADATA=true" >> /etc/ecs/ecs.config

# Create data directories for volume mounts
mkdir -p /data/badminton-analyzer/uploads
mkdir -p /data/badminton-analyzer/analysis_output
chmod -R 777 /data/badminton-analyzer

# Install updates
yum update -y
EOF
)

    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id ${AMI_ID} \
        --instance-type ${INSTANCE_TYPE} \
        --key-name ${KEY_NAME} \
        --security-group-ids ${SG_ID} \
        --iam-instance-profile Name=ecsInstanceRole \
        --user-data "${USER_DATA}" \
        --block-device-mappings "[{\"DeviceName\":\"/dev/xvda\",\"Ebs\":{\"VolumeSize\":50,\"VolumeType\":\"gp3\"}}]" \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=badminton-analyzer-ecs}]" \
        --region ${AWS_REGION} \
        --query 'Instances[0].InstanceId' \
        --output text)

    echo "EC2 instance created: ${INSTANCE_ID}"
    echo "Waiting for instance to be running..."
    aws ec2 wait instance-running --instance-ids ${INSTANCE_ID} --region ${AWS_REGION}
fi

# Get instance public IP
INSTANCE_IP=$(aws ec2 describe-instances \
    --instance-ids ${INSTANCE_ID} \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text \
    --region ${AWS_REGION})

echo "Instance IP: ${INSTANCE_IP}"

# Step 7: Create Secrets in AWS Secrets Manager
echo -e "${GREEN}[7/8] Creating Secrets in Secrets Manager...${NC}"
echo -e "${YELLOW}You need to manually update these secrets with actual values!${NC}"

# Database URL secret
if aws secretsmanager describe-secret --secret-id badminton-analyzer/database-url --region ${AWS_REGION} 2>/dev/null; then
    echo "Database URL secret already exists"
else
    aws secretsmanager create-secret \
        --name badminton-analyzer/database-url \
        --description "Database connection URL for Badminton Analyzer" \
        --secret-string "mysql+pymysql://user:password@host:3306/badminton_analyzer" \
        --region ${AWS_REGION}
    echo "Database URL secret created - UPDATE IT with real credentials!"
fi

# JWT secret
if aws secretsmanager describe-secret --secret-id badminton-analyzer/jwt-secret-key --region ${AWS_REGION} 2>/dev/null; then
    echo "JWT secret already exists"
else
    JWT_SECRET=$(openssl rand -hex 32)
    aws secretsmanager create-secret \
        --name badminton-analyzer/jwt-secret-key \
        --description "JWT secret key for Badminton Analyzer" \
        --secret-string "${JWT_SECRET}" \
        --region ${AWS_REGION}
    echo "JWT secret created"
fi

# Datadog API key
if aws secretsmanager describe-secret --secret-id badminton-analyzer/datadog-api-key --region ${AWS_REGION} 2>/dev/null; then
    echo "Datadog API key secret already exists"
else
    aws secretsmanager create-secret \
        --name badminton-analyzer/datadog-api-key \
        --description "Datadog API key for Badminton Analyzer" \
        --secret-string "YOUR_DATADOG_API_KEY" \
        --region ${AWS_REGION}
    echo "Datadog API key secret created - UPDATE IT with your actual Datadog API key!"
fi

# Step 8: Create ECS Service
echo -e "${GREEN}[8/8] Registering Task Definition and Creating Service...${NC}"

# Wait for EC2 to register with ECS cluster
echo "Waiting for EC2 instance to register with ECS cluster (this may take 2-3 minutes)..."
REGISTERED=false
for i in {1..30}; do
    CONTAINER_INSTANCES=$(aws ecs list-container-instances \
        --cluster ${CLUSTER_NAME} \
        --region ${AWS_REGION} \
        --query 'length(containerInstanceArns)' \
        --output text 2>/dev/null)

    if [ "$CONTAINER_INSTANCES" != "0" ] && [ -n "$CONTAINER_INSTANCES" ]; then
        REGISTERED=true
        echo "EC2 instance registered with ECS cluster!"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 10
done

if [ "$REGISTERED" = false ]; then
    echo -e "${YELLOW}Warning: EC2 instance not yet registered with ECS cluster.${NC}"
    echo "This might take a few more minutes. You can check manually with:"
    echo "aws ecs list-container-instances --cluster ${CLUSTER_NAME} --region ${AWS_REGION}"
fi

# Register task definition
echo "Registering task definition..."
TASK_DEF_ARN=$(aws ecs register-task-definition \
    --cli-input-json file://task-definition.json \
    --region ${AWS_REGION} \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)
echo "Task definition registered: ${TASK_DEF_ARN}"

# Check if service exists
SERVICE_EXISTS=$(aws ecs describe-services \
    --cluster ${CLUSTER_NAME} \
    --services ${SERVICE_NAME} \
    --region ${AWS_REGION} \
    --query 'services[0].status' \
    --output text 2>/dev/null)

if [ "$SERVICE_EXISTS" = "ACTIVE" ]; then
    echo "ECS service already exists"
else
    # Create service
    aws ecs create-service \
        --cluster ${CLUSTER_NAME} \
        --service-name ${SERVICE_NAME} \
        --task-definition badminton-analyzer-task \
        --desired-count 1 \
        --launch-type EC2 \
        --region ${AWS_REGION}
    echo "ECS service created"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Infrastructure Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Summary:"
echo "  ECR Repository:  ${ECR_REPO_NAME}"
echo "  ECS Cluster:     ${CLUSTER_NAME}"
echo "  ECS Service:     ${SERVICE_NAME}"
echo "  EC2 Instance:    ${INSTANCE_ID}"
echo "  Instance IP:     ${INSTANCE_IP}"
echo "  Instance Type:   ${INSTANCE_TYPE} (2 vCPU, 8 GB RAM)"
echo "  Security Group:  ${SG_ID}"
echo ""
echo -e "${YELLOW}IMPORTANT: Before deploying, update the secrets:${NC}"
echo "1. Update DATABASE_URL secret with your actual database connection string:"
echo "   aws secretsmanager update-secret --secret-id badminton-analyzer/database-url --secret-string 'mysql+pymysql://user:pass@host:3306/db' --region ${AWS_REGION}"
echo ""
echo "2. Update DATADOG_API_KEY secret with your Datadog API key:"
echo "   aws secretsmanager update-secret --secret-id badminton-analyzer/datadog-api-key --secret-string 'your-datadog-api-key' --region ${AWS_REGION}"
echo ""
echo "3. SSH into EC2 instance:"
echo "   ssh -i ${KEY_NAME}.pem ec2-user@${INSTANCE_IP}"
echo ""
echo "4. Run deployment:"
echo "   ./deploy.sh"
echo ""
echo "5. Access API at:"
echo "   http://${INSTANCE_IP}:8002"
echo ""
