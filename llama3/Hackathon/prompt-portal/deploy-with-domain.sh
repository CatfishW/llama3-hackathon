#!/bin/bash

# Quick deployment script with domain configuration for lammp.agaii.org

export DEPLOY_DOMAIN="lammp.agaii.org"
export DEPLOY_NGINX="true"

echo "🚀 Deploying with domain: $DEPLOY_DOMAIN"
echo "📦 Nginx will be configured automatically"
echo ""

# Run the main deployment script
./deploy.sh
