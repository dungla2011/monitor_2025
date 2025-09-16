#!/usr/bin/env python3
"""
Performance Comparison: Threading vs AsyncIO
Test script to compare CPU/Memory usage between original threading and new AsyncIO versions
"""

import asyncio
import time
import psutil
import os
import sys
import threading
from datetime import datetime
import subprocess
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class PerformanceMonitor:
    """Monitor CPU, Memory, and other system metrics"""
    
    def __init__(self, test_name):
        self.test_name = test_name
        self.process = psutil.Process()
        self.start_time = None
        self.monitoring = False
        self.metrics = []
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.start_time = time.time()
        self.monitoring = True
        self.metrics = []
        
        def monitor_loop():
            while self.monitoring:
                try:
                    cpu_percent = self.process.cpu_percent()
                    memory_info = self.process.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024
                    
                    # Count threads
                    thread_count = self.process.num_threads()
                    
                    # Get connections (file descriptors)
                    try:
                        connections = len(self.process.connections())
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        connections = 0
                    
                    metric = {
                        'timestamp': time.time() - self.start_time,
                        'cpu_percent': cpu_percent,
                        'memory_mb': memory_mb,
                        'thread_count': thread_count,
                        'connections': connections
                    }
                    
                    self.metrics.append(metric)
                    
                    time.sleep(1)  # Sample every second
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        print(f"📊 Started performance monitoring for {self.test_name}")
    
    def stop_monitoring(self):
        """Stop performance monitoring and return results"""
        self.monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        
        if not self.metrics:
            return None
        
        # Calculate statistics
        total_time = time.time() - self.start_time
        
        cpu_values = [m['cpu_percent'] for m in self.metrics if m['cpu_percent'] > 0]
        memory_values = [m['memory_mb'] for m in self.metrics]
        thread_values = [m['thread_count'] for m in self.metrics]
        connection_values = [m['connections'] for m in self.metrics]
        
        results = {
            'test_name': self.test_name,
            'total_time_seconds': total_time,
            'sample_count': len(self.metrics),
            'cpu_percent': {
                'average': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                'max': max(cpu_values) if cpu_values else 0,
                'min': min(cpu_values) if cpu_values else 0
            },
            'memory_mb': {
                'average': sum(memory_values) / len(memory_values),
                'max': max(memory_values),
                'min': min(memory_values),
                'final': memory_values[-1] if memory_values else 0
            },
            'thread_count': {
                'average': sum(thread_values) / len(thread_values),
                'max': max(thread_values),
                'min': min(thread_values),
                'final': thread_values[-1] if thread_values else 0
            },
            'connections': {
                'average': sum(connection_values) / len(connection_values),
                'max': max(connection_values),
                'final': connection_values[-1] if connection_values else 0
            }
        }
        
        print(f"✅ Performance monitoring completed for {self.test_name}")
        return results


async def test_asyncio_performance(monitor_count=100, test_duration=60):
    """Test AsyncIO version performance"""
    print(f"\n🚀 Testing AsyncIO Performance with {monitor_count} monitors for {test_duration}s")
    
    # Import AsyncIO service
    from monitor_service_asyncio import AsyncMonitorService
    
    # Create mock monitors
    class MockMonitor:
        def __init__(self, i):
            self.id = i
            self.name = f"Test Monitor {i}"
            self.url_check = "https://httpbin.org/delay/1"  # 1 second delay
            self.type = "ping_web"
            self.check_interval_seconds = 5
            self.enable = 1
            self.user_id = 1
    
    mock_monitors = [MockMonitor(i) for i in range(1, monitor_count + 1)]
    
    # Start performance monitoring
    perf_monitor = PerformanceMonitor("AsyncIO")
    perf_monitor.start_monitoring()
    
    try:
        service = AsyncMonitorService(1)
        await service.initialize()
        
        # Override get_enabled_monitors to use mock data
        async def get_mock_monitors():
            return mock_monitors
        service.get_enabled_monitors = get_mock_monitors
        
        # Start monitoring with timeout
        monitoring_task = asyncio.create_task(service.start_monitoring())
        
        try:
            await asyncio.wait_for(monitoring_task, timeout=test_duration)
        except asyncio.TimeoutError:
            print("⏰ AsyncIO test completed (timeout)")
        
        await service.shutdown()
        
    except Exception as e:
        print(f"❌ AsyncIO test error: {e}")
    finally:
        # Stop monitoring and get results
        results = perf_monitor.stop_monitoring()
        return results


def test_threading_performance(monitor_count=100, test_duration=60):
    """Test Threading version performance (simplified simulation)"""
    print(f"\n🧵 Testing Threading Performance with {monitor_count} monitors for {test_duration}s")
    
    # Start performance monitoring
    perf_monitor = PerformanceMonitor("Threading")
    perf_monitor.start_monitoring()
    
    # Simulate threading version behavior
    def monitor_thread_simulation(monitor_id):
        """Simulate a single monitor thread"""
        import requests
        
        while time.time() - start_time < test_duration:
            try:
                # Simulate HTTP check
                response = requests.get("https://httpbin.org/delay/1", timeout=30)
                time.sleep(5)  # Check interval
            except:
                time.sleep(5)
    
    start_time = time.time()
    threads = []
    
    try:
        # Create threads (limited to avoid system limits)
        actual_count = min(monitor_count, 50)  # Limit to avoid "can't start new thread" error
        
        for i in range(actual_count):
            thread = threading.Thread(target=monitor_thread_simulation, args=(i,), daemon=True)
            threads.append(thread)
            thread.start()
            time.sleep(0.1)  # Small delay to avoid overwhelming
        
        # Wait for test duration
        time.sleep(test_duration)
        
        print(f"⏰ Threading test completed with {len(threads)} threads")
        
    except Exception as e:
        print(f"❌ Threading test error: {e}")
    finally:
        # Stop monitoring and get results
        results = perf_monitor.stop_monitoring()
        return results


