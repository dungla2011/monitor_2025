#!/bin/bash
# Script setup.sh: Tự động cài đặt các dịch vụ và phần mềm cần thiết cho server Unbuntu 24:
# wget -qO- https://mytree.vn/setup/01.sh | sudo bash
# DB_USER="myuser" DB_PASS="mypass" wget -qO- https://mytree.vn/setup/01.sh | sudo -E bash
set -e

# Thiết lập biến môi trường để tránh interactive prompts
export DEBIAN_FRONTEND=noninteractive

# Ghi lại thời gian bắt đầu
START_TIME=$(date +%s)

# Nhập thông tin database user (có thể truyền qua biến môi trường)
if [ -n "$DB_USER" ] && [ -n "$DB_PASS" ]; then
    DB_USERNAME="$DB_USER"
    DB_PASSWORD="$DB_PASS"
    echo "=== Sử dụng Database User từ biến môi trường ==="
    echo "Username: $DB_USERNAME"
    echo "Password đã được thiết lập từ biến."
    echo "================================"
else
    # Nhập thông tin database user
    echo "=== Cấu hình Database User ==="

    # Đọc input từ terminal
    read -p "Nhập username cho MySQL/PostgreSQL: " DB_USERNAME </dev/tty
    read -s -p "Nhập password cho MySQL/PostgreSQL: " DB_PASSWORD </dev/tty
    echo ""

    echo "Username: $DB_USERNAME"
    echo "Password đã được lưu."
    echo "================================"
fi

# Tăng ulimit lên 65536
ulimit -n 65536

# Cấu hình ulimit vĩnh viễn
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "root soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "root hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Cập nhật systemd limits
echo "DefaultLimitNOFILE=65536" | sudo tee -a /etc/systemd/system.conf
echo "DefaultLimitNOFILE=65536" | sudo tee -a /etc/systemd/user.conf

# Cấu hình DNS để tránh vấn đề với systemd-resolved
echo "Configuring DNS..."

# Phương án 1: Cấu hình systemd-resolved với DNS tùy chỉnh
if systemctl is-active --quiet systemd-resolved; then
    echo "Configuring systemd-resolved with custom DNS..."
    sudo mkdir -p /etc/systemd/resolved.conf.d
    sudo tee /etc/systemd/resolved.conf.d/dns_servers.conf > /dev/null <<EOF
[Resolve]
DNS=8.8.8.8 8.8.4.4 1.1.1.1 208.67.222.222
FallbackDNS=8.8.8.8 1.1.1.1
Cache=yes
EOF
    sudo systemctl restart systemd-resolved
    echo "systemd-resolved configured with custom DNS."
else
    # Phương án 2: Thay thế bằng resolv.conf truyền thống
    echo "Setting up traditional resolv.conf..."
    
    # Mở khóa file nếu bị chattr
    sudo chattr -i /etc/resolv.conf 2>/dev/null || true
    
    # Dừng systemd-resolved
    sudo systemctl stop systemd-resolved 2>/dev/null || true
    sudo systemctl disable systemd-resolved 2>/dev/null || true
    
    # Xóa symlink resolv.conf và tạo file mới
    sudo rm -f /etc/resolv.conf 2>/dev/null || true
    sudo unlink /etc/resolv.conf 2>/dev/null || true
    
    # Tạo file resolv.conf với DNS servers ổn định
    sudo tee /etc/resolv.conf > /dev/null <<EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
nameserver 1.1.1.1
nameserver 208.67.222.222
EOF
    
    # Khóa file để không bị ghi đè
    sudo chattr +i /etc/resolv.conf 2>/dev/null || true
    echo "Traditional resolv.conf configured."
fi

echo "DNS configuration completed."

# Cập nhật hệ thống
DEBIAN_FRONTEND=noninteractive sudo apt update && DEBIAN_FRONTEND=noninteractive sudo apt upgrade -y

# Cài đặt Samba
sudo apt install -y samba vim net-tools

# Backup file cấu hình Samba hiện tại và tạo file cấu hình mới
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
sudo cp /etc/samba/smb.conf /etc/samba/smb.conf.backup_$TIMESTAMP

