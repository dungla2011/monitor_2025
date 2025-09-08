"""
Single Instance Manager và HTTP API cho Monitor Service
"""
import os
import sys
import time
import json
import socket
import psutil
import threading
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for
from pathlib import Path
from dotenv import load_dotenv
import hashlib
import secrets

# Load environment variables
load_dotenv()

# Global variables để track instance
INSTANCE_LOCK_FILE = "monitor_service.lock"

def get_default_port():
    """Get default port from environment (lazy loading)"""
    return int(os.getenv('HTTP_PORT', 5005))

def get_default_host():
    """Get default host from environment (lazy loading)"""
    return os.getenv('HTTP_HOST', '127.0.0.1')

class SingleInstanceManager:
    """Quản lý single instance cho monitor service"""
    
    def __init__(self, lock_file=None, port=None):
        self.lock_file = lock_file or INSTANCE_LOCK_FILE
        self.port = port or get_default_port()  # Lazy load port
        self.pid = None
        
    def is_already_running(self):
        """Kiểm tra xem có instance nào đang chạy không (chỉ dựa trên port)"""
        # Kiểm tra port có đang được sử dụng không
        if self._is_port_in_use(self.port):
            # Thử lấy thông tin từ lock file nếu có
            lock_info = self.get_running_instance_info()
            if lock_info:
                return True, lock_info.get('pid'), lock_info.get('port', self.port)
            else:
                # Port đang được dùng nhưng không có lock file
                return True, None, self.port
        
        # Port không được dùng - cleanup lock file cũ nếu có
        if os.path.exists(self.lock_file):
            self._remove_lock_file()
        
        return False, None, None
    
    def _is_port_in_use(self, port):
        """
        Kiểm tra port có đang được sử dụng không
        Trả về True nếu port đang được sử dụng
        """
        try:
            # Thử connect đến port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((get_default_host(), port))
                if result == 0:
                    return True
                    
            # Nếu connect không được, thử bind để chắc chắn
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.settimeout(1)
                s.bind((get_default_host(), port))
                # Nếu bind được thì port không được sử dụng
                return False
                
        except socket.error:
            # Nếu bind fail thì port đang được sử dụng
            return True
        except Exception as e:
            print(f"⚠️ Error checking port {port}: {e}")
            return False
    
    def get_process_using_port(self, port):
        """
        Tìm process đang sử dụng port (để debug)
        Trả về (pid, name, cmdline) hoặc None
        """
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                    if conn.pid:
                        try:
                            process = psutil.Process(conn.pid)
                            return conn.pid, process.name(), ' '.join(process.cmdline())
                        except psutil.NoSuchProcess:
                            return conn.pid, "Unknown", "Process not found"
            return None
        except Exception as e:
            print(f"⚠️ Error finding process using port {port}: {e}")
            return None
    
    def create_lock_file(self):
        """Tạo lock file cho instance hiện tại"""
        self.pid = os.getpid()
        
        lock_data = {
            'pid': self.pid,
            'port': self.port,
            'started_at': datetime.now().isoformat(),
            'host': get_default_host()
        }
        
        try:
            with open(self.lock_file, 'w') as f:
                json.dump(lock_data, f, indent=2)
            print(f"✅ Created lock file: {self.lock_file} (PID: {self.pid}, Port: {self.port})")
            return True
        except IOError as e:
            print(f"❌ Failed to create lock file: {e}")
            return False
    
    def _remove_lock_file(self):
        """Xóa lock file"""
        try:
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
                print(f"🗑️ Removed lock file: {self.lock_file}")
        except IOError as e:
            print(f"⚠️ Failed to remove lock file: {e}")
    
    def cleanup(self):
        """Cleanup khi thoát"""
        self._remove_lock_file()
    
    def get_running_instance_info(self):
        """Lấy thông tin instance đang chạy"""
        if not os.path.exists(self.lock_file):
            return None
            
        try:
            with open(self.lock_file, 'r') as f:
                return json.load(f)
        except:
            return None

