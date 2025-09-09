# Monitor Service - Docker Deployment

## 🐳 Docker Support

Monitor Service có thể chạy hoàn toàn trong Docker với MySQL container.

## 📋 Prerequisites

- Docker và Docker Compose đã cài đặt
- Port 5005 và 3306 available

## 🚀 Quick Start

### 1. Build và Start Services
```bash
# Build image
python docker_deploy.py build

# Start all services
python docker_deploy.py up
```

### 2. Access Services
- **Web Dashboard**: http://localhost:5005
- **Login**: admin / qqqppp@123
- **MySQL**: localhost:3306

### 3. Check Status
```bash
python docker_deploy.py status
```

## 📁 Docker Files

- `Dockerfile` - Monitor service container
- `docker-compose.yml` - Multi-container setup
- `.env.docker` - Environment variables for Docker
- `docker_deploy.py` - Deployment helper script
- `init.sql` - MySQL initialization

## 🔧 Configuration

### Environment Variables
Copy `.env.docker` to `.env` và customize:

```bash
cp .env.docker .env
# Edit .env with your settings
```

### Custom Configuration
- **Database**: MySQL 8.0 container với persistent storage
- **Volumes**: Logs và data được mount ra host
- **Network**: Isolated bridge network
- **Health Checks**: Automatic service monitoring

## 📊 Management Commands

```bash
# Build
python docker_deploy.py build

# Start services  
python docker_deploy.py up

# Stop services
python docker_deploy.py down

# Restart
python docker_deploy.py restart

# View logs
python docker_deploy.py logs
python docker_deploy.py logs monitor-service
python docker_deploy.py logs mysql

# Check status
python docker_deploy.py status

# Shell access
python docker_deploy.py shell
python docker_deploy.py shell mysql

# Clean up
python docker_deploy.py clean
```

## 🗂️ Data Persistence

- **MySQL Data**: Persistent volume `mysql_data`
- **Logs**: `./logs` directory mounted
- **Application Data**: `./data` directory mounted

## 🔒 Security Features

- Non-root user trong container
- Isolated network
- Health checks
- Environment-based configuration

## 🌐 Production Deployment

### With Reverse Proxy (Nginx/Traefik)
```yaml
# Add to docker-compose.yml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.monitor.rule=Host(`monitor.yourdomain.com`)"
  - "traefik.http.routers.monitor.tls=true"
```

### Environment Variables for Production
```bash
# .env
ADMIN_DOMAIN=monitor.yourdomain.com
WEB_ADMIN_PASSWORD=your_secure_password
DB_PASSWORD=your_secure_db_password
```

## 🆘 Troubleshooting

### Check Logs
```bash
python docker_deploy.py logs monitor-service
```

### Database Issues
```bash
# Connect to MySQL
docker-compose exec mysql mysql -u monitor_user -p monitor_db

# Check tables
python docker_deploy.py shell
python 001_create_db_and_table.py
```

### Port Conflicts
```yaml
# Change ports in docker-compose.yml
ports:
  - "5006:5005"  # Change host port
```

### Reset Everything
```bash
python docker_deploy.py clean
python docker_deploy.py build
python docker_deploy.py up
```

## 📈 Monitoring

- **Health Checks**: Automatic trong Docker
- **Web Dashboard**: Real-time monitoring
- **API Endpoints**: Status và metrics
- **Logs**: Persistent logging

## 🔄 Updates

```bash
# Pull latest code
git pull

# Rebuild and restart
python docker_deploy.py down
python docker_deploy.py build
python docker_deploy.py up
```
