#!/usr/bin/env python3
"""
Async Monitor Check Functions - High Performance Edition
AsyncIO versions of all monitor check functions for 3000+ concurrent monitors
"""

import asyncio
import aiohttp
import time
import socket
import ssl
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse
import subprocess
import platform

# Import utils for logging
from utils import ol1, olerror, format_response_time


async def ping_icmp_async(monitor_item):
    """
    Async ICMP ping check using subprocess
    
    Args:
        monitor_item: Monitor item with url_check
        
    Returns:
        dict: Check result with success, response_time, message, details
    """
    start_time = time.time()
    
    # Initialize variables for error handling
    url = getattr(monitor_item, 'url_check', '') or ''
    url = url.strip() if url else ''
    hostname = url
    
    try:
        # Extract hostname/IP from URL
        
        # Remove protocol if present
        if '://' in url:
            hostname = urlparse(url).netloc.split(':')[0]
        else:
            hostname = url.split(':')[0]
        
        if not hostname:
            return {
                'success': False,
                'response_time': None,
                'message': 'Invalid hostname for ICMP ping',
                'details': {'hostname': url}
            }
        
        # Determine ping command based on OS
        if platform.system().lower() == 'windows':
            cmd = ['ping', '-n', '1', '-w', '5000', hostname]  # 5 second timeout
        else:
            cmd = ['ping', '-c', '1', '-W', '5', hostname]  # 5 second timeout
        
        # Run ping command asynchronously
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
        except asyncio.TimeoutError:
            process.kill()
            return {
                'success': False,
                'response_time': None,
                'message': f'ICMP ping timeout after 10 seconds to {hostname}',
                'details': {'hostname': hostname, 'timeout': True}
            }
        
        response_time_ms = (time.time() - start_time) * 1000
        stdout_str = stdout.decode('utf-8', errors='ignore')
        stderr_str = stderr.decode('utf-8', errors='ignore')
        
        if process.returncode == 0:
            # Try to extract actual ping time from output
            actual_ping_time = None
            
            if platform.system().lower() == 'windows':
                # Windows: "time=1ms" or "time<1ms"
                time_match = re.search(r'time[<=](\d+)ms', stdout_str)
                if time_match:
                    actual_ping_time = float(time_match.group(1))
            else:
                # Linux/Unix: "time=1.234 ms"
                time_match = re.search(r'time=(\d+\.?\d*)\s*ms', stdout_str)
                if time_match:
                    actual_ping_time = float(time_match.group(1))
            
            return {
                'success': True,
                'response_time': actual_ping_time or response_time_ms,
                'message': f'ICMP ping successful to {hostname}',
                'details': {
                    'hostname': hostname,
                    'ping_time_ms': actual_ping_time,
                    'total_time_ms': response_time_ms,
                    'stdout': stdout_str.strip()
                }
            }
        else:
            return {
                'success': False,
                'response_time': response_time_ms,
                'message': f'ICMP ping failed to {hostname}: {stderr_str or stdout_str}',
                'details': {
                    'hostname': hostname,
                    'return_code': process.returncode,
                    'stdout': stdout_str.strip(),
                    'stderr': stderr_str.strip()
                }
            }
            
    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        return {
            'success': False,
            'response_time': response_time_ms,
            'message': f'ICMP ping error: {str(e)}',
            'details': {'error': str(e), 'hostname': hostname if 'hostname' in locals() else url}
        }


