#!/bin/bash

# Suitme 部署脚本
# 用法: ./deploy.sh

set -e

# 配置变量
SSH_KEY="C:\Users\bystanders\Downloads\key.pem"
SERVER="root@43.139.129.10"
PROJECT_PATH="/opt/suitme/suitme"

echo "========== Suitme 部署脚本 =========="

# 1. 拉取最新代码
echo "[1/3] 拉取最新代码..."
ssh -i "$SSH_KEY" $SERVER "cd $PROJECT_PATH && git pull origin main"

# 2. 停止旧服务
echo "[2/3] 重启服务..."
ssh -i "$SSH_KEY" $SERVER "fuser -k 8000/tcp 2>/dev/null || true"

# 3. 启动新服务
ssh -i "$SSH_KEY" $SERVER "cd $PROJECT_PATH && nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /var/log/suitme.log 2>&1 &"

# 4. 等待启动并检查
sleep 3
echo "[3/3] 检查服务状态..."
ssh -i "$SSH_KEY" $SERVER "curl -s http://localhost:8000/health"

echo ""
echo "========== 部署完成! =========="
echo "服务地址: http://43.139.129.10:8000"
echo "API文档: http://43.139.129.10:8000/docs"
