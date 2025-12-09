# Suitme 部署脚本 (PowerShell)
# 用法: .\deploy.ps1

$SSH_KEY = "C:\Users\科奥\Downloads\suitme.pem"
$SERVER = "root@43.139.129.10"
$PROJECT_PATH = "/opt/suitme/suitme"

Write-Host "========== Suitme 部署脚本 ==========" -ForegroundColor Cyan

# 1. 拉取最新代码
Write-Host "[1/3] 拉取最新代码..." -ForegroundColor Yellow
ssh -i $SSH_KEY $SERVER "cd $PROJECT_PATH && git pull origin main"

# 2. 停止旧服务
Write-Host "[2/3] 重启服务..." -ForegroundColor Yellow
ssh -i $SSH_KEY $SERVER "fuser -k 8000/tcp 2>/dev/null || true"

# 3. 启动新服务
ssh -i $SSH_KEY $SERVER "cd $PROJECT_PATH && nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /var/log/suitme.log 2>&1 &"

# 4. 等待启动并检查
Start-Sleep -Seconds 3
Write-Host "[3/3] 检查服务状态..." -ForegroundColor Yellow
ssh -i $SSH_KEY $SERVER "curl -s http://localhost:8000/health"

Write-Host ""
Write-Host "========== 部署完成! ==========" -ForegroundColor Green
Write-Host "服务地址: http://43.139.129.10:8000"
Write-Host "API文档: http://43.139.129.10:8000/docs"