async def ping_web_async(monitor_item, session):
    """
    Async HTTP/HTTPS ping check
    
    Args:
        monitor_item: Monitor item with url_check
        session: aiohttp.ClientSession
        
    Returns:
        dict: Check result with success, response_time, message, details
    """
    start_time = time.time()
    
    try:
        url = monitor_item.url_check.strip()
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Make HTTP request
        async with session.get(url, allow_redirects=True) as response:
            response_time_ms = (time.time() - start_time) * 1000
            
            # Read response body for additional info (max 10 KB)
            max_content_size = 10 * 1024  # 10 KB
            content_bytes = await response.content.read(max_content_size)
            content = content_bytes.decode('utf-8', errors='ignore')
            content_length = len(content_bytes)  # Actual bytes read
            
            # Log first 50 characters of content
            content_preview = content[:50].replace('\n', '\\n').replace('\r', '\\r')
            ol1(f"📄 [WEB] {url} - Content preview (50 chars):\n{content_preview}\n | Size: {content_length} bytes", monitor_item)
            
            if response.status < 400:  # 200-399 are success
                return {
                    'success': True,
                    'response_time': response_time_ms,
                    'message': f'HTTP {response.status} - {response.reason}',
                    'details': {
                        'status_code': response.status,
                        'reason': response.reason,
                        'content_length': content_length,
                        'headers': dict(response.headers),
                        'url': str(response.url)
                    }
                }
            else:
                return {
                    'success': False,
                    'response_time': response_time_ms,
                    'message': f'HTTP {response.status} - {response.reason}',
                    'details': {
                        'status_code': response.status,
                        'reason': response.reason,
                        'content_length': content_length,
                        'url': str(response.url)
                    }
                }
                
    except asyncio.TimeoutError:
        response_time_ms = (time.time() - start_time) * 1000
        return {
            'success': False,
            'response_time': response_time_ms,
            'message': f'HTTP request timeout to {url}',
            'details': {'url': url, 'timeout': True}
        }
    except aiohttp.ClientError as e:
        response_time_ms = (time.time() - start_time) * 1000
        return {
            'success': False,
            'response_time': response_time_ms,
            'message': f'HTTP client error: {str(e)}',
            'details': {'url': url, 'error': str(e)}
        }
    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        return {
            'success': False,
            'response_time': response_time_ms,
            'message': f'HTTP request error: {str(e)}',
            'details': {'url': url, 'error': str(e)}
        }