def compare_results(asyncio_results, threading_results):
    """Compare performance results"""
    print("\n" + "="*80)
    print("📊 PERFORMANCE COMPARISON RESULTS")
    print("="*80)
    
    if not asyncio_results or not threading_results:
        print("❌ Missing test results for comparison")
        return
    
    # Create comparison table
    print(f"{'Metric':<25} {'AsyncIO':<15} {'Threading':<15} {'Improvement':<15}")
    print("-" * 70)
    
    # CPU Usage
    asyncio_cpu = asyncio_results['cpu_percent']['average']
    threading_cpu = threading_results['cpu_percent']['average']
    cpu_improvement = ((threading_cpu - asyncio_cpu) / threading_cpu * 100) if threading_cpu > 0 else 0
    
    print(f"{'CPU Usage (avg %)':<25} {asyncio_cpu:<15.1f} {threading_cpu:<15.1f} {cpu_improvement:<15.1f}%")
    
    # Memory Usage
    asyncio_mem = asyncio_results['memory_mb']['average']
    threading_mem = threading_results['memory_mb']['average']
    mem_improvement = ((threading_mem - asyncio_mem) / threading_mem * 100) if threading_mem > 0 else 0
    
    print(f"{'Memory Usage (avg MB)':<25} {asyncio_mem:<15.1f} {threading_mem:<15.1f} {mem_improvement:<15.1f}%")
    
    # Thread Count
    asyncio_threads = asyncio_results['thread_count']['average']
    threading_threads = threading_results['thread_count']['average']
    thread_improvement = ((threading_threads - asyncio_threads) / threading_threads * 100) if threading_threads > 0 else 0
    
    print(f"{'Thread Count (avg)':<25} {asyncio_threads:<15.1f} {threading_threads:<15.1f} {thread_improvement:<15.1f}%")
    
    # Connections
    asyncio_conn = asyncio_results['connections']['average']
    threading_conn = threading_results['connections']['average']
    
    print(f"{'Connections (avg)':<25} {asyncio_conn:<15.1f} {threading_conn:<15.1f} {'N/A':<15}")
    
    print("-" * 70)
    print(f"{'Test Duration (s)':<25} {asyncio_results['total_time_seconds']:<15.1f} {threading_results['total_time_seconds']:<15.1f} {'N/A':<15}")
    
    # Summary
    print(f"\n🎯 SUMMARY:")
    print(f"   💾 Memory Savings: {mem_improvement:.1f}% ({threading_mem:.0f}MB → {asyncio_mem:.0f}MB)")
    print(f"   🔥 CPU Reduction: {cpu_improvement:.1f}% ({threading_cpu:.1f}% → {asyncio_cpu:.1f}%)")
    print(f"   🧵 Thread Reduction: {thread_improvement:.1f}% ({threading_threads:.0f} → {asyncio_threads:.0f})")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if mem_improvement > 50:
        print("   ✅ AsyncIO provides significant memory savings - recommended for production")
    if cpu_improvement > 30:
        print("   ✅ AsyncIO provides significant CPU savings - better resource utilization")
    if thread_improvement > 80:
        print("   ✅ AsyncIO dramatically reduces thread overhead - better for high concurrency")
    
    # Save results to file
    results_data = {
        'timestamp': datetime.now().isoformat(),
        'asyncio': asyncio_results,
        'threading': threading_results,
        'comparison': {
            'memory_improvement_percent': mem_improvement,
            'cpu_improvement_percent': cpu_improvement,
            'thread_improvement_percent': thread_improvement
        }
    }
    
    with open('performance_comparison_results.json', 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"\n📁 Results saved to: performance_comparison_results.json")


async def main():
    """Main performance comparison"""
    print("🏁 AsyncIO vs Threading Performance Comparison")
    print("=" * 60)
    
    # Test configuration
    monitor_count = 30  # Limited to avoid overwhelming system
    test_duration = 45  # 45 seconds per test
    
    print(f"Configuration:")
    print(f"  Monitors: {monitor_count}")
    print(f"  Duration: {test_duration}s per test")
    print(f"  Total time: ~{test_duration * 2}s")
    
    # Test AsyncIO version
    asyncio_results = await test_asyncio_performance(monitor_count, test_duration)
    
    # Wait a bit between tests
    print("\n⏸️ Waiting 10 seconds between tests...")
    await asyncio.sleep(10)
    
    # Test Threading version
    threading_results = test_threading_performance(monitor_count, test_duration)
    
    # Compare results
    compare_results(asyncio_results, threading_results)
    
    print(f"\n🎉 Performance comparison completed!")
    print(f"Run the actual services to see real-world performance:")
    print(f"  AsyncIO: python monitor_service_asyncio.py start --limit={monitor_count}")
    print(f"  Threading: python monitor_service.py start --limit={monitor_count}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Performance comparison interrupted")
    except Exception as e:
        print(f"\n❌ Performance comparison error: {e}")
        import traceback
        print(traceback.format_exc())