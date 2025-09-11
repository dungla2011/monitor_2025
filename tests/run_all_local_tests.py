#!/usr/bin/env python3
"""
Monitor Service Master Test Runner
Chạy tất cả các test của monitoring system và tạo report tổng hợp
"""

import os
import sys
import subprocess
import time
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def print_banner():
    """Print test banner"""
    print("="*80)
    print("🧪 MONITOR 2025 - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"� Python: {sys.version.split()[0]}")
    print("="*80)

def get_test_files() -> List[str]:
    """Get all test files in tests directory"""
    tests_dir = Path(__file__).parent  # Current directory (tests folder)
    test_files = []
    
    if tests_dir.exists():
        current_file = Path(__file__).name  # Get current file name
        for file in tests_dir.glob("*.py"):
            # Include all numbered test files, exclude current file (test runner)
            if re.match(r'^\d+\..*\.py$', file.name) and file.name != current_file:
                test_files.append(str(file))
    
    return sorted(test_files)

def parse_test_output(output: str, test_file: str) -> Dict:
    """Parse test output to extract results"""
    result = {
        'file': test_file,
        'name': Path(test_file).stem,
        'status': 'UNKNOWN',
        'successes': 0,
        'errors': 0,
        'duration': 0,
        'start_time': '',
        'end_time': '',
        'summary': '',
        'error_messages': [],
        'exit_code': 0
    }
    
    # Extract success/error counts
    success_match = re.search(r'✅ Successes: (\d+)', output)
    if success_match:
        result['successes'] = int(success_match.group(1))
    
    error_match = re.search(r'❌ Errors: (\d+)', output)
    if error_match:
        result['errors'] = int(error_match.group(1))
    
    # Extract start/end times
    start_match = re.search(r'Test started at: ([^\n]+)', output)
    if start_match:
        result['start_time'] = start_match.group(1).strip()
    
    end_match = re.search(r'Test completed at: ([^\n]+)', output)
    if end_match:
        result['end_time'] = end_match.group(1).strip()
    
    # Calculate duration if possible
    if result['start_time'] and result['end_time']:
        try:
            start_dt = datetime.strptime(result['start_time'], '%Y-%m-%d %H:%M:%S')
            end_dt = datetime.strptime(result['end_time'], '%Y-%m-%d %H:%M:%S')
            result['duration'] = (end_dt - start_dt).total_seconds()
        except:
            pass
    
    # Determine status
    if any(phrase in output for phrase in ['TEST PASSED', 'PASSED!', 'test completed successfully', 'ALL TESTS PASSED!', 'ALL CRITICAL TESTS PASSED!', 'ALL API TESTS PASSED!', 'DYNAMIC CONTROL TEST PASSED!']):
        result['status'] = 'PASSED'
    elif any(phrase in output for phrase in ['TEST FAILED', 'FAILED!', 'test failed']):
        result['status'] = 'FAILED'
    elif result['errors'] > 0:
        result['status'] = 'FAILED'
    elif result['successes'] > 0:
        result['status'] = 'PASSED'
    
    # Extract summary
    summary_patterns = [
        r'TEST SUMMARY.*?\n(.*?)(?=\n\n|\n=|$)',
        r'SUMMARY.*?\n(.*?)(?=\n\n|\n=|$)',
        r'(✅.*?working perfectly!)',
        r'(🎉.*?PASSED!)',
        r'(✅.*?test completed successfully!)',
        r'(All tests completed successfully!)',
        r'(Database setup completed successfully!)'
    ]
    
    for pattern in summary_patterns:
        match = re.search(pattern, output, re.DOTALL | re.IGNORECASE)
        if match:
            result['summary'] = match.group(1).strip()[:200]  # Limit length
            break
    
    # Extract error messages
    error_lines = []
    for line in output.split('\n'):
        if any(keyword in line for keyword in ['❌', 'ERROR:', 'Exception:', 'Traceback', 'Failed:']):
            error_lines.append(line.strip())
            if len(error_lines) >= 3:  # Limit to 3 error lines
                break
    
    result['error_messages'] = error_lines
    
    return result

def run_single_test(test_file: str) -> Dict:
    """Run a single test file and return results"""
    print(f"\n🧪 Running {Path(test_file).name}...")
    print("-" * 60)
    
    start_time = datetime.now()
    
    try:
        # Run the test with timeout
        result = subprocess.run(
            [sys.executable, test_file],
            cwd=Path(__file__).parent.parent,  # Run from project root, not tests folder
            capture_output=False,  # Don't capture output to see real-time results
            text=True,
            timeout=300  # 5 minute timeout per test
        )
        
        output = ""  # Since we're not capturing, output will be empty
        
        # Parse results - determine status from exit code only
        test_result = {
            'file': test_file,
            'name': Path(test_file).stem,
            'status': 'PASSED' if result.returncode == 0 else 'FAILED',
            'successes': 0,
            'errors': 0 if result.returncode == 0 else 1,
            'duration': 0,
            'start_time': '',
            'end_time': '',
            'summary': '',
            'error_messages': [],
            'exit_code': result.returncode,
            'raw_output': ''
        }
        
        # Calculate actual duration
        actual_duration = (datetime.now() - start_time).total_seconds()
        test_result['duration'] = actual_duration
        
        # Print immediate result
        if test_result['status'] == 'PASSED':
            print(f"\n✅ {Path(test_file).name} - PASSED ({test_result['duration']:.1f}s)")
        else:
            print(f"\n❌ {Path(test_file).name} - FAILED ({actual_duration:.1f}s)")
            print(f"   💥 Exit code: {result.returncode}")
        
        return test_result
        
    except subprocess.TimeoutExpired:
        print(f"⏰ {Path(test_file).name} - TIMEOUT (>5 minutes)")
        return {
            'file': test_file,
            'name': Path(test_file).stem,
            'status': 'TIMEOUT',
            'successes': 0,
            'errors': 1,
            'duration': 300,
            'exit_code': -1,
            'error_messages': ['Test timed out after 5 minutes'],
            'summary': 'Test timed out'
        }
        
    except Exception as e:
        print(f"💥 {Path(test_file).name} - ERROR: {str(e)}")
        return {
            'file': test_file,
            'name': Path(test_file).stem,
            'status': 'ERROR',
            'successes': 0,
            'errors': 1,
            'duration': 0,
            'exit_code': -1,
            'error_messages': [str(e)],
            'summary': f'Runtime error: {str(e)}'
        }

def generate_comprehensive_report(results: List[Dict], total_duration: float):
    """Generate comprehensive test report"""
    print("\n" + "="*80)
    print("📊 TEST SUITE SUMMARY REPORT")
    print("="*80)
    
    # Overall statistics
    total_tests = len(results)
    passed_tests = len([r for r in results if r['status'] == 'PASSED'])
    failed_tests = len([r for r in results if r['status'] == 'FAILED'])
    error_tests = len([r for r in results if r['status'] == 'ERROR'])
    timeout_tests = len([r for r in results if r['status'] == 'TIMEOUT'])
    
    total_successes = sum(r.get('successes', 0) for r in results)
    total_errors = sum(r.get('errors', 0) for r in results)
    
    print(f"\n📈 OVERALL STATISTICS:")
    print(f"   📊 Total Tests: {total_tests}")
    print(f"   ✅ Passed: {passed_tests}")
    print(f"   ❌ Failed: {failed_tests}")
    print(f"   💥 Errors: {error_tests}")
    print(f"   ⏰ Timeouts: {timeout_tests}")
    if total_tests > 0:
        print(f"   🎯 Success Rate: {(passed_tests/total_tests*100):.1f}%")
    
    print(f"\n🔢 ASSERTION STATISTICS:")
    print(f"   ✅ Total Successes: {total_successes}")
    print(f"   ❌ Total Errors: {total_errors}")
    print(f"   ⏱️ Total Duration: {total_duration:.1f} seconds")
    if total_tests > 0:
        print(f"   ⚡ Average per Test: {(total_duration/total_tests):.1f} seconds")
    
    # Individual test results
    print(f"\n📋 DETAILED TEST RESULTS:")
    print("-" * 80)
    
    for i, result in enumerate(results, 1):
        status_symbol = {
            'PASSED': '✅',
            'FAILED': '❌',
            'ERROR': '💥',
            'TIMEOUT': '⏰',
            'UNKNOWN': '❓'
        }.get(result['status'], '❓')
        
        print(f"{i:2d}. {status_symbol} {result['name']}")
        print(f"     Status: {result['status']}")
        print(f"     Stats: {result.get('successes', 0)} successes, {result.get('errors', 0)} errors")
        print(f"     Duration: {result.get('duration', 0):.1f}s")
        
        if result.get('summary'):
            print(f"     Summary: {result['summary']}")
        
        if result.get('error_messages') and result['status'] in ['FAILED', 'ERROR']:
            print(f"     Error: {'; '.join(result['error_messages'][:1])}")
        
        print()
    
    # Final verdict
    print("="*80)
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! 🎉")
        print("✅ Monitor 2025 system is working perfectly!")
    else:
        failed_count = failed_tests + error_tests + timeout_tests
        print(f"⚠️  {failed_count} TEST(S) FAILED")
        print("❌ Some issues need to be addressed")
    
    print(f"📅 Report completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

def save_json_report(results: List[Dict], total_duration: float):
    """Save detailed JSON report"""
    report_data = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'total_duration': total_duration,
            'python_version': sys.version.split()[0],
            'platform': sys.platform
        },
        'statistics': {
            'total_tests': len(results),
            'passed_tests': len([r for r in results if r['status'] == 'PASSED']),
            'failed_tests': len([r for r in results if r['status'] == 'FAILED']),
            'error_tests': len([r for r in results if r['status'] == 'ERROR']),
            'timeout_tests': len([r for r in results if r['status'] == 'TIMEOUT']),
            'total_successes': sum(r.get('successes', 0) for r in results),
            'total_errors': sum(r.get('errors', 0) for r in results),
            'success_rate': len([r for r in results if r['status'] == 'PASSED']) / len(results) * 100 if results else 0
        },
        'results': results
    }
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"test_report_{timestamp}.json"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    print(f"📄 Detailed JSON report saved to: {report_file}")

