<#
Peleg As A Service on your Windows PC: a desktop and Start-menu icon that opens the web UI on the VM in its own
app window (Chrome or Edge app mode: no tabs, no address bar - like a desktop app). Run once, in PowerShell:

  powershell -ExecutionPolicy Bypass -File Install-PaaS-App.ps1 -Vm <vm-name-or-ip> [-TrustCert] [-SshUser root]

-TrustCert copies the VM's HTTPS certificate over ssh (your existing key) and trusts it for your Windows user, so
the browser shows no warning. Without it, the first start shows a warning: Advanced -> Proceed.
Nothing is installed: two shortcuts and an icon in %LOCALAPPDATA%\PelegAsAService. Re-run to change the VM.
#>
param(
  [Parameter(Mandatory = $true)][string]$Vm,
  [int]$Port = 3001,
  [switch]$TrustCert,
  [string]$SshUser = 'root'
)
$ErrorActionPreference = 'Stop'
$url = "https://${Vm}:$Port"
$dir = Join-Path $env:LOCALAPPDATA 'PelegAsAService'
New-Item -ItemType Directory -Force -Path $dir | Out-Null

# the icon: next to this script (repo checkout / zip), else from the public repo
$ico = Join-Path $dir 'paas.ico'
$local = Join-Path $PSScriptRoot 'paas.ico'
if (Test-Path $local) { Copy-Item $local $ico -Force }
else { Invoke-WebRequest 'https://raw.githubusercontent.com/peleg2312/storage-mcp-servers/main/brain/ui/windows/paas.ico' -OutFile $ico -UseBasicParsing }

# Chrome if installed, else Edge (always on Windows 10/11)
$exe = @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $exe) { throw 'Neither Chrome nor Edge was found' }

$shell = New-Object -ComObject WScript.Shell
$places = @([Environment]::GetFolderPath('Desktop'), (Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs'))
foreach ($folder in $places) {
  $lnk = $shell.CreateShortcut((Join-Path $folder 'Peleg As A Service.lnk'))
  $lnk.TargetPath = $exe
  $lnk.Arguments = "--app=$url --window-size=1400,900"
  $lnk.IconLocation = "$ico,0"
  $lnk.Description = 'Peleg As A Service - Claude on the VM'
  $lnk.Save()
}
Write-Host "Shortcuts created on the Desktop and in the Start menu -> $url (opens in $(Split-Path $exe -Leaf))"

if ($TrustCert) {
  $crt = Join-Path $dir 'paas-ui.crt'
  & scp "${SshUser}@${Vm}:~/.claude/paas-ui-tls/paas-ui.crt" $crt
  if ($LASTEXITCODE -ne 0) { throw "Could not copy the certificate (ssh ${SshUser}@${Vm}); the UI still works, with a warning on first start" }
  Import-Certificate -FilePath $crt -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
  Write-Host 'Certificate trusted for your Windows user: no browser warning. Restart Chrome/Edge if it is open.'
}
Write-Host 'Tip: right-click the desktop icon -> Pin to taskbar.'
