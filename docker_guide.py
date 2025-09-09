#!/usr/bin/env python3
"""
Docker Development Guide
Hướng dẫn sử dụng Docker cho development vs production
"""

print("""
🐳 DOCKER DEPLOYMENT OPTIONS
============================

📋 OPTION 1: PRODUCTION MODE (Code copied into container)
----------------------------------------------------------
✅ Use Case: Production deployment, stable releases
✅ Code Location: Inside container (copied during build)
✅ Updates: Need rebuild after code changes

Commands:
  python docker_deploy.py build    # Build image with current code
  python docker_deploy.py up       # Start production containers
  python docker_deploy.py down     # Stop containers
  
After code changes:
  python docker_deploy.py down
  python docker_deploy.py build
  python docker_deploy.py up

📋 OPTION 2: DEVELOPMENT MODE (Code mounted from host)
------------------------------------------------------
✅ Use Case: Development, testing, debugging  
✅ Code Location: Host directory (mounted into container)
✅ Updates: Immediate (restart service inside container)

Commands:
  python docker_deploy.py build    # Build base image (once)
  python docker_deploy.py dev      # Start development containers
  python docker_deploy.py down     # Stop containers

After code changes:
  # No rebuild needed! Just restart service:
  docker-compose -f docker-compose.dev.yml restart monitor-service

🔍 CURRENT STATUS CHECK
-----------------------
""")

import subprocess
import os

def check_docker_status():
    try:
        # Check if production containers running
        result = subprocess.run("docker-compose ps", shell=True, capture_output=True, text=True)
        if "monitor-service" in result.stdout and "Up" in result.stdout:
            print("📊 Production Mode: RUNNING")
            print(f"   {result.stdout.strip()}")
        else:
            print("📊 Production Mode: STOPPED")
            
        # Check if development containers running  
        result = subprocess.run("docker-compose -f docker-compose.dev.yml ps", shell=True, capture_output=True, text=True)
        if "monitor-service-dev" in result.stdout and "Up" in result.stdout:
            print("🔧 Development Mode: RUNNING")
            print(f"   {result.stdout.strip()}")
        else:
            print("🔧 Development Mode: STOPPED")
            
    except Exception as e:
        print(f"❌ Error checking status: {e}")

def check_files():
    print("\n📁 DOCKER FILES STATUS")
    print("----------------------")
    files = [
        "Dockerfile",
        "docker-compose.yml", 
        "docker-compose.dev.yml",
        ".env.docker",
        "requirements.txt"
    ]
    
    for file in files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} (missing)")

if __name__ == "__main__":
    check_docker_status()
    check_files()
    
    print("""
💡 RECOMMENDATIONS
------------------
For Development: 
  python docker_deploy.py dev
  # Edit code normally, changes reflect immediately

For Production:
  python docker_deploy.py build
  python docker_deploy.py up
  
🔧 Quick Commands:
  python docker_deploy.py logs     # View logs
  python docker_deploy.py shell    # Access container
  python docker_deploy.py status   # Check health
""")
