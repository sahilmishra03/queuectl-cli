# ==============================================================================
# QueueCTL - All Features Demonstration & Testing Script
# ==============================================================================
# Run this script in PowerShell inside the activated virtual environment:
#   .\.venv\Scripts\activate
#   .\demo_features.ps1
# ==============================================================================

Write-Host "`n=== 1. VERIFYING CLI HELP SYSTEM ===" -ForegroundColor Cyan
queuectl --help

Write-Host "`n=== 2. CONFIGURATION MANAGEMENT ===" -ForegroundColor Cyan
Write-Host "Setting max-retries to 3..."
queuectl config set max-retries 3
queuectl config set backoff-base 2
queuectl config list

Write-Host "`n=== 3. ENQUEUEING JOBS (All Features & Bonus Options) ===" -ForegroundColor Cyan

# A. Enqueue using JSON format (Required Category Example)
Write-Host "-> Enqueueing via JSON payload..."
queuectl enqueue '{"id":"json-job-1","command":"echo Hello from JSON Payload!"}'

# B. Enqueue basic job
Write-Host "-> Enqueueing standard job..."
queuectl enqueue "echo Standard Job Executed Successfully" --id "standard-job-1"

# C. Enqueue Priority Jobs (Bonus Feature)
Write-Host "-> Enqueueing Priority Jobs (Priority 10 should run before Priority 0)..."
queuectl enqueue "echo Low Priority Task" --priority 0 --id "priority-low"
queuectl enqueue "echo High Priority Task" --priority 10 --id "priority-high"

# D. Enqueue Timeout Job (Bonus Feature - will time out after 2 seconds)
Write-Host "-> Enqueueing Timeout Job (ping 10 seconds, timeout at 2 seconds)..."
queuectl enqueue "ping localhost -n 10" --timeout 2 --id "timeout-job-1"

# E. Enqueue Failing Job (Will fail and move to DLQ after retries)
Write-Host "-> Enqueueing Failing Job to demonstrate DLQ..."
queuectl enqueue "python -c `"import sys; print('Failing now'); sys.exit(1)`"" --id "failing-job-1"

# F. Enqueue Scheduled/Delayed Job (Bonus Feature)
$futureTime = (Get-Date).AddMinutes(5).ToString("yyyy-MM-ddTHH:mm:ss")
Write-Host "-> Enqueueing Scheduled Job (Scheduled for $futureTime)..."
queuectl enqueue "echo Scheduled Task Executed" --run-at $futureTime --id "scheduled-job-1"

Write-Host "`n=== 4. CHECKING INITIAL STATUS & PENDING LIST ===" -ForegroundColor Cyan
queuectl status
Write-Host "`nList of Pending Jobs:"
queuectl list --state pending

Write-Host "`n=== 5. STARTING WORKERS TO PROCESS JOBS ===" -ForegroundColor Cyan
Write-Host "To process the queue, start workers in a separate terminal OR run one cycle."
Write-Host "Starting 2 parallel workers for 6 seconds..."
# We start the worker process in background and stop it cleanly after 6 seconds for demonstration
$workerJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    .\.venv\Scripts\queuectl worker start --count 2
}

Start-Sleep -Seconds 6
Write-Host "Stopping workers gracefully..."
queuectl worker stop
Receive-Job $workerJob -AutoRemoveJob | Out-Null

Write-Host "`n=== 6. VERIFYING RESULTS & OUTPUT LOGS (Bonus Feature) ===" -ForegroundColor Cyan
queuectl status

Write-Host "`nCompleted Jobs:"
queuectl list --state completed

Write-Host "`n-> Output Logs for JSON Job ('json-job-1'):"
queuectl logs json-job-1

Write-Host "`n-> Output Logs for High Priority Job ('priority-high'):"
queuectl logs priority-high

Write-Host "`n-> Output Logs for Timeout Job ('timeout-job-1'):"
queuectl list --state timed_out
queuectl logs timeout-job-1

Write-Host "`n=== 7. DEAD LETTER QUEUE (DLQ) & RETRY ===" -ForegroundColor Cyan
Write-Host "Checking jobs that failed after retries in DLQ:"
queuectl dlq list

Write-Host "`nRetrying the dead/failing job from DLQ back to PENDING:"
queuectl dlq retry failing-job-1
queuectl list --state pending

Write-Host "`n=== 8. LIVE MONITORING & DASHBOARD ===" -ForegroundColor Cyan
Write-Host "To launch the Terminal UI (TUI) Monitor, run:"
Write-Host "  queuectl monitor --refresh-interval 1.0" -ForegroundColor Yellow
Write-Host "`nTo launch the Web Dashboard, run:"
Write-Host "  queuectl dashboard start --port 8000" -ForegroundColor Yellow
Write-Host "`n=== DEMONSTRATION COMPLETE ===" -ForegroundColor Green
