#!/bin/bash

# Badminton Analyzer Deployment Script
# Builds Docker image and deploys to AWS ECS

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
SERVICE_NAME="badminton-analyzer-service"
CLUSTER_NAME="badminton-analyzer-cluster"

# Use git commit ID as image tag (short SHA), fallback to argument or 'latest'
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
IMAGE_TAG="${1:-${GIT_COMMIT}}"

ECR_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
FULL_IMAGE_NAME="${ECR_URL}/${ECR_REPO_NAME}:${IMAGE_TAG}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Badminton Analyzer Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Region:       ${AWS_REGION}"
echo -e "Account:      ${AWS_ACCOUNT_ID}"
echo -e "Repository:   ${ECR_REPO_NAME}"
echo -e "Cluster:      ${CLUSTER_NAME}"
echo -e "Service:      ${SERVICE_NAME}"
echo -e "Git Branch:   ${GIT_BRANCH}"
echo -e "Git Commit:   ${GIT_COMMIT}"
echo -e "Image Tag:    ${IMAGE_TAG}"
echo ""

# Step 1: Login to ECR
echo -e "${GREEN}[1/7] Logging in to AWS ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URL}

# Step 2: Build Docker image
echo -e "${GREEN}[2/7] Building Docker image...${NC}"
docker build --platform linux/amd64 -f Dockerfile.deploy -t ${ECR_REPO_NAME}:${IMAGE_TAG} .

# Step 3: Tag image for ECR
echo -e "${GREEN}[3/7] Tagging image for ECR...${NC}"
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} ${FULL_IMAGE_NAME}

# Step 4: Push to ECR
echo -e "${GREEN}[4/7] Pushing image to ECR...${NC}"
docker push ${FULL_IMAGE_NAME}

# Step 5: Update task definition with new image tag and register
echo -e "${GREEN}[5/7] Updating and registering task definition...${NC}"

# Create temporary task definition with updated image tag
TEMP_TASK_DEF=$(mktemp)
cat task-definition.json | jq --arg IMAGE "${FULL_IMAGE_NAME}" \
    '.containerDefinitions[0].image = $IMAGE' > ${TEMP_TASK_DEF}

echo "Updated task definition image to: ${FULL_IMAGE_NAME}"

