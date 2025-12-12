## OPTIX Trading Platform - Deployment Guide

# Deployment Guide

**Phase 1: Foundation Deployment**  
**Version:** 1.0.0  
**Environment:** AWS EKS

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Database Migration](#database-migration)
4. [Application Deployment](#application-deployment)
5. [Monitoring Setup](#monitoring-setup)
6. [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### Required Tools
- `kubectl` >= 1.28
- `helm` >= 3.12
- `aws-cli` >= 2.13
- `docker` >= 24.0
- `terraform` >= 1.5

### AWS Resources
- EKS Cluster (Kubernetes 1.28+)
- RDS PostgreSQL 15 (Multi-AZ)
- ElastiCache Redis 7.0
- Application Load Balancer
- Route 53 DNS
- ACM Certificate

---

## Infrastructure Setup

### 1. Configure AWS Credentials

```bash
aws configure
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

### 2. Create EKS Cluster

```bash
cd infrastructure/terraform

terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 3. Configure kubectl

```bash
aws eks update-kubeconfig --name optix-production --region us-east-1
kubectl get nodes
```

---

## Database Migration

### 1. Create Database

```bash
# Connect to RDS
psql -h optix-production.xxxxx.us-east-1.rds.amazonaws.com \
     -U postgres -d postgres

CREATE DATABASE optix;
```

### 2. Run Migrations

```bash
# Set database URL
export DATABASE_URL="postgresql://postgres:password@optix-production.xxxxx.us-east-1.rds.amazonaws.com:5432/optix"

# Run Alembic migrations
alembic upgrade head
```

---

## Application Deployment

### 1. Build Docker Image

```bash
cd /path/to/optix-trading-platform

# Build image
docker build -t optix/trading-platform:1.0.0 -f infrastructure/docker/Dockerfile .

# Tag for ECR
docker tag optix/trading-platform:1.0.0 \
  ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/optix/trading-platform:1.0.0

# Push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/optix/trading-platform:1.0.0
```

### 2. Create Kubernetes Secrets

```bash
# Create namespace
kubectl create namespace optix-production

# Create secrets
kubectl create secret generic optix-secrets \
  --namespace=optix-production \
  --from-literal=database-url="postgresql://..." \
  --from-literal=redis-url="redis://..." \
  --from-literal=jwt-secret="$(openssl rand -hex 32)" \
  --from-literal=schwab-client-id="..." \
  --from-literal=schwab-client-secret="..."
```

### 3. Deploy Application

```bash
# Apply deployment
kubectl apply -f infrastructure/kubernetes/deployment.yaml

# Verify deployment
kubectl get pods -n optix-production
kubectl logs -f deployment/optix-api -n optix-production
```

### 4. Configure Ingress

```bash
# Install nginx ingress controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install nginx-ingress ingress-nginx/ingress-nginx

# Apply ingress rules
kubectl apply -f infrastructure/kubernetes/ingress.yaml
```

---

## Monitoring Setup

### 1. Install Datadog Agent

```bash
# Add Datadog Helm repo
helm repo add datadog https://helm.datadoghq.com
helm repo update

# Install Datadog
helm install datadog-agent datadog/datadog \
  --set datadog.apiKey=$DD_API_KEY \
  --set datadog.site=datadoghq.com \
  --namespace=optix-production
```

### 2. Configure Alerts

```bash
# PagerDuty integration
kubectl create secret generic pagerduty-config \
  --namespace=optix-production \
  --from-literal=integration-key="..."
```

---

## Performance Verification

### Load Testing

```bash
# Install k6
brew install k6

# Run load test
k6 run tests/load/api_load_test.js

# Verify NFRs:
# - p95 response time < 200ms (reads)
# - p95 response time < 500ms (writes)
# - Support 100K concurrent users
```

### API Health Checks

```bash
# Health check
curl https://api.optix.com/health

# Verify services
curl https://api.optix.com/ | jq
```

---

## Rollback Procedures

### Rollback Deployment

```bash
# List revisions
kubectl rollout history deployment/optix-api -n optix-production

# Rollback to previous version
kubectl rollout undo deployment/optix-api -n optix-production

# Rollback to specific revision
kubectl rollout undo deployment/optix-api -n optix-production --to-revision=2
```

### Database Rollback

```bash
# Rollback migration
alembic downgrade -1
```

---

## Post-Deployment Checklist

- [ ] All pods running and healthy
- [ ] Database migrations completed
- [ ] Redis connection verified
- [ ] Load balancer health checks passing
- [ ] Monitoring dashboards displaying data
- [ ] Alerts configured and tested
- [ ] SSL certificate valid
- [ ] Performance NFRs verified
- [ ] Rollback procedure tested
- [ ] Documentation updated

---

## Troubleshooting

### Pod Not Starting

```bash
kubectl describe pod <pod-name> -n optix-production
kubectl logs <pod-name> -n optix-production
```

### Database Connection Issues

```bash
# Test connection from pod
kubectl run -it --rm debug --image=postgres:15 --restart=Never -- \
  psql -h optix-production.xxxxx.us-east-1.rds.amazonaws.com -U postgres
```

### High Latency

```bash
# Check metrics
kubectl top pods -n optix-production
kubectl top nodes

# Check HPA status
kubectl get hpa -n optix-production
```

---

## Support Contacts

- **DevOps Team:** devops@optix.com
- **On-Call Engineer:** PagerDuty escalation
- **AWS Support:** Enterprise Support Plan

---

**Last Updated:** December 2024  
**Document Owner:** DevOps Team
