#!/usr/bin/env python3
"""Deploy Mastra agent to AWS Bedrock AgentCore"""

import json
import sys

import boto3

# Configuration
RUNTIME_NAME = "mastra-weather-agent"
ROLE_NAME = "MastraAgentCoreExecutionRole"

envVariables = {"your-env-variables-here": "your-env-variables-here"}

iam_client = boto3.client("iam")
sts_client = boto3.client("sts")
agentcore_client = boto3.client("bedrock-agentcore-control")

# Get AWS account info automatically
account_id = sts_client.get_caller_identity()["Account"]
region = boto3.session.Session().region_name or "us-east-1"

# Build URIs dynamically
IMAGE_URI = f"{account_id}.dkr.ecr.{region}.amazonaws.com/mastra-agent:latest"
ECR_REPOSITORY_ARN = f"arn:aws:ecr:{region}:{account_id}:repository/mastra-agent"

print(f"🔐 Creating IAM role: {ROLE_NAME}")

# Trust policy for AgentCore
trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "bedrock.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }
    ],
}

# Load permissions policy from file
with open("docs/iam_agentcore_execution_role.json", "r") as f:
    permissions_policy = json.load(f)

# Replace template variables
permissions_policy_str = json.dumps(permissions_policy)
permissions_policy_str = permissions_policy_str.replace(
    "${ecr_repository_arn}", ECR_REPOSITORY_ARN
)
permissions_policy_str = permissions_policy_str.replace("${region}", region)
permissions_policy_str = permissions_policy_str.replace("${account_id}", account_id)
permissions_policy = json.loads(permissions_policy_str)

# Create or get role
try:
    role_response = iam_client.create_role(
        RoleName=ROLE_NAME,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Description="Execution role for Mastra AgentCore runtime",
    )
    role_arn = role_response["Role"]["Arn"]
    print(f"   ✅ Created role: {role_arn}")

    # Attach inline policy
    iam_client.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName="AgentCoreExecutionPolicy",
        PolicyDocument=json.dumps(permissions_policy),
    )
    print(f"   ✅ Attached permissions policy")

except iam_client.exceptions.EntityAlreadyExistsException:
    role_arn = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"
    print(f"   ℹ️  Role already exists: {role_arn}")

print(f"\n🚀 Creating AgentCore runtime: {RUNTIME_NAME}")

try:
    response = agentcore_client.create_agent_runtime(
        agentRuntimeName=RUNTIME_NAME,
        agentRuntimeArtifact={"containerConfiguration": {"containerUri": IMAGE_URI}},
        networkConfiguration={"networkMode": "PUBLIC"},
        roleArn=role_arn,
        protocolConfiguration={"serverProtocol": "HTTP"},
        environmentVariables=envVariables,
    )

    print(f"✅ Created AgentCore runtime!")
    print(f"   Runtime ID: {response['agentRuntimeId']}")
    print(f"   Runtime ARN: {response['agentRuntimeArn']}")

except Exception as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)
