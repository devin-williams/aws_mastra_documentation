#!/bin/bash

# Exit on error
set -e

# Set variables
AWS_REGION="${AWS_REGION:-us-east-1}"
REPO_NAME="mastra-agent"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo "🚀 Pushing Mastra Agent to ECR..."
echo "Region: $AWS_REGION"
echo "Repository: $REPO_NAME"
echo "Tag: $IMAGE_TAG"
echo ""

# Get AWS account ID
echo "📋 Getting AWS account ID..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account ID: $AWS_ACCOUNT_ID"
echo ""

# Create ECR repository (ignore error if it already exists)
echo "📦 Creating ECR repository (if it doesn't exist)..."
aws ecr create-repository --repository-name $REPO_NAME --region $AWS_REGION 2>/dev/null || echo "Repository already exists, continuing..."
echo ""

# Authenticate Docker to ECR
echo "🔐 Authenticating Docker with ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
echo ""

# Tag the image
echo "🏷️  Tagging Docker image..."
docker tag mastra-agent:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:$IMAGE_TAG
echo ""

# Push to ECR
echo "⬆️  Pushing image to ECR..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:$IMAGE_TAG
echo ""

echo "✅ Image pushed successfully!"
echo ""
echo "📍 Image URI:"
echo "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:$IMAGE_TAG"
echo ""
echo "💡 You can now use this URI to deploy your agent to AWS services."