class MonitorAPI:
    """HTTP API cho Monitor Service"""
    
    def __init__(self, host="127.0.0.1", port=5005):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.app.config['JSON_AS_ASCII'] = False  # Để support tiếng Việt
        
        # Setup Flask session for authentication
        self.app.secret_key = secrets.token_urlsafe(32)
        
        # Get authentication credentials from environment
        self.admin_username = os.getenv('WEB_ADMIN_USERNAME', 'admin')
        self.admin_password = os.getenv('WEB_ADMIN_PASSWORD', 'admin123')
        
        # Không import ngay để tránh circular import
        self.running_threads = None
        self.thread_consecutive_errors = None
        self.thread_last_alert_time = None
        self.get_all_monitor_items = None
        self.shutdown_event = None
        
        self.setup_routes()
    
    def requires_auth(self, f):
        """Decorator to require authentication for routes"""
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'authenticated' not in session or not session['authenticated']:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    
    def hash_password(self, password):
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_credentials(self, username, password):
        """Verify login credentials"""
        print(f"🔐 DEBUG AUTH:")

        
        result = (username == self.admin_username and 
                password == self.admin_password)
        print(f"   Final result: {result}")
        return result
    
    def set_monitor_refs(self, running_threads, thread_consecutive_errors, 
                        thread_last_alert_time, get_all_monitor_items, shutdown_event):
        """Set references to monitor_service objects directly"""
        self.running_threads = running_threads
        self.thread_consecutive_errors = thread_consecutive_errors
        self.thread_last_alert_time = thread_last_alert_time
        self.get_all_monitor_items = get_all_monitor_items
        self.shutdown_event = shutdown_event
        
    def _init_monitor_refs(self):
        """Initialize references to monitor_service objects (lazy loading)"""
        # Skip if references already set via set_monitor_refs()
        if self.running_threads is not None:
            return
            
        try:
            # Suppress any signal-related warnings during import
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                from monitor_service import (
                    running_threads, thread_consecutive_errors, 
                    thread_last_alert_time, get_all_monitor_items,
                    shutdown_event
                )
            
            self.running_threads = running_threads
            self.thread_consecutive_errors = thread_consecutive_errors
            self.thread_last_alert_time = thread_last_alert_time
            self.get_all_monitor_items = get_all_monitor_items
            self.shutdown_event = shutdown_event
            
        except Exception as e:
            print(f"⚠️ Could not import monitor_service references: {e}")
            # Fallback values
            self.running_threads = {}
            self.thread_consecutive_errors = {}
            self.thread_last_alert_time = {}
            self.get_all_monitor_items = lambda: []
            self.shutdown_event = None
    
    def setup_routes(self):
        """Setup các routes cho API"""
        
        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            """Login page"""
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')
                
                if self.verify_credentials(username, password):
                    session['authenticated'] = True
                    return redirect(url_for('dashboard'))
                else:
                    return render_template_string(LOGIN_HTML, error="Invalid username or password")
            
            return render_template_string(LOGIN_HTML, error=None)
        
        @self.app.route('/logout')
        def logout():
            """Logout"""
            session.pop('authenticated', None)
            return redirect(url_for('login'))
        
        @self.app.route('/')
        @self.requires_auth
        def dashboard():
            """Web dashboard"""
            return render_template_string(DASHBOARD_HTML)
        
        @self.app.route('/api/status')
        def api_status():
            """API status tổng quan"""
            try:
                # Lazy init monitor references
                self._init_monitor_refs()
                
                monitor_items = self.get_all_monitor_items()
                
                total_items = len(monitor_items) if monitor_items else 0
                enabled_items = len([item for item in monitor_items if item.enable]) if monitor_items else 0
                running_threads_count = len(self.running_threads)
                
                return jsonify({
                    'status': 'running',
                    'timestamp': datetime.now().isoformat(),
                    'monitor_items': {
                        'total': total_items,
                        'enabled': enabled_items,
                        'running_threads': running_threads_count
                    },
                    'threads': list(self.running_threads.keys()),
                    'consecutive_errors': dict(self.thread_consecutive_errors),
                    'last_alert_times': {
                        str(k): datetime.fromtimestamp(v).isoformat() if v else None 
                        for k, v in self.thread_last_alert_time.items()
                    }
                })
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/monitors')
        def api_monitors():
            """API danh sách monitors"""
            try:
                # Lazy init monitor references
                self._init_monitor_refs()
                
                monitor_items = self.get_all_monitor_items()
                
                monitors = []
                for item in monitor_items or []:
                    thread_id = item.id
                    monitors.append({
                        'id': item.id,
                        'name': item.name,
                        'type': item.type,
                        'url_check': item.url_check,
                        'enabled': bool(item.enable),
                        'last_status': item.last_check_status,
                        'last_check_time': item.last_check_time.isoformat() if item.last_check_time else None,
                        'time_range_seconds': item.check_interval_seconds,
                        'user_id': item.user_id,
                        'consecutive_errors': self.thread_consecutive_errors.get(thread_id, 0),
                        'is_thread_running': thread_id in self.running_threads,
                        'stop_to': item.stopTo.isoformat() if item.stopTo else None,
                        'count_online': item.count_online or 0,
                        'count_offline': item.count_offline or 0
                    })
                
                return jsonify({
                    'monitors': monitors,
                    'total': len(monitors),
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/threads')
        def api_threads():
            """API thông tin threads"""
            try:
                # Lazy init monitor references
                self._init_monitor_refs()
                
                threads_info = {}
                for thread_id, thread_obj in self.running_threads.items():
                    threads_info[str(thread_id)] = {
                        'thread_name': thread_obj.name,
                        'is_alive': thread_obj.is_alive(),
                        'consecutive_errors': self.thread_consecutive_errors.get(thread_id, 0),
                        'last_alert_time': datetime.fromtimestamp(
                            self.thread_last_alert_time.get(thread_id, 0)
                        ).isoformat() if self.thread_last_alert_time.get(thread_id) else None
                    }
                
                return jsonify({
                    'threads': threads_info,
                    'total_running': len(self.running_threads),
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/shutdown', methods=['POST'])
        def api_shutdown():
            """API shutdown service"""
            try:
                self.shutdown_event.set()
                
                # Shutdown Flask server
                def shutdown_server():
                    time.sleep(2)  # Delay để response được gửi
                    os._exit(0)
                
                threading.Thread(target=shutdown_server, daemon=True).start()
                
                return jsonify({
                    'status': 'shutting_down',
                    'message': 'Monitor service is shutting down...',
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/logs')
        def api_logs():
            """API lấy logs gần nhất từ logs/log_main.txt"""
            try:
                lines = int(request.args.get('lines', 50))
                log_file = 'logs/log_main.txt'
                
                if not os.path.exists(log_file):
                    return jsonify({
                        'logs': ['📝 Log file not found: logs/log_main.txt'],
                        'total_lines': 0,
                        'timestamp': datetime.now().isoformat()
                    })
                
                with open(log_file, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                return jsonify({
                    'logs': [line.strip() for line in recent_lines],
                    'total_lines': len(all_lines),
                    'showing_lines': len(recent_lines),
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    'error': f'Error reading logs: {str(e)}',
                    'logs': [f'❌ Error: {str(e)}'],
                    'timestamp': datetime.now().isoformat()
                }), 500
    
    def start_server(self):
        """Khởi động HTTP server"""
        try:
            print(f"🌐 Starting HTTP API server on http://{self.host}:{self.port}")
            
            # Sử dụng built-in WSGI server của Python thay vì Flask dev server
            from wsgiref.simple_server import make_server
            import threading
            
            # Create WSGI server
            server = make_server(self.host, self.port, self.app)
            
            print(f"✅ HTTP server started successfully on http://{self.host}:{self.port}")
            
            # Start server in current thread
            server.serve_forever()
            
        except Exception as e:
            print(f"❌ Failed to start HTTP server: {e}")
            import traceback
            traceback.print_exc()

def check_instance_and_get_status():
    """Kiểm tra instance và lấy status qua API"""
    manager = SingleInstanceManager()
    is_running, pid, port = manager.is_already_running()
    
    if is_running:
        print(f"✅ Monitor service is already running (PID: {pid}, Port: {port})")
        
        # Thử lấy status qua API
        try:
            import requests
            response = requests.get(f"http://{get_default_host()}:{port}/api/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Status: {data['status']}")
                print(f"📈 Monitor items: {data['monitor_items']['total']} total, {data['monitor_items']['enabled']} enabled")
                print(f"🧵 Running threads: {data['monitor_items']['running_threads']}")
                return True
            else:
                print(f"⚠️ API response error: {response.status_code}")
        except requests.RequestException as e:
            print(f"⚠️ Cannot connect to API: {e}")
        
        return True
    else:
        print("❌ No monitor service instance is running")
        return False

# HTML Dashboard Template
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Monitor Service Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: #f5f5f5; 
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { 
            background: white; 
            border-radius: 8px; 
            padding: 20px; 
            margin-bottom: 20px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
        }
        .header { text-align: center; color: #333; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
        .status-card { text-align: center; padding: 15px; }
        .status-card h3 { margin: 0 0 10px 0; color: #666; }
        .status-card .number { font-size: 2em; font-weight: bold; color: #2196F3; }
        .monitor-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        .monitor-table th, .monitor-table td { 
            padding: 12px; 
            text-align: left; 
            border-bottom: 1px solid #ddd; 
        }
        .monitor-table th { background: #f8f9fa; font-weight: 600; }
        .status-ok { color: #28a745; font-weight: bold; }
        .status-error { color: #dc3545; font-weight: bold; }
        .status-unknown { color: #6c757d; }
        .enabled { color: #28a745; }
        .disabled { color: #dc3545; }
        .refresh-btn, .shutdown-btn { 
            padding: 10px 20px; 
            margin: 5px; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer; 
            font-weight: bold;
        }
        .refresh-btn { background: #2196F3; color: white; }
        .shutdown-btn { background: #dc3545; color: white; }
        .logout-btn { background: #6c757d; color: white; }
        .logs-container { max-height: 300px; overflow-y: auto; background: #f8f9fa; padding: 15px; border-radius: 4px; }
        .log-line { font-family: monospace; font-size: 12px; margin-bottom: 2px; }
        .loading { text-align: center; color: #666; }
        .header-actions { text-align: right; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header-actions">
            <button class="logout-btn" onclick="window.location.href='/logout'">🚪 Logout</button>
        </div>
        
        <div class="card">
            <div class="header">
                <h1>🖥️ Monitor Service Dashboard</h1>
                <p>Real-time monitoring and management interface</p>
                <button class="refresh-btn" onclick="refreshData()">🔄 Refresh</button>
                <button class="shutdown-btn" onclick="shutdownService()">⚠️ Shutdown Service</button>
            </div>
        </div>

        <div class="card">
            <h2>📊 System Status</h2>
            <div id="status-grid" class="status-grid">
                <div class="loading">Loading...</div>
            </div>
        </div>

        <div class="card">
            <h2>📋 Monitor Items</h2>
            <div id="monitors-table">
                <div class="loading">Loading...</div>
            </div>
        </div>

        <div class="card">
            <h2>📝 Recent Logs</h2>
            <div id="logs-container" class="logs-container">
                <div class="loading">Loading...</div>
            </div>
        </div>
    </div>

    <script>
        async function fetchData(endpoint) {
            const response = await fetch(`/api/${endpoint}`);
            return await response.json();
        }

        async function refreshData() {
            try {
                // Load status
                const status = await fetchData('status');
                document.getElementById('status-grid').innerHTML = `
                    <div class="status-card">
                        <h3>Total Items</h3>
                        <div class="number">${status.monitor_items.total}</div>
                    </div>
                    <div class="status-card">
                        <h3>Enabled Items</h3>
                        <div class="number">${status.monitor_items.enabled}</div>
                    </div>
                    <div class="status-card">
                        <h3>Running Threads</h3>
                        <div class="number">${status.monitor_items.running_threads}</div>
                    </div>
                    <div class="status-card">
                        <h3>Status</h3>
                        <div class="number" style="color: #28a745;">✅ Running</div>
                    </div>
                `;

                // Load monitors
                const monitors = await fetchData('monitors');
                let tableHTML = `
                    <table class="monitor-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Name</th>
                                <th>Type</th>
                                <th>Status</th>
                                <th>Enabled</th>
                                <th>Thread</th>
                                <th>Success</th>
                                <th>Failed</th>
                                <th>Errors</th>
                                <th>Last Check</th>
                            </tr>
                        </thead>
                        <tbody>
                `;

                monitors.monitors.forEach(monitor => {
                    const statusClass = monitor.last_status === 1 ? 'status-ok' : 
                                      monitor.last_status === -1 ? 'status-error' : 'status-unknown';
                    const statusText = monitor.last_status === 1 ? '✅ OK' : 
                                     monitor.last_status === -1 ? '❌ Error' : '⚪ Unknown';
                    
                    const enabledClass = monitor.enabled ? 'enabled' : 'disabled';
                    const enabledText = monitor.enabled ? '✅ Yes' : '❌ No';
                    
                    const threadText = monitor.is_thread_running ? '🟢 Running' : '⚪ Stopped';
                    
                    tableHTML += `
                        <tr>
                            <td>${monitor.id}</td>
                            <td>${monitor.name || 'N/A'}</td>
                            <td>${monitor.type || 'N/A'}</td>
                            <td class="${statusClass}">${statusText}</td>
                            <td class="${enabledClass}">${enabledText}</td>
                            <td>${threadText}</td>
                            <td style="color: #28a745; font-weight: bold;">${monitor.count_online || 0}</td>
                            <td style="color: #dc3545; font-weight: bold;">${monitor.count_offline || 0}</td>
                            <td>${monitor.consecutive_errors}</td>
                            <td>${monitor.last_check_time ? new Date(monitor.last_check_time).toLocaleString() : 'Never'}</td>
                        </tr>
                    `;
                });

                tableHTML += `</tbody></table>`;
                document.getElementById('monitors-table').innerHTML = tableHTML;

                // Load logs
                const logs = await fetchData('logs?lines=20');
                document.getElementById('logs-container').innerHTML = logs.logs.map(log => 
                    `<div class="log-line">${log}</div>`
                ).join('');

                console.log('Data refreshed successfully');
            } catch (error) {
                console.error('Error refreshing data:', error);
            }
        }

        async function shutdownService() {
            if (confirm('Are you sure you want to shutdown the monitor service?')) {
                try {
                    const response = await fetch('/api/shutdown', { method: 'POST' });
                    const data = await response.json();
                    alert(data.message || 'Service is shutting down...');
                } catch (error) {
                    console.error('Error shutting down service:', error);
                }
            }
        }

        // Auto refresh every 30 seconds
        setInterval(refreshData, 30000);
        
        // Initial load
        refreshData();
    </script>
</body>
</html>
'''

# Login HTML Template
LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Monitor Service - Login</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
            text-align: center;
        }
        .login-header {
            color: #333;
            margin-bottom: 30px;
            font-size: 24px;
            font-weight: 300;
        }
        .form-group {
            margin-bottom: 20px;
            text-align: left;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #666;
            font-weight: 500;
        }
        .form-control {
            width: 100%;
            padding: 12px;
            border: 2px solid #e1e5e9;
            border-radius: 6px;
            font-size: 16px;
            transition: border-color 0.3s;
            box-sizing: border-box;
        }
        .form-control:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn-login {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .btn-login:hover {
            transform: translateY(-1px);
        }
        .error {
            color: #e74c3c;
            margin-top: 15px;
            padding: 10px;
            background: #ffeaea;
            border-radius: 4px;
            font-size: 14px;
        }
        .footer {
            margin-top: 30px;
            color: #666;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1 class="login-header">🖥️ Monitor Service</h1>
        <form method="POST" action="/login">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" class="form-control" required>
            </div>
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" class="form-control" required>
            </div>
            <button type="submit" class="btn-login">🔐 Login</button>
        </form>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
        <div class="footer">
            Monitor Service Web Admin
        </div>
    </div>
</body>
</html>
'''
