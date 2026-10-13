#!/usr/bin/env python3
"""
GitHub Webhook 部署钩子
"""

from flask import Flask, request, jsonify
import subprocess
import hmac
import hashlib
import json
import os
from datetime import datetime

app = Flask(__name__)

GITHUB_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET', '')
DEPLOY_SCRIPT = '/opt/ResourceHub/deploy.sh'
LOG_FILE = '/var/log/webhook-deploy.log'

def log_event(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] {message}\n"
    print(log_message, end='')
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(log_message)
    except:
        pass

@app.route('/webhook/deploy', methods=['POST'])
def webhook_deploy():
    payload = request.get_data()
    
    # 处理 form-urlencoded 格式
    try:
        if request.content_type == 'application/x-www-form-urlencoded':
            payload_str = payload.decode('utf-8')
            if payload_str.startswith('payload='):
                import urllib.parse
                payload_str = urllib.parse.unquote(payload_str[8:])
                payload = payload_str.encode('utf-8')
        
        data = json.loads(payload.decode('utf-8'))
    except Exception as e:
        log_event(f"❌ 请求解析失败: {str(e)}")
        return jsonify({'error': 'Parse error'}), 400
    
    # 只处理 push 事件
    if request.headers.get('X-GitHub-Event') != 'push':
        return jsonify({'status': 'ignored'}), 200
    
    branch = data.get('ref', '').split('/')[-1]
    
    if branch != 'main':
        log_event(f"⏭️  跳过非 main 分支: {branch}")
        return jsonify({'status': 'ignored'}), 200
    
    commits = data.get('commits', [])
    pusher = data.get('pusher', {}).get('name', 'unknown')
    
    log_event(f"📦 收到 push 事件: {len(commits)} 个提交 by {pusher}")
    
    try:
        log_event("🚀 开始部署...")
        result = subprocess.run(
            ['/bin/bash', DEPLOY_SCRIPT],
            capture_output=True,
            text=True,
            timeout=600,
            cwd='/opt/ResourceHub'
        )
        
        # 记录输出
        if result.stdout:
            log_event(f"输出: {result.stdout[:500]}")
        if result.stderr:
            log_event(f"错误: {result.stderr[:500]}")
        
        if result.returncode == 0:
            log_event("✅ 部署成功")
            return jsonify({'status': 'deployed'}), 200
        else:
            log_event(f"❌ 部署失败 (exit code: {result.returncode})")
            return jsonify({'status': 'failed'}), 500
    
    except subprocess.TimeoutExpired:
        log_event("❌ 部署超时")
        return jsonify({'status': 'timeout'}), 500
    except Exception as e:
        log_event(f"❌ 部署异常: {str(e)}")
        return jsonify({'status': 'error'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    app.run(host='0.0.0.0', port=9000, debug=False)