# Tạo file cấu hình Samba mới
sudo tee /etc/samba/smb.conf > /dev/null <<EOF
[global]
    encrypt passwords = yes
    idmap uid = 16777216-33554431
    dos filetime resolution = yes
    printing = cups
    dns proxy = no
    log file = /var/log/samba/log.%m
    passdb backend = smbpasswd
    workgroup = MYGROUP
    null passwords = yes
    template shell = /bin/false
    server string = Samba Server
    nt acl support = no
    max log size = 50
    netbios name = Asianux
    socket options = TCP_NODELAY SO_RCVBUF=8192 SO_SNDBUF=8192
    winbind use default domain = no
    idmap gid = 16777216-33554431
    dos filetimes = yes
	oplocks = False
[share]
    comment = 
    writeable = yes
    guest ok = yes
    path = "/"
    ##guest account = root
    valid users = root 
EOF

# Khởi động lại dịch vụ Samba
sudo systemctl enable smbd
sudo systemctl restart smbd

# Cài đặt htop
sudo apt install -y htop vnstat

# Cài đặt nginx
sudo apt install -y nginx

# Cấu hình nginx default site để chạy PHP-FPM 8.4
sudo tee /etc/nginx/sites-available/default > /dev/null <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    root /var/www/html;
    index index.php index.html index.htm index.nginx-debian.html;

    server_name _;

    location / {
        try_files $uri $uri/ =404;
    }

    # PHP-FPM configuration
    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php8.4-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }

    # Deny access to .htaccess files
    location ~ /\.ht {
        deny all;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private no_last_modified no_etag auth;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/javascript;
}
EOF

echo "Nginx default site configured for PHP-FPM 8.4"

# Tạo file test PHP
sudo tee /var/www/html/info.php > /dev/null <<'EOF'
<?php
phpinfo();
?>
EOF

# Tạo file index.php mặc định
sudo tee /var/www/html/index.php > /dev/null <<'EOF'
<?php
echo "<h1>Server Setup Complete!</h1>";
echo "<p>PHP Version: " . PHP_VERSION . "</p>";
echo "<p>Server Time: " . date('Y-m-d H:i:s') . "</p>";
echo "<hr>";
echo "<p><a href='/info.php'>View PHP Info</a></p>";
echo "<p><a href='/phpmyadmin6868/'>phpMyAdmin</a></p>";
?>
EOF

sudo chown -R www-data:www-data /var/www/html/
sudo chmod -R 755 /var/www/html/

echo "PHP test files created"

# Cài đặt PHP 8.4 và PHP-FPM
sudo add-apt-repository ppa:ondrej/php -y
sudo apt update
sudo apt install -y php8.4 php8.4-fpm php8.4-cli php8.4-common php8.4-curl php8.4-zip php8.4-gd php8.4-xml php8.4-mbstring php8.4-bcmath php8.4-intl php8.4-soap php8.4-opcache php8.4-mysql php8.4-pgsql php8.4-sqlite3 php8.4-redis php8.4-memcached

# Cấu hình PHP để cho phép upload file lên 500MB
sudo sed -i 's/upload_max_filesize = .*/upload_max_filesize = 500M/' /etc/php/8.4/fpm/php.ini
sudo sed -i 's/post_max_size = .*/post_max_size = 500M/' /etc/php/8.4/fpm/php.ini
sudo sed -i 's/max_execution_time = .*/max_execution_time = 60/' /etc/php/8.4/fpm/php.ini
sudo sed -i 's/max_input_time = .*/max_input_time = 60/' /etc/php/8.4/fpm/php.ini
sudo sed -i 's/memory_limit = .*/memory_limit = 512M/' /etc/php/8.4/fpm/php.ini

# Cấu hình PHP CLI cũng tương tự
sudo sed -i 's/upload_max_filesize = .*/upload_max_filesize = 500M/' /etc/php/8.4/cli/php.ini
sudo sed -i 's/post_max_size = .*/post_max_size = 500M/' /etc/php/8.4/cli/php.ini
sudo sed -i 's/max_execution_time = .*/max_execution_time = 60/' /etc/php/8.4/cli/php.ini
sudo sed -i 's/memory_limit = .*/memory_limit = 512M/' /etc/php/8.4/cli/php.ini

# Cấu hình Nginx để cho phép upload file lên 500MB
if ! grep -q "client_max_body_size" /etc/nginx/nginx.conf; then
    # Thêm mới nếu chưa có
    sudo sed -i '/http {/a\\tclient_max_body_size 500M;' /etc/nginx/nginx.conf
    echo "Added client_max_body_size to nginx.conf"
