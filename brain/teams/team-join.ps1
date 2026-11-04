# Join this team's brain on a Windows PC with Claude Code, from a clone of the team repository (PowerShell, no admin):
#   git clone <team repository url>; powershell -ExecutionPolicy Bypass -File .\brain-<team>\join.ps1
# 1. trusts the VM's certificate (the plugin's lib\paas-ui.crt) for your user (Windows asks once to confirm);
# 2. checks the VM's docs service (TCP port, certificate); 3. adds the team marketplace and installs (or updates) the plugin;
# 4. checks that Claude Code connects docs-http. Safe to run again. Nothing here needs Python.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$failed = $false
function Ok($m) { Write-Host "  ok    $m" }
function Bad($m) { Write-Host "  FAIL  $m" -ForegroundColor Red; $script:failed = $true }

$team = (Get-Content (Join-Path $here 'team.json') -Raw | ConvertFrom-Json).name
if (-not $team) { throw 'join: no team.json here: run this from a clone of the team repository' }
$plug = "paas-brain-$team"
$crt = Join-Path $here "$plug\lib\paas-ui.crt"
$docs = $null
$mcpFile = Join-Path $here "$plug\.mcp.json"
if (Test-Path $mcpFile) {
    $srv = (Get-Content $mcpFile -Raw | ConvertFrom-Json).mcpServers
    if ($srv.PSObject.Properties.Name -contains 'docs-http') { $docs = $srv.'docs-http'.url }
}
Write-Host "team $team"
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) { throw 'join: Claude Code (claude) is not installed or not on PATH' }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'join: git is missing (Claude Code installs the team marketplace with it)' }

# 1. the VM's certificate, in the current user's trusted roots (Claude Code reads the Windows store)
if (-not $docs) {
    Bad 'the plugin has no docs-http: the team was published without the VM''s docs address (re-run the VM''s installer)'
} elseif (-not (Test-Path $crt)) {
    Bad "no certificate in $plug\lib\paas-ui.crt (publish the team on the VM, where the certificate is)"
} else {
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2 $crt
    if (Get-ChildItem Cert:\CurrentUser\Root | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }) {
        Ok "VM certificate already trusted ($($cert.Subject))"
    } else {
        Import-Certificate -FilePath $crt -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
        Ok "VM certificate trusted for your user ($($cert.Subject))"
    }
    # 2. the docs service answers
    $u = [Uri]$docs
    $tcp = Test-NetConnection -ComputerName $u.Host -Port $u.Port -WarningAction SilentlyContinue
    if (-not $tcp.TcpTestSucceeded) {
        Bad "TCP $($u.Port) to $($u.Host) is closed: open it from this PC to the VM (firewall), and check the name resolves"
    } else {
        try {
            $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 -Uri "https://$($u.Host):$($u.Port)/health"
            Ok "docs service answers: https://$($u.Host):$($u.Port) ($($r.StatusCode))"
        } catch {
            Bad "docs service at https://$($u.Host):$($u.Port): $($_.Exception.Message) (a certificate error: the VM name in the url is not in its certificate)"
        }
    }
}

# 3. the plugin (the marketplace is this repository's own remote, or this folder when there is none)
$src = (& git -C $here remote get-url origin 2>$null)
if (-not $src) { $src = $here }
$ErrorActionPreference = 'Continue'
if ((& claude plugin marketplace list 2>&1 | Out-String) -match [regex]::Escape($plug)) {
    & claude plugin marketplace update $plug *> $null
} else {
    & claude plugin marketplace add $src *> $null
    if ($LASTEXITCODE -ne 0) { Bad "claude plugin marketplace add $src failed" }
}
if ((& claude plugin list 2>&1 | Out-String) -match [regex]::Escape("$plug@$plug")) {
    & claude plugin update "$plug@$plug" *> $null
} else {
    & claude plugin install "$plug@$plug" *> $null
    if ($LASTEXITCODE -ne 0) { Bad "claude plugin install $plug@$plug failed" }
}
if ((& claude plugin list 2>&1 | Out-String) -match [regex]::Escape("$plug@$plug")) { Ok "plugin $plug installed" }

# 4. Claude Code connects docs-http
if ($docs) {
    $line = (& claude mcp list 2>&1 | Out-String) -split "`n" | Where-Object { $_ -match [regex]::Escape("${plug}:docs-http") } | Select-Object -First 1
    if ($line -match 'onnected') { Ok 'Claude Code connects docs-http' }
    elseif ($line -match 'SELF_SIGNED|CERT|certificate') { Bad "docs-http: certificate not trusted: $line" }
    else { Bad "docs-http: $(if ($line) { $line } else { 'not listed' })" }
}
if (-not (Get-Command python3 -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host '  note  Python 3 is missing: the brain''s session hooks and docs-local need it (docs-http does not)'
}
if ($failed) { Write-Host 'some checks failed (above)' -ForegroundColor Red; exit 1 }
Write-Host 'done: start claude; the first session sets the team up'
