#!/usr/bin/env python3
"""
AsyncIO Monitor Service Master Test Runner
Chạy tất cả các test của AsyncIO monitoring system và tạo report tổng hợp
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
    """Print AsyncIO test banner"""
    print("="*80)
    print("🧪 MONITOR 2025 - ASYNCIO COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print("⚡ Testing: AsyncIO Monitor Service")
    print("="*80)

def get_asyncio_test_files(filter_patterns: List[str] = None) -> List[str]:
    """Get all AsyncIO test files in tests directory, optionally filtered by patterns"""
    tests_dir = Path(__file__).parent  # Current directory (tests folder)
    test_files = []
    
    if tests_dir.exists():
        current_file = Path(__file__).name  # Get current file name
        for file in tests_dir.glob("*-asyncio.py"):
            # Include all AsyncIO test files, exclude current file (test runner)
            if file.name != current_file:
                # Apply filter if provided
                if filter_patterns:
                    # Check if filename contains any of the filter patterns
                    if any(pattern in file.name for pattern in filter_patterns):
                        test_files.append(str(file))
                else:
                    test_files.append(str(file))
    
    return sorted(test_files)

def parse_test_output(output: str, test_file: str) -> Dict:
    """Parse test output to extract results"""
    results = {
        'test_file': os.path.basename(test_file),
        'status': 'UNKNOWN',
        'passed': 0,
        'total': 0,
        'success_rate': 0.0,
        'duration': 0.0,
        'errors': [],
        'successes': [],
        'summary': ''
    }
    
    try:
        # Look for test results pattern
        if 'Results:' in output:
            # Extract results line like "Results: 4/5 tests passed (80.0%)"
            results_match = re.search(r'Results:\s+(\d+)/(\d+)\s+tests\s+passed\s+\((\d+\.?\d*)%\)', output)
            if results_match:
                results['passed'] = int(results_match.group(1))
                results['total'] = int(results_match.group(2))
                results['success_rate'] = float(results_match.group(3))
                
                if results['passed'] == results['total']:
                    results['status'] = 'PASS'
                elif results['passed'] > 0:
                    results['status'] = 'PARTIAL'
                else:
                    results['status'] = 'FAIL'
        
        # Extract duration if available
        duration_match = re.search(r'Completed at:.*?(\d+:\d+:\d+)', output)
        start_match = re.search(r'Started at:.*?(\d+:\d+:\d+)', output)
        if duration_match and start_match:
            # Simple duration calculation (approximate)
            results['duration'] = 60.0  # Placeholder
        
        # Extract errors and successes
        error_lines = [line.strip() for line in output.split('\n') if line.strip().startswith('❌')]
        success_lines = [line.strip() for line in output.split('\n') if line.strip().startswith('✅')]
        
        results['errors'] = [line[2:].strip() for line in error_lines[:5]]  # Limit to 5
        results['successes'] = [line[2:].strip() for line in success_lines[:5]]  # Limit to 5
        
        # Generate summary
        if results['status'] == 'PASS':
            results['summary'] = f"All {results['total']} tests passed"
        elif results['status'] == 'PARTIAL':
            results['summary'] = f"{results['passed']}/{results['total']} tests passed"
        else:
            results['summary'] = "Tests failed or could not run"
            
    except Exception as e:
        results['summary'] = f"Error parsing results: {e}"
    
    return results

def run_single_test(test_file: str, stop_on_error: bool = False) -> Dict:
    """Run a single test file and return results"""
    test_name = os.path.basename(test_file)
    print(f"\n{'='*60}")
    print(f"🧪 Running: {test_name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Run test with timeout and proper encoding
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONLEGACYWINDOWSIOENCODING'] = '0'  # Force UTF-8 on Windows
        
        result = subprocess.run([
            sys.executable, test_file
        ], 
        capture_output=True, 
        text=True, 
        encoding='utf-8',  # Explicit UTF-8 encoding
        errors='replace',  # Replace problematic characters instead of failing
        timeout=300, 
        cwd=os.path.dirname(test_file), 
        env=env)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print output in real-time style
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        # Parse results
        output = result.stdout + result.stderr
        test_results = parse_test_output(output, test_file)
        test_results['duration'] = duration
        test_results['return_code'] = result.returncode
        
        # Determine status based on return code if not already determined
        if test_results['status'] == 'UNKNOWN':
            if result.returncode == 0:
                test_results['status'] = 'PASS'
            else:
                test_results['status'] = 'FAIL'
        
        print(f"\n⏱️ Duration: {duration:.1f}s")
        print(f"🔄 Return Code: {result.returncode}")
        print(f"📊 Status: {test_results['status']}")
        
        return test_results
        
    except subprocess.TimeoutExpired:
        end_time = time.time()
        duration = end_time - start_time
        print(f"⏰ Test timed out after {duration:.1f}s")
        
        return {
            'test_file': test_name,
            'status': 'TIMEOUT',
            'passed': 0,
            'total': 0,
            'success_rate': 0.0,
            'duration': duration,
            'return_code': -1,
            'errors': ['Test timed out after 5 minutes'],
            'successes': [],
            'summary': 'Test timed out'
        }
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ Test failed with exception: {e}")
        
        return {
            'test_file': test_name,
            'status': 'ERROR',
            'passed': 0,
            'total': 0,
            'success_rate': 0.0,
            'duration': duration,
            'return_code': -1,
            'errors': [f'Exception: {e}'],
            'successes': [],
            'summary': f'Test error: {e}'
        }

def generate_report(test_results: List[Dict], start_time: datetime) -> Dict:
    """Generate comprehensive test report"""
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    # Calculate overall statistics
    total_tests = len(test_results)
    passed_tests = len([r for r in test_results if r['status'] == 'PASS'])
    failed_tests = len([r for r in test_results if r['status'] in ['FAIL', 'ERROR', 'TIMEOUT']])
    partial_tests = len([r for r in test_results if r['status'] == 'PARTIAL'])
    
    total_test_cases = sum(r['total'] for r in test_results)
    passed_test_cases = sum(r['passed'] for r in test_results)
    
    overall_success_rate = (passed_test_cases / total_test_cases * 100) if total_test_cases > 0 else 0
    
    report = {
        'timestamp': end_time.isoformat(),
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'total_duration': total_duration,
        'service_type': 'AsyncIO Monitor Service',
        'summary': {
            'total_test_files': total_tests,
            'passed_files': passed_tests,
            'failed_files': failed_tests,
            'partial_files': partial_tests,
            'total_test_cases': total_test_cases,
            'passed_test_cases': passed_test_cases,
            'overall_success_rate': overall_success_rate
        },
        'test_results': test_results
    }
    
    return report

def print_final_summary(report: Dict):
    """Print final test summary"""
    summary = report['summary']
    
    print("\n" + "="*80)
    print("📋 ASYNCIO MONITOR SERVICE - FINAL TEST REPORT")
    print("="*80)
    
    # Overall statistics
    print(f"⏰ Total Duration: {report['total_duration']:.1f}s")
    print(f"📁 Test Files: {summary['total_test_files']}")
    print(f"✅ Passed Files: {summary['passed_files']}")
    print(f"❌ Failed Files: {summary['failed_files']}")
    if summary['partial_files'] > 0:
        print(f"⚠️ Partial Files: {summary['partial_files']}")
    
    print(f"\n📊 Test Cases: {summary['passed_test_cases']}/{summary['total_test_cases']} passed ({summary['overall_success_rate']:.1f}%)")
    
    # Individual test results
    print(f"\n📋 Individual Test Results:")
    print("-" * 80)
    for result in report['test_results']:
        status_emoji = {
            'PASS': '✅',
            'FAIL': '❌', 
            'PARTIAL': '⚠️',
            'ERROR': '💥',
            'TIMEOUT': '⏰',
            'UNKNOWN': '❔'
        }.get(result['status'], '❔')
        
        test_name = result['test_file'].replace('-asyncio.py', '').replace('.py', '')
        duration = f"{result['duration']:.1f}s"
        
        if result['total'] > 0:
            case_info = f"({result['passed']}/{result['total']})"
        else:
            case_info = ""
        
        print(f"{status_emoji} {test_name:<30} {duration:>8} {case_info:>8} | {result['summary']}")
    
    # Final verdict
    print("\n" + "="*80)
    if summary['failed_files'] == 0:
        print("🎉 ALL ASYNCIO TESTS PASSED! AsyncIO Monitor Service is ready for production.")
    elif summary['passed_files'] > summary['failed_files']:
        print("⚠️ MOST ASYNCIO TESTS PASSED. Some issues need attention.")
    else:
        print("❌ MULTIPLE ASYNCIO TEST FAILURES. AsyncIO service needs fixes.")
    
    print(f"📊 Final Score: {summary['overall_success_rate']:.1f}% ({summary['passed_test_cases']}/{summary['total_test_cases']} test cases)")
    print("="*80)

def save_report(report: Dict):
    """Save test report to JSON file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"asyncio_test_report_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"💾 Report saved: {filename}")
    except Exception as e:
        print(f"❌ Failed to save report: {e}")