else
    # Cập nhật giá trị nếu đã có
    sudo sed -i 's/client_max_body_size.*;/client_max_body_size 500M;/' /etc/nginx/nginx.conf
    echo "Updated existing client_max_body_size in nginx.conf"
fi

# Cài đặt certbot
sudo apt install -y certbot python3-certbot-nginx

# Tải và cài đặt phpMyAdmin
if [ ! -f "/var/www/html/phpmyadmin6868/index.php" ]; then
    echo "Downloading và installing phpMyAdmin..."
    cd /tmp
    
    # Xóa file cũ nếu có
    sudo rm -f phpMyAdmin-latest-all-languages.tar.gz*
    
    sudo wget https://www.phpmyadmin.net/downloads/phpMyAdmin-latest-all-languages.tar.gz
    sudo tar -xzf phpMyAdmin-latest-all-languages.tar.gz
    
    # Tạo target directory
    sudo mkdir -p /var/www/html/phpmyadmin6868
    
    # Move nội dung vào thư mục đích (không tạo subfolder)
    sudo mv phpMyAdmin-*-all-languages/* /var/www/html/phpmyadmin6868/
    sudo mv phpMyAdmin-*-all-languages/.[^.]* /var/www/html/phpmyadmin6868/ 2>/dev/null || true
    
    # Xóa thư mục rỗng
    sudo rmdir phpMyAdmin-*-all-languages 2>/dev/null || true
    
    sudo chown -R www-data:www-data /var/www/html/phpmyadmin6868
    sudo chmod -R 755 /var/www/html/phpmyadmin6868
    echo "phpMyAdmin installed successfully."
else
    echo "phpMyAdmin already installed, skipping download."
fi

# Cấu hình phpMyAdmin (chỉ chạy nếu cần)
if [ -f "/var/www/html/phpmyadmin6868/index.php" ]; then
    # Tạo thư mục tmp cho phpMyAdmin
    sudo mkdir -p /var/www/html/phpmyadmin6868/tmp
    sudo chown -R www-data:www-data /var/www/html/phpmyadmin6868/tmp
    sudo chmod 777 /var/www/html/phpmyadmin6868/tmp

    # Tạo config cho phpMyAdmin nếu chưa có
    if [ ! -f "/var/www/html/phpmyadmin6868/config.inc.php" ]; then
        sudo cp /var/www/html/phpmyadmin6868/config.sample.inc.php /var/www/html/phpmyadmin6868/config.inc.php
        
        # Tạo blowfish secret an toàn
        BLOWFISH_SECRET=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-31)
        sudo sed -i "s/\$cfg\['blowfish_secret'\] = '';/\$cfg['blowfish_secret'] = '$BLOWFISH_SECRET';/" /var/www/html/phpmyadmin6868/config.inc.php
        
        echo "phpMyAdmin config created."
    fi
    
    # Dọn dẹp file tải về
    sudo rm -f /tmp/phpMyAdmin-latest-all-languages.tar.gz*
fi

# Cài đặt OpenVPN, wget, unzip, bpytop
sudo apt install -y openvpn unzip wget bpytop

# Tải và cài đặt VPN config từ GalaxyCloud
echo "Downloading VPN config from GalaxyCloud..."
cd /tmp
sudo wget -O vpn_linux_galaxycloud.zip https://vpn.galaxycloud.vn/download/vpn_linux_galaxycloud.zip
sudo unzip -o vpn_linux_galaxycloud.zip -d /etc/openvpn/
mv /etc/openvpn/vpn_linux_galaxycloud/* /etc/openvpn/

# Vô hiệu hóa OpenVPN service mặc định để tránh xung đột
sudo systemctl disable openvpn
sudo systemctl stop openvpn

# Thêm OpenVPN vào crontab để tự động khởi động khi reboot
CRON_ENTRY="@reboot openvpn --config /etc/openvpn/client/client.conf --float"
(crontab -l 2>/dev/null | grep -v "openvpn --config /etc/openvpn/client/client.conf --float"; echo "$CRON_ENTRY") | crontab -

# Cài đặt pip cho Python
sudo apt install -y python3-pip

# Kiểm tra Python version và cài đặt venv tương ứng
echo "Checking Python version and installing virtual environment..."
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP 'Python \K[0-9]+\.[0-9]+')
echo "Detected Python version: $PYTHON_VERSION"

# Cài đặt python venv cho version hiện tại
if [ -n "$PYTHON_VERSION" ]; then
    VENV_PACKAGE="python${PYTHON_VERSION}-venv"
    echo "Installing $VENV_PACKAGE..."
    
    if sudo apt install -y "$VENV_PACKAGE"; then
        echo "✓ Successfully installed $VENV_PACKAGE"
        
        # Test tạo virtual environment
        echo "Testing virtual environment creation..."
        cd /tmp
        python3 -m venv test_venv
        if [ -d "test_venv" ]; then
            echo "✓ Virtual environment test successful"
            rm -rf test_venv
        else
            echo "⚠ Virtual environment test failed"
        fi
    else
        echo "⚠ Failed to install $VENV_PACKAGE, trying fallback..."
        # Fallback: cài đặt python3-venv generic
        sudo apt install -y python3-venv
        echo "✓ Installed generic python3-venv"
    fi
else
    echo "⚠ Cannot detect Python version, installing generic python3-venv"
    sudo apt install -y python3-venv
fi

echo "Python virtual environment support installed."

# Cài đặt Node.js và npm
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs


sudo apt install locales
sudo locale-gen vi_VN.UTF-8
sudo update-locale



# Cài đặt SSH server nếu chưa có
if dpkg -l | grep -q "openssh-server"; then
    echo "OpenSSH server already installed, skipping installation."
else
    echo "Installing OpenSSH server..."
    DEBIAN_FRONTEND=noninteractive sudo apt install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" openssh-server
    echo "✓ OpenSSH server installed."
fi

# Cấu hình SSH để cho phép root login và password authentication
echo "Configuring SSH server..."
sudo sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
sudo sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
echo "✓ SSH server configured."

# Tải và cấu hình SSH public key cho root
echo "Configuring SSH key authentication..."
sudo mkdir -p /root/.ssh
sudo chmod 700 /root/.ssh

# Tải SSH public key
if wget -q --spider http://mytree.vn/setup/ssh.pub; then
    echo "Downloading SSH public key..."
    sudo wget -O /tmp/ssh.pub http://mytree.vn/setup/ssh.pub
    
    # Kiểm tra file tải về có hợp lệ không
    if [ -s /tmp/ssh.pub ] && grep -q "ssh-" /tmp/ssh.pub; then
        # Thêm key vào authorized_keys (tránh duplicate)
        if [ ! -f /root/.ssh/authorized_keys ] || ! grep -Fxq "$(cat /tmp/ssh.pub)" /root/.ssh/authorized_keys; then
            sudo cat /tmp/ssh.pub >> /root/.ssh/authorized_keys
            echo "SSH public key added to authorized_keys"
        else
            echo "SSH public key already exists in authorized_keys"
        fi
        
        # Set đúng permissions
        sudo chmod 600 /root/.ssh/authorized_keys
        sudo chown root:root /root/.ssh/authorized_keys
        
        # Cleanup
        sudo rm -f /tmp/ssh.pub
        
        echo "SSH key authentication configured successfully!"
    else
        echo "Warning: Downloaded SSH key file is invalid or empty"
        sudo rm -f /tmp/ssh.pub
    fi
else
    echo "Warning: Cannot download SSH public key from http://mytree.vn/setup/ssh.pub"
fi

# Cài đặt PgBouncer
sudo apt install -y pgbouncer pgloader 
sudo systemctl enable pgbouncer

# Cài đặt TigerVNC server
sudo apt install -y tigervnc-standalone-server tigervnc-common

# Cài đặt Docker
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release
# Xóa keyring cũ nếu có để tránh prompt
sudo rm -f /usr/share/keyrings/docker-archive-keyring.gpg
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Cài đặt Docker Compose v2
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Enable và start tất cả các dịch vụ
echo "Enabling và starting các dịch vụ..."
sudo systemctl enable nginx
sudo systemctl start nginx

sudo systemctl enable php8.4-fpm
sudo systemctl restart php8.4-fpm

# Restart Nginx để áp dụng cấu hình mới
sudo systemctl restart nginx

sudo systemctl enable ssh
sudo systemctl restart ssh

sudo systemctl enable docker
sudo systemctl start docker

# Thêm user hiện tại vào group docker
sudo usermod -aG docker $USER

sudo mkdir -p /var/glx/weblog
sudo chown -R www-data:www-data /var/glx/weblog

# Tạo thư mục và cài đặt pgAdmin4 với Docker
echo "Setting up pgAdmin4 with Docker..."
sudo mkdir -p /var/glx/docker/pg_admin
cd /var/glx/docker/pg_admin

# Tạo file docker-compose.yml cho pgAdmin4
sudo tee docker-compose.yml > /dev/null <<EOF
version: '3.8'
services:
  pgadmin:
    image: dpage/pgadmin4
    container_name: pgadmin
    restart: unless-stopped
    network_mode: host
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@lad.vn
      PGADMIN_DEFAULT_PASSWORD: qqqppp@12z
      PGADMIN_LISTEN_PORT: 5080
    volumes:
      - pgadmin_data:/var/lib/pgadmin

volumes:
  pgadmin_data:
EOF



# Khởi động pgAdmin4 container
sudo docker-compose up -d

# Tạo backup directory
sudo mkdir -p /var/glx/docker/pg_admin/pgadmin_backup

# Cài đặt MariaDB
sudo apt install -y mariadb-server mariadb-client
sudo systemctl enable mariadb
sudo systemctl start mariadb

# Tạo user MySQL/MariaDB với full privileges nếu có DB_USERNAME và DB_PASSWORD 
if [ -n "$DB_USERNAME" ] && [ -n "$DB_PASSWORD" ]; then
    echo "Tạo user MySQL/MariaDB: $DB_USERNAME"
    sudo mysql -e "CREATE USER IF NOT EXISTS '$DB_USERNAME'@'localhost' IDENTIFIED BY '$DB_PASSWORD';"
    sudo mysql -e "GRANT ALL PRIVILEGES ON *.* TO '$DB_USERNAME'@'localhost' WITH GRANT OPTION;"
    sudo mysql -e "FLUSH PRIVILEGES;"
fi

# Cài đặt PostgreSQL 
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Tạo user PostgreSQL với superuser privileges nếu có DB_USERNAME và DB_PASSWORD
if [ -n "$DB_USERNAME" ] && [ -n "$DB_PASSWORD" ]; then
    echo "Cấu hình user PostgreSQL: $DB_USERNAME"
    
    # Kiểm tra user đã tồn tại chưa
    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USERNAME'" | grep -q 1; then
        echo "User $DB_USERNAME đã tồn tại, cập nhật password..."
        sudo -u postgres psql -c "ALTER USER $DB_USERNAME WITH PASSWORD '$DB_PASSWORD' SUPERUSER CREATEDB CREATEROLE;"
    else
        echo "Tạo user $DB_USERNAME mới..."
        sudo -u postgres psql -c "CREATE USER $DB_USERNAME WITH PASSWORD '$DB_PASSWORD' SUPERUSER CREATEDB CREATEROLE;"
    fi
    
    # Cấu hình pg_hba.conf để cho phép password authentication
    # Tìm file pg_hba.conf trong thư mục postgresql
    PG_HBA_FILE=$(find /etc/postgresql -name "pg_hba.conf" -type f | head -1)
    
    if [ -n "$PG_HBA_FILE" ] && [ -f "$PG_HBA_FILE" ]; then
        echo "Found pg_hba.conf at: $PG_HBA_FILE"
        
        # Backup file gốc
        sudo cp "$PG_HBA_FILE" "$PG_HBA_FILE.backup_$(date +%Y%m%d_%H%M%S)"
        
        # Thêm rule cho user mới ở đầu file (trước các rule khác)
        sudo sed -i "1i\\# Rule for $DB_USERNAME user" "$PG_HBA_FILE"
        sudo sed -i "2i\\local   all             $DB_USERNAME                                md5" "$PG_HBA_FILE"
        sudo sed -i "3i\\host    all             $DB_USERNAME        127.0.0.1/32            md5" "$PG_HBA_FILE"
        sudo sed -i "4i\\host    all             $DB_USERNAME        ::1/128                 md5" "$PG_HBA_FILE"
        sudo sed -i "5i\\host    all             $DB_USERNAME        0.0.0.0/0               md5" "$PG_HBA_FILE"
        sudo sed -i "6i\\" "$PG_HBA_FILE"
        
        # Cấu hình PostgreSQL để listen trên tất cả interfaces
        PG_CONF_FILE=$(find /etc/postgresql -name "postgresql.conf" -type f | head -1)
        if [ -n "$PG_CONF_FILE" ] && [ -f "$PG_CONF_FILE" ]; then
            echo "Configuring PostgreSQL to listen on all addresses..."
            sudo cp "$PG_CONF_FILE" "$PG_CONF_FILE.backup_$(date +%Y%m%d_%H%M%S)"
            
            # Cấu hình listen_addresses
            if grep -q "^listen_addresses" "$PG_CONF_FILE"; then
                sudo sed -i "s/^listen_addresses.*/listen_addresses = '*'/" "$PG_CONF_FILE"
            else
                sudo sed -i "/^#listen_addresses/a listen_addresses = '*'" "$PG_CONF_FILE"
            fi
            
            # Cấu hình port (đảm bảo port 5432)
            if grep -q "^port" "$PG_CONF_FILE"; then
                sudo sed -i "s/^port.*/port = 5432/" "$PG_CONF_FILE"
            else
                sudo sed -i "/^#port/a port = 5432" "$PG_CONF_FILE"
            fi
            
            echo "PostgreSQL configured to listen on all addresses."
        fi
        
        # Restart PostgreSQL để áp dụng cấu hình
        sudo systemctl restart postgresql
        
        echo "PostgreSQL user $DB_USERNAME đã được tạo và cấu hình!"
        echo "Bạn có thể login bằng: psql -U $DB_USERNAME -h localhost -d postgres"
    else
        echo "Không tìm thấy file pg_hba.conf. PostgreSQL user đã được tạo nhưng chưa cấu hình authentication."
        echo "Bạn cần cấu hình thủ công trong file pg_hba.conf"
    fi
