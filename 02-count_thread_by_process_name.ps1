# PowerShell Thread Count Monitor Script
# Đếm số threads theo process name mỗi 2 giây và ghi log với datetime
# Usage: .\02-count_thread_by_process_name.ps1 <process_name>
# Example: .\02-count_thread_by_process_name.ps1 python

param(
    [Parameter(Mandatory=$true)]
    [string]$ProcessName
)

# Tạo tên log file
$LogFile = "thread_count_$ProcessName.log"

# Tạo header cho log file nếu chưa tồn tại
if (-Not (Test-Path $LogFile)) {
    @"
# Thread Count Monitor Log for process: $ProcessName
# Started at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
# Format: DateTime | Thread Count | Process Details
# =================================================
"@ | Out-File -FilePath $LogFile -Encoding UTF8
    Write-Host "✅ Created log file: $LogFile" -ForegroundColor Green
}

Write-Host "🔍 Monitoring threads for process: '$ProcessName'" -ForegroundColor Cyan
Write-Host "📊 Logging to: $LogFile" -ForegroundColor Yellow
Write-Host "⏱️  Interval: 2 seconds" -ForegroundColor Gray
Write-Host "🛑 Press Ctrl+C to stop" -ForegroundColor Red
Write-Host "================================"

# Main monitoring loop
try {
    while ($true) {
        # Lấy current timestamp
        $Timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
        
        # Đếm processes theo tên
        $Processes = Get-Process -Name "*$ProcessName*" -ErrorAction SilentlyContinue
        
        if ($Processes) {
            $ThreadCount = 0
            $ProcessDetails = @()
            
            foreach ($Process in $Processes) {
                $ThreadCount += $Process.Threads.Count
                $ProcessDetails += "$($Process.Id):$($Process.ProcessName)"
            }
            
            $ProcessDetailsString = $ProcessDetails -join " "
            $LogLine = "$Timestamp | Threads: $ThreadCount | PIDs: $ProcessDetailsString"
        } else {
            $LogLine = "$Timestamp | Threads: 0 | No processes found"
        }
        
        # Ghi vào log file và hiển thị trên console
        Write-Host $LogLine -ForegroundColor White
        Add-Content -Path $LogFile -Value $LogLine -Encoding UTF8
        
        # Đợi 2 giây
        Start-Sleep -Seconds 2
    }
}
catch {
    $StopMessage = "`n🛑 Monitoring stopped at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Host $StopMessage -ForegroundColor Red
    Add-Content -Path $LogFile -Value $StopMessage -Encoding UTF8
}