async def check_tcp_port_async(monitor_item):
    """
    Async TCP port check
    
    Args:
        monitor_item: Monitor item with url_check (format: hostname:port)
        
    Returns:
        dict: Check result with success, response_time, message, details
    """
    start_time = time.time()
    
    try:
        url = monitor_item.url_check.strip()
        
        # Parse hostname and port
        if ':' in url:
            hostname, port_str = url.rsplit(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                return {
                    'success': False,
                    'response_time': None,
                    'message': f'Invalid port number in {url}',
                    'details': {'url': url, 'error': 'Invalid port'}
                }
        else:
            return {
                'success': False,
                'response_time': None,
                'message': f'Port not specified in {url}. Format: hostname:port',
                'details': {'url': url, 'error': 'Missing port'}
            }
        
        # Remove protocol if present
        if '://' in hostname:
            hostname = urlparse(f'http://{hostname}').netloc
        
        # TCP connection test
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(hostname, port),
                timeout=10
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Close connection
            writer.close()
            await writer.wait_closed()
            
            return {
                'success': True,
                'response_time': response_time_ms,
                'message': f'TCP connection successful to {hostname}:{port}',
                'details': {
                    'hostname': hostname,
                    'port': port,
                    'connection_time_ms': response_time_ms
                }
            }
            
        except asyncio.TimeoutError:
            response_time_ms = (time.time() - start_time) * 1000
            return {
                'success': False,
                'response_time': response_time_ms,
                'message': f'TCP connection timeout to {hostname}:{port}',
                'details': {
                    'hostname': hostname,
                    'port': port,
                    'timeout': True
                }
            }
        except ConnectionRefusedError:
            response_time_ms = (time.time() - start_time) * 1000
            return {
                'success': False,
                'response_time': response_time_ms,
                'message': f'TCP connection refused to {hostname}:{port}',
                'details': {
                    'hostname': hostname,
                    'port': port,
                    'connection_refused': True
                }
            }
        except OSError as e:
            response_time_ms = (time.time() - start_time) * 1000
            return {
                'success': False,
                'response_time': response_time_ms,
                'message': f'TCP connection error to {hostname}:{port}: {str(e)}',
                'details': {
                    'hostname': hostname,
                    'port': port,
                    'error': str(e)
                }
            }
            
    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        return {
            'success': False,
            'response_time': response_time_ms,
            'message': f'TCP check error: {str(e)}',
            'details': {'url': url, 'error': str(e)}
        }


async def check_ssl_certificate_async(monitor_item):
    """
    Async SSL certificate check
    
    Args:
        monitor_item: Monitor item with url_check
        
    Returns:
        dict: Check result with success, response_time, message, details
    """
    start_time = time.time()
    
    try:
        url = monitor_item.url_check.strip()
        
        # Parse hostname and port
        if '://' in url:
            parsed = urlparse(url)
            hostname = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        elif ':' in url:
            hostname, port_str = url.rsplit(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 443
        else:
            hostname = url
            port = 443
        
        if not hostname:
            return {
                'success': False,
                'response_time': None,
                'message': 'Invalid hostname for SSL check',
                'details': {'url': url}
            }
        
        # Create SSL context
        context = ssl.create_default_context()
        
        # Connect and get certificate
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(hostname, port, ssl=context, server_hostname=hostname),
                timeout=15
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Get certificate info
            ssl_object = writer.get_extra_info('ssl_object')
            cert = ssl_object.getpeercert()
            
            # Close connection
            writer.close()
            await writer.wait_closed()
            
            if cert:
                # Parse certificate expiry
                not_after = cert.get('notAfter')
                if not_after:
                    expiry_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                    days_until_expiry = (expiry_date - datetime.now()).days
                    
                    if days_until_expiry > 7:  # More than 7 days = OK
                        return {
                            'success': True,
                            'response_time': response_time_ms,
                            'message': f'SSL certificate valid, expires in {days_until_expiry} days',
                            'details': {
                                'hostname': hostname,
                                'port': port,
                                'expiry_date': not_after,
                                'days_until_expiry': days_until_expiry,
                                'subject': cert.get('subject'),
                                'issuer': cert.get('issuer')
                            }
                        }
                    else:
                        return {
                            'success': False,
                            'response_time': response_time_ms,
                            'message': f'SSL certificate expires soon: {days_until_expiry} days',
                            'details': {
                                'hostname': hostname,
                                'port': port,
                                'expiry_date': not_after,
                                'days_until_expiry': days_until_expiry,
                                'warning': 'Certificate expires soon'
                            }
                        }
                else:
                    return {
                        'success': False,
                        'response_time': response_time_ms,
                        'message': 'SSL certificate has no expiry date',
                        'details': {'hostname': hostname, 'port': port}
                    }
            else:
                return {
                    'success': False,
                    'response_time': response_time_ms,
                    'message': 'No SSL certificate found',
                    'details': {'hostname': hostname, 'port': port}
                }
                
        except ssl.SSLError as e:
            response_time_ms = (time.time() - start_time) * 1000
            return {
                'success': False,
                'response_time': response_time_ms,
                'message': f'SSL error: {str(e)}',
                'details': {'hostname': hostname, 'port': port, 'ssl_error': str(e)}
            }
        except asyncio.TimeoutError:
            response_time_ms = (time.time() - start_time) * 1000
            return {
                'success': False,
                'response_time': response_time_ms,
                'message': f'SSL connection timeout to {hostname}:{port}',
                'details': {'hostname': hostname, 'port': port, 'timeout': True}
            }
        except OSError as e:
            response_time_ms = (time.time() - start_time) * 1000
            return {
                'success': False,
                'response_time': response_time_ms,
                'message': f'SSL connection error: {str(e)}',
                'details': {'hostname': hostname, 'port': port, 'error': str(e)}
            }
            
    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        return {
            'success': False,
            'response_time': response_time_ms,
            'message': f'SSL check error: {str(e)}',
            'details': {'url': url, 'error': str(e)}
        }


async def check_web_content_async(monitor_item, session):
    """
    Async web content check - search for specific text in response
    
    Args:
        monitor_item: Monitor item with url_check and result_valid (search text)
        session: aiohttp.ClientSession
        
    Returns:
        dict: Check result with success, response_time, message, details
    """
    start_time = time.time()
    
    # Initialize variables for error handling
    url = getattr(monitor_item, 'url_check', '') or ''
    url = url.strip() if url else ''
    search_text = getattr(monitor_item, 'result_valid', '') or ''
    search_text = search_text.strip() if search_text else ''
    
    try:
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Make HTTP request first (same as original logic)
        async with session.get(url, allow_redirects=True) as response:
            response_time_ms = (time.time() - start_time) * 1000
            
            if response.status >= 400:
                return {
                    'success': False,
                    'response_time': response_time_ms,
                    'message': f'HTTP {response.status} - Cannot check content',
                    'details': {
                        'status_code': response.status,
                        'url': str(response.url),
                        'search_text': search_text
                    }
                }
            
            # Read content (max 10 KB)
            max_content_size = 10 * 1024  # 10 KB
            content_bytes = await response.content.read(max_content_size)
            content = content_bytes.decode('utf-8', errors='ignore')
            
            # Log first 50 characters of content
            content_preview = content[:50].replace('\n', '\\n').replace('\r', '\\r')
            ol1(f"📄 [CONTENT] {url} - Preview (50 chars):\n{content_preview}\n | Size: {len(content_bytes)} bytes | Search: '{search_text}'", monitor_item)
            
            # Check result_error first (if specified)
            result_error = getattr(monitor_item, 'result_error', '') or ''
            result_error = result_error.strip() if result_error else ''
            
            if result_error:
                error_keywords = [keyword.strip() for keyword in result_error.split(',') if keyword.strip()]
                for keyword in error_keywords:
                    if keyword in content:
                        return {
                            'success': False,
                            'response_time': response_time_ms,
                            'message': f'Found error keyword: "{keyword}"',
                            'details': {
                                'status_code': response.status,
                                'content_length': len(content),
                                'error_keyword': keyword,
                                'check_type': 'error_keyword',
                                'url': str(response.url)
                            }
                        }
            
            # Check result_valid (if specified)
            if search_text:
                valid_keywords = [keyword.strip() for keyword in search_text.split(',') if keyword.strip()]
                missing_keywords = []
                
                for keyword in valid_keywords:
                    if keyword not in content:
                        missing_keywords.append(keyword)
                
                if missing_keywords:
                    return {
                        'success': False,
                        'response_time': response_time_ms,
                        'message': f'Missing required keywords: {", ".join(missing_keywords)}',
                        'details': {
                            'status_code': response.status,
                            'content_length': len(content),
                            'missing_keywords': missing_keywords,
                            'check_type': 'missing_required',
                            'url': str(response.url)
                        }
                    }
            
            # All checks passed or no validation required
            success_message = f'Content validation passed (Status: {response.status})'
            if search_text:
                success_message = f'All required keywords found (Status: {response.status})'
            
            return {
                'success': True,
                'response_time': response_time_ms,
                'message': success_message,
                'details': {
                    'status_code': response.status,
                    'content_length': len(content),
                    'check_type': 'content_validation',
                    'url': str(response.url)
                }
            }
                
    except asyncio.TimeoutError:
        response_time_ms = (time.time() - start_time) * 1000
        return {
            'success': False,
            'response_time': response_time_ms,
            'message': f'Content check timeout to {url}',
            'details': {'url': url, 'search_text': search_text, 'timeout': True}
        }
    except aiohttp.ClientError as e:
        response_time_ms = (time.time() - start_time) * 1000
        return {
            'success': False,
            'response_time': response_time_ms,
            'message': f'Content check client error: {str(e)}',
            'details': {'url': url, 'search_text': search_text, 'error': str(e)}
        }
    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        return {
            'success': False,
            'response_time': response_time_ms,
            'message': f'Content check error: {str(e)}',
            'details': {'url': url, 'search_text': search_text, 'error': str(e)}
        }


# Async wrappers for compatibility with existing check types
async def check_ping_web_async(monitor_item, session):
    """Async wrapper for ping_web check"""
    return await ping_web_async(monitor_item, session)


async def check_ping_icmp_async(monitor_item):
    """Async wrapper for ping_icmp check"""
    return await ping_icmp_async(monitor_item)


async def check_ssl_expired_check_async(monitor_item):
    """Async wrapper for SSL expiry check"""
    return await check_ssl_certificate_async(monitor_item)


async def fetch_web_content_async(monitor_item, session):
    """Async wrapper for web content fetching"""
    start_time = time.time()
    
    try:
        url = monitor_item.url_check.strip()
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        async with session.get(url, allow_redirects=True) as response:
            response_time_ms = (time.time() - start_time) * 1000
            # Read content (max 10 KB)
            max_content_size = 10 * 1024  # 10 KB
            content_bytes = await response.content.read(max_content_size)
            content = content_bytes.decode('utf-8', errors='ignore')
            
            # Log first 50 characters of content
            content_preview = content[:50].replace('\n', '\\n').replace('\r', '\\r')
            ol1(f"📄 [FETCH] {url} - Content preview (50 chars):\n{content_preview}\n | Size: {len(content_bytes)} bytes")
            
            return {
                'success': response.status < 400,
                'response_time': response_time_ms,
                'message': f'HTTP {response.status}',
                'details': {
                    'status_code': response.status,
                    'content_length': len(content),
                    'content': content[:1000],  # First 1000 chars
                    'url': str(response.url)
                }
            }
            
    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        return {
            'success': False,
            'response_time': response_time_ms,
            'message': f'Fetch error: {str(e)}',
            'details': {'url': url, 'error': str(e)}
        }


# Helper functions for async implementations
def extract_domain_from_url(url):
    """Extract domain from URL (sync function, used by async functions)"""
    try:
        if not url:
            return None
        
        # Remove protocol
        if '://' in url:
            url = url.split('://', 1)[1]
        
        # Remove path and query
        domain = url.split('/')[0].split('?')[0]
        
        # Remove port
        if ':' in domain:
            domain = domain.split(':')[0]
        
        return domain.lower()
    except:
        return None


async def check_open_port_tcp_then_error_async(monitor_item):
    """
    Async version: Check if TCP port is CLOSED (success when port is closed/error)
    This is opposite logic - success when connection fails
    """
    result = await check_tcp_port_async(monitor_item)
    
    # Reverse the logic - success becomes failure and vice versa
    result['success'] = not result['success']
    
    if result['success']:
        result['message'] = f"Port is closed/filtered (as expected): {result['message']}"
    else:
        result['message'] = f"Port is open (unexpected): {result['message']}"
    
    return result


async def check_open_port_tcp_then_valid_async(monitor_item):
    """
    Async version: Check if TCP port is OPEN (success when port is open)
    This is normal logic - success when connection succeeds
    """
    return await check_tcp_port_async(monitor_item)


# Performance test function for AsyncIO
async def test_async_performance(monitor_items, concurrency_limit=500):
    """
    Test async performance with multiple monitors
    
    Args:
        monitor_items: List of monitor items to test
        concurrency_limit: Maximum concurrent operations
        
    Returns:
        dict: Performance statistics
    """
    start_time = time.time()
    
    # Create HTTP session
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    connector = aiohttp.TCPConnector(limit=concurrency_limit, limit_per_host=50)
    
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrency_limit)
        
        async def check_with_semaphore(monitor_item):
            async with semaphore:
                if monitor_item.type == 'ping_web':
                    return await check_ping_web_async(monitor_item, session)
                elif monitor_item.type == 'ping_icmp':
                    return await check_ping_icmp_async(monitor_item)
                elif monitor_item.type == 'web_content':
                    return await check_web_content_async(monitor_item, session)
                elif monitor_item.type == 'ssl_expired_check':
                    return await check_ssl_expired_check_async(monitor_item)
                else:
                    return {'success': False, 'message': f'Unknown type: {monitor_item.type}'}
        
        # Run all checks concurrently
        tasks = [check_with_semaphore(item) for item in monitor_items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        successful = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
        failed = len(results) - successful
        
        return {
            'total_checks': len(results),
            'successful': successful,
            'failed': failed,
            'success_rate': successful / len(results) * 100 if results else 0,
            'total_time_seconds': total_time,
            'checks_per_second': len(results) / total_time if total_time > 0 else 0,
            'concurrency_limit': concurrency_limit
        }


if __name__ == "__main__":
    # Test async functions
    import sys
    import os
    
    # Add parent directory to path for imports
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    class TestMonitor:
        def __init__(self, url, monitor_type, result_valid=""):
            self.url_check = url
            self.type = monitor_type
            self.result_valid = result_valid
            self.id = 1
            self.name = "Test Monitor"
    
    async def test_all_functions():
        print("🧪 Testing AsyncIO Monitor Check Functions")
        print("=" * 50)
        
        # Test monitors
        test_monitors = [
            TestMonitor("https://google.com", "ping_web"),
            TestMonitor("8.8.8.8", "ping_icmp"),
            TestMonitor("google.com:443", "tcp"),
            TestMonitor("https://google.com", "ssl_expired_check"),
            TestMonitor("https://google.com", "web_content", "Google")
        ]
        
        # Test individual functions
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for monitor in test_monitors:
                print(f"\n🔍 Testing {monitor.type}: {monitor.url_check}")
                
                start = time.time()
                if monitor.type == "ping_web":
                    result = await ping_web_async(monitor, session)
                elif monitor.type == "ping_icmp":
                    result = await ping_icmp_async(monitor)
                elif monitor.type == "tcp":
                    result = await check_tcp_port_async(monitor)
                elif monitor.type == "ssl_expired_check":
                    result = await check_ssl_certificate_async(monitor)
                elif monitor.type == "web_content":
                    result = await check_web_content_async(monitor, session)
                
                duration = time.time() - start
                status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
                
                print(f"  {status} | {duration*1000:.1f}ms | {result['message']}")
        
        print("\n✅ AsyncIO function tests completed")
    
    # Run tests
    asyncio.run(test_all_functions())