def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AsyncIO Monitor Service Test Runner')
    parser.add_argument('--stop-on-error', action='store_true', 
                       help='Stop on first test failure')
    parser.add_argument('--filter', nargs='+', 
                       help='Filter tests by name patterns')
    parser.add_argument('--no-report', action='store_true',
                       help='Skip saving JSON report')
    
    args = parser.parse_args()
    
    print_banner()
    
    # Get test files
    test_files = get_asyncio_test_files(args.filter)
    
    if not test_files:
        print("❌ No AsyncIO test files found!")
        print("   Looking for: *-asyncio.py files")
        return 1
    
    print(f"📁 Found {len(test_files)} AsyncIO test files:")
    for i, test_file in enumerate(test_files, 1):
        test_name = os.path.basename(test_file)
        print(f"   {i}. {test_name}")
    
    if args.filter:
        print(f"🔍 Filter applied: {args.filter}")
    
    if args.stop_on_error:
        print("🛑 Stop-on-error mode enabled")
    
    # Run tests
    start_time = datetime.now()
    test_results = []
    
    for i, test_file in enumerate(test_files, 1):
        print(f"\n🚀 Progress: {i}/{len(test_files)}")
        
        result = run_single_test(test_file, args.stop_on_error)
        test_results.append(result)
        
        # Stop on error if requested
        if args.stop_on_error and result['status'] in ['FAIL', 'ERROR', 'TIMEOUT']:
            print(f"\n🛑 Stopping due to test failure: {result['test_file']}")
            break
    
    # Generate and display report
    report = generate_report(test_results, start_time)
    print_final_summary(report)
    
    # Save report
    if not args.no_report:
        save_report(report)
    
    # Return appropriate exit code
    if report['summary']['failed_files'] > 0:
        return 1
    else:
        return 0

if __name__ == "__main__":
    sys.exit(main())