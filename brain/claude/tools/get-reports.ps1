<#
Storage brain: get every report Claude makes on the VM onto this Windows PC, by itself.
Watches the VM's ~/storage-reports/.outbox (report.py adds each new report folder to it), downloads the folder
into Downloads\storage-reports and opens the report (report.html with the charts, or report.xlsx).

One-time setup on the PC (PowerShell; Windows 10/11 have ssh / scp built in):
  1. ssh-keygen -t ed25519                     (ENTER for every question; skip if ~\.ssh\id_ed25519 exists)
  2. type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh <user>@<vm> "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
  3. scp <user>@<vm>:.claude/tools/get-reports.ps1 $env:USERPROFILE\
Then, each day (leave the window open, minimised):
  powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\get-reports.ps1 -Vm <user>@<vm>
Options: -Port 22  -Every 5 (seconds)  -NoOpen (download only)
#>
param(
  [Parameter(Mandatory = $true)][string]$Vm,
  [int]$Port = 22,
  [int]$Every = 5,
  [switch]$NoOpen
)
$dest = Join-Path $env:USERPROFILE "Downloads\storage-reports"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$ssh = @("-p", $Port, "-o", "BatchMode=yes", "-o", "ConnectTimeout=8")
# take the queue atomically (a report queued meanwhile goes to the next round); no double quotes in arguments
# to ssh / scp: Windows PowerShell 5.1 breaks them (report folders have no spaces)
$take = 'f=~/storage-reports/.outbox; [ -s $f ] && mv $f $f.$$ && cat $f.$$ && rm -f $f.$$; true'

ssh @ssh $Vm "true" 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Cannot log in to $Vm without a password: do the one-time setup at the top of this script." -ForegroundColor Red
  exit 1
}
Write-Host "Watching $Vm for new reports -> $dest   (Ctrl+C to stop)" -ForegroundColor Cyan
$first = $true      # reports queued while this window was closed: downloaded, not all opened at once
while ($true) {
  $lines = ssh @ssh $Vm $take 2>$null
  foreach ($line in @($lines)) {
    if (-not $line) { continue }
    $folder, $open = $line -split "`t", 2
    $name = Split-Path $folder -Leaf
    scp -P $Port -o BatchMode=yes -r "${Vm}:$folder" "$dest" 2>$null
    if ($LASTEXITCODE -ne 0) { Write-Host "could not copy $folder" -ForegroundColor Yellow; continue }
    $file = Join-Path (Join-Path $dest $name) $open
    Write-Host ("{0:HH:mm}  {1}" -f (Get-Date), $file) -ForegroundColor Green
    if (-not $NoOpen -and -not $first -and (Test-Path $file)) { Invoke-Item $file }
  }
  $first = $false
  Start-Sleep -Seconds $Every
}