fi

# Cấu hình UFW Firewall
echo "Configuring UFW Firewall..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow specific ports
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw allow 60000/tcp comment 'Custom Port'

# Allow specific IP range
sudo ufw allow from 12.0.0.0/24 comment 'Allow 12.0.0.0/24 network'
sudo ufw allow from 10.0.0.0/24 comment 'Allow 10.0.0.0/24 network'

# Enable UFW
sudo ufw --force enable

# Dọn dẹp các package không cần thiết
sudo apt autoremove -y

sudo locale-gen vi_VN.UTF-8
sudo update-locale

# Thông báo hoàn thành

echo "\n-- Set password --"
echo "\n smbpasswd -a root!"
echo "\n vnspasswd"
echo "\n vi /etc/openvpn/login_file.txt"
echo "\n scp -P 2222 -r root@remote_host:/var/www/html/* /var/www/html/"
echo "\n------------------------------------------"
echo "\nHoàn tất cài đặt các dịch vụ và phần mềm!"
echo "Các dịch vụ đã được enable và start:"
echo "- Samba (smbd)"
echo "- Nginx"
echo "- PHP 8.4 FPM"
echo "- SSH Server"
echo "- Docker"
echo "- MariaDB (User: $DB_USERNAME created)"
echo "- PostgreSQL (User: $DB_USERNAME created)"
echo "- PgBouncer"
echo "- Node.js & npm"
echo "\nFirewall UFW đã được cấu hình:"
echo "- Ports allowed: 22 (SSH), 80 (HTTP), 443 (HTTPS), 60000 (Custom)"
echo "- IP range allowed: 12.0.0.0/24"



# Tính toán và hiển thị thời gian chạy
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo "\n======================================"
echo "HOÀN THÀNH SETUP SERVER!"
echo "Thời gian chạy: ${MINUTES} phút ${SECONDS} giây"
echo "======================================"
echo "\nTruy cập các web interface:"
echo "- phpMyAdmin: http://your-server-ip/phpmyadmin6868"
echo "- pgAdmin4: http://your-server-ip:5080"
echo "  Email: admin@lad.vn"
echo "  Password: qqqppp@12z"
echo "\nDatabase user: $DB_USERNAME"
echo "\nLưu ý: Bạn cần logout và login lại để sử dụng Docker không cần sudo."

# Cấu hình Samba và VNC passwords
echo "\n======================================"
echo "CẤU HÌNH PASSWORDS"
echo "======================================"

echo "\n1. Cấu hình Samba password cho root:"
echo "Nhập password cho Samba user 'root':"
sudo smbpasswd -a root
 
echo "\n2. Cấu hình VNC password:"
echo "Nhập password cho VNC server:"
sudo -u root vncpasswd

echo "\n======================================"
echo "PASSWORDS ĐÃ ĐƯỢC CẤU HÌNH!"
echo "======================================"
