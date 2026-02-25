#!/bin/bash

# Frontend Deployment Script
# Builds and deploys to EC2 via rsync

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
EC2_HOST="13.126.25.28"
EC2_USER="ec2-user"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SSH_KEY="${SCRIPT_DIR}/../badminton-analyzer-key.pem"
REMOTE_PATH="/var/www/badminton-analyzer"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Frontend Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Host: ${EC2_HOST}"
echo "Remote Path: ${REMOTE_PATH}"
echo ""

# Change to frontend directory
cd "$(dirname "$0")"

# Step 1: Install dependencies (if needed)
echo -e "${GREEN}[1/4] Checking dependencies...${NC}"
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Step 2: Build (VITE_ env vars are baked in at build time)
echo -e "${GREEN}[2/4] Building frontend...${NC}"
if [ -f ../.env ]; then
    GOOGLE_CLIENT_ID=$(grep '^GOOGLE_CLIENT_ID=' ../.env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    DD_RUM_APP_ID=$(grep '^DD_RUM_APPLICATION_ID=' ../.env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    DD_RUM_TOKEN=$(grep '^DD_RUM_CLIENT_TOKEN=' ../.env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
fi
export VITE_GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID}"
export VITE_DD_RUM_APPLICATION_ID="${DD_RUM_APP_ID}"
export VITE_DD_RUM_CLIENT_TOKEN="${DD_RUM_TOKEN}"
echo "  VITE_GOOGLE_CLIENT_ID=${VITE_GOOGLE_CLIENT_ID:+(set)}"
echo "  VITE_DD_RUM_APPLICATION_ID=${VITE_DD_RUM_APPLICATION_ID:+(set)}"
echo "  VITE_DD_RUM_CLIENT_TOKEN=${VITE_DD_RUM_CLIENT_TOKEN:+(set)}"
npm run build

# Step 3: Deploy to EC2
echo -e "${GREEN}[3/4] Deploying to EC2...${NC}"

# Create temp dir, copy files, then move to final location
ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_HOST} "rm -rf /tmp/frontend-dist && mkdir -p /tmp/frontend-dist"
scp -i ${SSH_KEY} -o StrictHostKeyChecking=no -r dist/* ${EC2_USER}@${EC2_HOST}:/tmp/frontend-dist/
ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_HOST} "sudo rm -rf ${REMOTE_PATH}/* && sudo cp -r /tmp/frontend-dist/* ${REMOTE_PATH}/ && rm -rf /tmp/frontend-dist"

# Step 4: Verify
echo -e "${GREEN}[4/4] Verifying deployment...${NC}"
ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_HOST} "ls -la ${REMOTE_PATH}/ | head -10"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Frontend Deployment Successful!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Site: https://pushup.neymo.ai"
