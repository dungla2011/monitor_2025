# Database Configuration Guide

## 🗃️ Hỗ trợ Database

Monitor 2025 hỗ trợ cả MySQL và PostgreSQL. Bạn có thể chuyển đổi giữa 2 loại database bằng cách thay đổi biến `DB_TYPE` trong file `.env`.

## ⚙️ Cấu hình

### 1. MySQL (Mặc định)
```env
DB_TYPE=mysql

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=monitor_user
MYSQL_PASSWORD=monitor_pass
MYSQL_NAME=monitor_db
```

### 2. PostgreSQL
```env
DB_TYPE=postgresql

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=monitor_user
POSTGRES_PASSWORD=monitor_pass
POSTGRES_NAME=monitor_db
```

## 🔄 Cách chuyển đổi

### Phương pháp 1: Sử dụng script
```bash
python switch_db.py
```

### Phương pháp 2: Thủ công
Sửa file `.env`:
```env
# Cho MySQL
DB_TYPE=mysql

# Cho PostgreSQL  
DB_TYPE=postgresql
```

## 📦 Dependencies

### Cài đặt drivers:
```bash
# MySQL
pip install PyMySQL

# PostgreSQL
pip install psycopg2-binary

# Hoặc cài tất cả
pip install -r requirements.txt
```

## 🏗️ Database Setup

### MySQL
```sql
CREATE DATABASE monitor_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'monitor_user'@'%' IDENTIFIED BY 'monitor_pass';
GRANT ALL PRIVILEGES ON monitor_db.* TO 'monitor_user'@'%';
FLUSH PRIVILEGES;
```

### PostgreSQL
```sql
CREATE DATABASE monitor_db;
CREATE USER monitor_user WITH PASSWORD 'monitor_pass';
GRANT ALL PRIVILEGES ON DATABASE monitor_db TO monitor_user;
```

## 🧪 Testing

### Kiểm tra kết nối:
```bash
python -c "from db_connection import engine; print('✅ Database connected:', engine.url)"
```

### Chạy test cho database:
```bash
python tests/01.test-models.py
python tests/02.test-create-local-db.py
```

## 📁 File Templates

- `.env` - Cấu hình hiện tại (MySQL mẫu)
- `.env.postgres` - Template cho PostgreSQL
- `.env.backup` - Backup tự động khi switch

## ⚠️ Lưu ý

1. **Migration**: Khi chuyển database, cần migrate data thủ công
2. **Schema**: SQLAlchemy sẽ tự tạo tables tương thích với cả 2 DB
3. **Performance**: PostgreSQL thường nhanh hơn với dataset lớn
4. **Backup**: Luôn backup database trước khi chuyển đổi

## 🔍 Troubleshooting

### MySQL Connection Error:
```bash
# Kiểm tra service
sudo systemctl status mysql

# Test connection
mysql -h localhost -u monitor_user -p monitor_db
```

### PostgreSQL Connection Error:
```bash
# Kiểm tra service
sudo systemctl status postgresql

# Test connection
psql -h localhost -U monitor_user -d monitor_db
```