def run_all_numbered_tests(stop_on_error=False):
    """Run all numbered test files and generate comprehensive report"""
    print_banner()
    
    if stop_on_error:
        print("🛑 Stop-on-error mode: Will stop at first failure")
    
    # Get test files
    test_files = get_test_files()
    
    if not test_files:
        print("❌ No numbered test files found in tests directory!")
        return False
    
    print(f"📋 Found {len(test_files)} test files:")
    for test_file in test_files:
        print(f"   • {Path(test_file).name}")
    
    # Run all tests
    results = []
    start_time = datetime.now()
    
    for i, test_file in enumerate(test_files, 1):
        print(f"\n{'='*20} TEST {i}/{len(test_files)} {'='*20}")
        result = run_single_test(test_file)
        results.append(result)
        
        # Check if we should stop on error
        if stop_on_error and result['status'] in ['FAILED', 'ERROR', 'TIMEOUT']:
            print(f"\n🛑 STOPPING: Test {result['name']} failed (stop-on-error mode)")
            print(f"   Status: {result['status']}")
            if result.get('error_messages'):
                print(f"   Error: {result['error_messages'][0]}")
            break
        
        # Brief pause between tests
        if i < len(test_files):
            time.sleep(1)
    
    total_duration = (datetime.now() - start_time).total_seconds()
    
    # Generate reports
    generate_comprehensive_report(results, total_duration)
    save_json_report(results, total_duration)
    
    # Return success status
    passed_count = len([r for r in results if r['status'] == 'PASSED'])
    return passed_count == len(results)

def main():
    """Main test runner"""
    stop_on_error = False
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            print("Monitor Service Master Test Runner")
            print("Usage:")
            print("  python run_all_tests.py                    - Run all numbered tests")
            print("  python run_all_tests.py --stop-on-error   - Stop at first failure")
            print("  python run_all_tests.py --help            - Show this help")
            return
        elif sys.argv[1] == '--stop-on-error':
            stop_on_error = True
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help to see available options")
            return
    
    # Run all numbered tests
    success = run_all_numbered_tests(stop_on_error=stop_on_error)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