# Always register new task definition with the new image tag
echo "Registering new task definition with image tag: ${IMAGE_TAG}..."
NEW_TASK_DEF=$(aws ecs register-task-definition \
    --cli-input-json file://${TEMP_TASK_DEF} \
    --region ${AWS_REGION} \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

# Clean up temp file
rm -f ${TEMP_TASK_DEF}

if [ $? -eq 0 ]; then
    echo "Registered new task definition: ${NEW_TASK_DEF}"
else
    echo -e "${RED}Failed to register task definition${NC}"
    exit 1
fi

# Step 6: Deploy with proper task definition update
echo -e "${GREEN}[6/7] Updating service to use new task definition...${NC}"

# Update service to new task definition AND scale to 0
echo "Updating service: task-definition=${NEW_TASK_DEF}, desired-count=0"
aws ecs update-service \
    --cluster ${CLUSTER_NAME} \
    --service ${SERVICE_NAME} \
    --task-definition ${NEW_TASK_DEF} \
    --desired-count 0 \
    --region ${AWS_REGION} > /dev/null

echo "Service updated to new task definition with desired-count=0"
echo "Waiting 5s for update to propagate..."
sleep 5

# Get current running task (if any)
CURRENT_TASK=$(aws ecs list-tasks \
    --cluster ${CLUSTER_NAME} \
    --service-name ${SERVICE_NAME} \
    --desired-status RUNNING \
    --region ${AWS_REGION} \
    --query 'taskArns[0]' \
    --output text)

if [ "$CURRENT_TASK" != "None" ] && [ -n "$CURRENT_TASK" ]; then
    CURRENT_TASK_ID=$(echo $CURRENT_TASK | awk -F'/' '{print $NF}')
    echo "Stopping old task: ${CURRENT_TASK_ID}"

    aws ecs stop-task \
        --cluster ${CLUSTER_NAME} \
        --task ${CURRENT_TASK} \
        --reason "Deployment: Freeing memory for new task" \
        --region ${AWS_REGION} > /dev/null 2>&1
fi

# Wait for ALL tasks to stop
echo "Waiting for all tasks to stop..."
MAX_WAIT=120
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    REMAINING_TASKS=$(aws ecs list-tasks \
        --cluster ${CLUSTER_NAME} \
        --service-name ${SERVICE_NAME} \
        --desired-status RUNNING \
        --region ${AWS_REGION} \
        --query 'length(taskArns)' \
        --output text)

    if [ "$REMAINING_TASKS" = "0" ]; then
        echo "All tasks stopped (waited ${WAITED}s)"
        break
    fi

    if [ $((WAITED % 10)) -eq 0 ]; then
        echo "Still waiting... (${WAITED}s, ${REMAINING_TASKS} task(s) still running)"
    fi
    sleep 5
    WAITED=$((WAITED + 5))
done

if [ "$REMAINING_TASKS" != "0" ]; then
    echo -e "${RED}ERROR: Tasks still running after ${WAITED}s${NC}"
    exit 1
fi

# Wait for container cleanup and memory release
echo "Waiting 20s for container cleanup and memory release..."
sleep 20

# Step 7: Scale back up with new task definition
echo -e "${GREEN}[7/7] Starting new task...${NC}"

aws ecs update-service \
    --cluster ${CLUSTER_NAME} \
    --service ${SERVICE_NAME} \
    --desired-count 1 \
    --region ${AWS_REGION} > /dev/null

echo "Desired count set to 1, ECS will start new task..."

echo "Waiting for new task to start (60 seconds for video processing container)..."
sleep 60

# Verify deployment
echo -e "${GREEN}Verifying deployment...${NC}"

# Check service events for errors
SERVICE_EVENTS=$(aws ecs describe-services \
    --cluster ${CLUSTER_NAME} \
    --services ${SERVICE_NAME} \
    --region ${AWS_REGION} \
    --query 'services[0].events[0:5]' \
    --output json)

if echo "$SERVICE_EVENTS" | grep -qi "error\|failed\|unable\|insufficient"; then
    echo -e "${YELLOW}Warning: Potential issues detected in service events${NC}"
    echo "$SERVICE_EVENTS" | jq -r '.[] | "\(.createdAt): \(.message)"' | head -5
fi

# Check task status
RUNNING_TASKS=$(aws ecs list-tasks \
    --cluster ${CLUSTER_NAME} \
    --service-name ${SERVICE_NAME} \
    --desired-status RUNNING \
    --region ${AWS_REGION} \
    --query 'length(taskArns)' \
    --output text)

if [ "$RUNNING_TASKS" = "0" ]; then
    echo -e "${RED}Error: No running tasks found!${NC}"
    echo "Recent service events:"
    echo "$SERVICE_EVENTS" | jq -r '.[] | "\(.createdAt): \(.message)"'
    echo ""
    echo "Check CloudWatch logs for errors:"
    echo "aws logs tail /ecs/badminton-analyzer --since 5m --region ${AWS_REGION}"
    exit 1
else
    echo -e "${GREEN}${RUNNING_TASKS} task(s) running${NC}"
fi

# Wait for health check
echo "Waiting for health check (30 seconds)..."
sleep 30

# Final verification
FINAL_RUNNING_TASKS=$(aws ecs list-tasks \
    --cluster ${CLUSTER_NAME} \
    --service-name ${SERVICE_NAME} \
    --desired-status RUNNING \
    --region ${AWS_REGION} \
    --query 'length(taskArns)' \
    --output text)

if [ "$FINAL_RUNNING_TASKS" = "0" ]; then
    echo -e "${RED}Deployment Failed: Task stopped after startup${NC}"
    aws ecs describe-services \
        --cluster ${CLUSTER_NAME} \
        --services ${SERVICE_NAME} \
        --region ${AWS_REGION} \
        --query 'services[0].events[0:10]' \
        --output table
    exit 1
fi

# Verify running task is using correct task definition
RUNNING_TASK_ARN=$(aws ecs list-tasks \
    --cluster ${CLUSTER_NAME} \
    --service-name ${SERVICE_NAME} \
    --desired-status RUNNING \
    --region ${AWS_REGION} \
    --query 'taskArns[0]' \
    --output text)

if [ "$RUNNING_TASK_ARN" != "None" ] && [ -n "$RUNNING_TASK_ARN" ]; then
    RUNNING_TASK_DEF=$(aws ecs describe-tasks \
        --cluster ${CLUSTER_NAME} \
        --tasks ${RUNNING_TASK_ARN} \
        --region ${AWS_REGION} \
        --query 'tasks[0].taskDefinitionArn' \
        --output text)

    if [ "$RUNNING_TASK_DEF" != "$NEW_TASK_DEF" ]; then
        echo -e "${RED}Error: Running task is using WRONG task definition!${NC}"
        echo "Expected: ${NEW_TASK_DEF}"
        echo "Actual:   ${RUNNING_TASK_DEF}"
        exit 1
    else
        echo -e "${GREEN}Running task verified - using correct task definition${NC}"
    fi
fi

# Get EC2 instance IP
INSTANCE_IP=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=badminton-analyzer-ecs" "Name=instance-state-name,Values=running" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text \
    --region ${AWS_REGION} 2>/dev/null || echo "unknown")

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Successful!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Image pushed:        ${FULL_IMAGE_NAME}"
echo "Task definition:     ${NEW_TASK_DEF}"
echo "Service updated:     ${SERVICE_NAME}"
echo "Running tasks:       ${FINAL_RUNNING_TASKS}"
echo ""
echo "API Endpoint:        http://${INSTANCE_IP}:8002"
echo "Health Check:        http://${INSTANCE_IP}:8002/health"
echo "API Docs:            http://${INSTANCE_IP}:8002/docs"
echo ""
echo "Monitor deployment:"
echo "aws ecs describe-services --cluster ${CLUSTER_NAME} --services ${SERVICE_NAME} --region ${AWS_REGION}"
echo ""
echo "View logs in Datadog:"
echo "https://us5.datadoghq.com/logs?query=service%3Abadminton-analyzer"
echo ""
