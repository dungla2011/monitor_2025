#!/usr/bin/env python3
"""
Docker Deployment Helper for Monitor Service
"""
import os
import subprocess
import sys

def run_command(cmd, description):
    """Run shell command with description"""
    print(f"\n🔧 {description}")
    print(f"💬 Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ Success!")
        if result.stdout.strip():
            print(f"Output: {result.stdout.strip()}")
    else:
        print(f"❌ Failed!")
        print(f"Error: {result.stderr.strip()}")
        return False
    return True

def main():
    print("="*60)
    print("🐳 MONITOR SERVICE - DOCKER DEPLOYMENT")
    print("="*60)
    
    if len(sys.argv) < 2:
        print("""
Usage:
  python docker_deploy.py build      - Build Docker image
  python docker_deploy.py up         - Start services (production mode)
  python docker_deploy.py dev        - Start services (development mode with code mounting)
  python docker_deploy.py down       - Stop services
  python docker_deploy.py restart    - Restart services
  python docker_deploy.py logs       - View logs
  python docker_deploy.py status     - Check status
  python docker_deploy.py clean      - Clean up containers and images
  python docker_deploy.py shell      - Access container shell

Production Mode:
  - Code is copied into container during build
  - Need to rebuild after code changes
  - Suitable for production deployment

Development Mode:
  - Code is mounted from host directory
  - Changes reflect immediately (no rebuild needed)
  - Suitable for development and testing
        """)
        return

    action = sys.argv[1].lower()
    
    if action == "build":
        print("🏗️ Building Docker image...")
        run_command("docker build -t monitor-service .", "Building monitor-service image")
        
    elif action == "up":
        print("🚀 Starting services (Production Mode)...")
        run_command("docker-compose up -d", "Starting services in background")
        print("\n📊 Services started! Access dashboard at:")
        print("🌐 Web Dashboard: http://localhost:5005")
        print("🐳 MySQL: localhost:3306")
        print("💡 Note: Code is inside container. Rebuild after changes.")
        
    elif action == "dev":
        print("🔧 Starting services (Development Mode)...")
        run_command("docker-compose -f docker-compose.dev.yml up -d", "Starting development services")
        print("\n📊 Development services started! Access dashboard at:")
        print("🌐 Web Dashboard: http://localhost:5005")
        print("🐳 MySQL: localhost:3306") 
        print("🔄 Note: Code is mounted from host. Changes reflect immediately!")
        
    elif action == "down":
        print("⏹️ Stopping services...")
        # Stop both production and development if running
        run_command("docker-compose down", "Stopping production services")
        run_command("docker-compose -f docker-compose.dev.yml down", "Stopping development services")
        
    elif action == "restart":
        print("🔄 Restarting services...")
        run_command("docker-compose down", "Stopping services")
        run_command("docker-compose up -d", "Starting services")
        
    elif action == "logs":
        service = sys.argv[2] if len(sys.argv) > 2 else ""
        if service:
            run_command(f"docker-compose logs -f {service}", f"Viewing logs for {service}")
        else:
            run_command("docker-compose logs -f", "Viewing all service logs")
            
    elif action == "status":
        print("📊 Service status:")
        run_command("docker-compose ps", "Checking service status")
        run_command("docker-compose top", "Checking running processes")
        
    elif action == "clean":
        print("🧹 Cleaning up...")
        run_command("docker-compose down -v", "Stopping and removing volumes")
        run_command("docker system prune -f", "Cleaning up system")
        run_command("docker image rm monitor-service", "Removing monitor-service image")
        
    elif action == "shell":
        service = sys.argv[2] if len(sys.argv) > 2 else "monitor-service"
        print(f"🐚 Opening shell in {service}...")
        subprocess.run(f"docker-compose exec {service} /bin/bash", shell=True)
        
    else:
        print(f"❌ Unknown action: {action}")
        return

if __name__ == "__main__":
    main()
