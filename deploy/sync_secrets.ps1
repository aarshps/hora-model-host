# Hora Model Host - Bitwarden Secrets Sync Wrapper
# This script wraps the deploy/sync_secrets.py execution using the local Python 3.12 installation.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonPath = "C:\Users\Aarsh\AppData\Local\Programs\Python\Python312\python.exe"
$SyncScript = Join-Path $ScriptDir "sync_secrets.py"

if (-not (Test-Path $PythonPath)) {
    # Try finding python on system PATH
    $PythonPath = Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
}

if (-not $PythonPath) {
    Write-Error "Python 3.12 was not found at C:\Users\Aarsh\AppData\Local\Programs\Python\Python312\python.exe or on your system PATH."
    exit 1
}

# Run the python sync script
& $PythonPath $SyncScript
