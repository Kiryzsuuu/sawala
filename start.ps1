#Requires -Version 5.1
<#
    Meeting Monitor - Skenario B
    One-shot orchestrator: verifies prerequisites, installs Python/Node
    dependencies, starts backend (FastAPI/uvicorn) + frontend (Vite) each in
    their own window, waits until both are actually responding, then opens
    the dashboard in the browser.
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$LogoPath = Join-Path $ProjectRoot "NIT.png"
$BackendUrl = "http://localhost:8000/api/health"
$FrontendUrl = "http://localhost:5173"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host ">> $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "   [OK] $Message" -ForegroundColor Green
}

function Write-Fail {
    param([string]$Message)
    Write-Host "   [GAGAL] $Message" -ForegroundColor Red
}

function Show-LogoSplash {
    param([string]$ImagePath, [int]$DurationSeconds = 3)
    if (-not (Test-Path $ImagePath)) { return }
    try {
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing

        $form = New-Object System.Windows.Forms.Form
        $form.Text = "Meeting Monitor"
        $form.StartPosition = "CenterScreen"
        $form.FormBorderStyle = "FixedDialog"
        $form.ControlBox = $false
        $form.TopMost = $true
        $form.ClientSize = New-Object System.Drawing.Size(340, 380)

        $pic = New-Object System.Windows.Forms.PictureBox
        $pic.SizeMode = "Zoom"
        $pic.Image = [System.Drawing.Image]::FromFile($ImagePath)
        $pic.Dock = "Top"
        $pic.Height = 300
        $form.Controls.Add($pic)

        $label = New-Object System.Windows.Forms.Label
        $label.Text = "Meeting Monitor sedang disiapkan..."
        $label.TextAlign = "MiddleCenter"
        $label.Dock = "Bottom"
        $label.Height = 60
        $label.Font = New-Object System.Drawing.Font("Segoe UI", 11)
        $form.Controls.Add($label)

        $timer = New-Object System.Windows.Forms.Timer
        $timer.Interval = $DurationSeconds * 1000
        $timer.Add_Tick({ $form.Close(); $timer.Stop() })
        $timer.Start()

        $form.Add_Shown({ $form.Activate() })
        [void]$form.ShowDialog()
    } catch {
        Write-Host "   (Splash logo dilewati: $_)" -ForegroundColor DarkYellow
    }
}

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Wait-ForHttp {
    param([string]$Url, [int]$TimeoutSeconds = 60)
    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) { return $true }
        } catch {
            Start-Sleep -Seconds 2
            $elapsed += 2
        }
    }
    return $false
}

Write-Host "=======================================================" -ForegroundColor DarkCyan
Write-Host "   MEETING MONITOR - SKENARIO B (Host Monitoring)" -ForegroundColor DarkCyan
Write-Host "=======================================================" -ForegroundColor DarkCyan

Show-LogoSplash -ImagePath $LogoPath -DurationSeconds 3

Set-Location $ProjectRoot

# ---------------------------------------------------------------------------
# 1. Cek prerequisite
# ---------------------------------------------------------------------------
Write-Step "Memeriksa prasyarat (Python & Node.js)"

if (-not (Test-CommandExists "python")) {
    Write-Fail "Python tidak ditemukan di PATH. Install Python 3.10+ dari https://python.org lalu jalankan ulang script ini."
    exit 1
}
$pythonVersion = (python --version) 2>&1
Write-Ok "Python ditemukan: $pythonVersion"

if (-not (Test-CommandExists "node")) {
    Write-Fail "Node.js tidak ditemukan di PATH. Install Node.js 18+ dari https://nodejs.org lalu jalankan ulang script ini."
    exit 1
}
$nodeVersion = (node --version) 2>&1
Write-Ok "Node.js ditemukan: $nodeVersion"

if (-not (Test-CommandExists "npm")) {
    Write-Fail "npm tidak ditemukan di PATH (biasanya ikut terpasang bersama Node.js)."
    exit 1
}
Write-Ok "npm ditemukan: $(npm --version)"

# ---------------------------------------------------------------------------
# 2. Setup virtual environment Python
# ---------------------------------------------------------------------------
Write-Step "Menyiapkan virtual environment Python (venv)"

$venvPath = Join-Path $ProjectRoot "venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    python -m venv $venvPath
    if (-not (Test-Path $venvPython)) {
        Write-Fail "Gagal membuat virtual environment."
        exit 1
    }
    Write-Ok "Virtual environment dibuat di .\venv"
} else {
    Write-Ok "Virtual environment sudah ada"
}

# ---------------------------------------------------------------------------
# 3. Install dependency Python
# ---------------------------------------------------------------------------
Write-Step "Menginstall dependency Python (requirements.txt)"

& $venvPython -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Gagal upgrade pip."
    exit 1
}

& $venvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt") --timeout 120
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Gagal menginstall dependency Python. Cek koneksi internet lalu coba lagi."
    exit 1
}
Write-Ok "Dependency Python terpasang"

# ---------------------------------------------------------------------------
# 4. Jalankan test backend (verifikasi sebelum start)
# ---------------------------------------------------------------------------
Write-Step "Menjalankan test backend untuk memastikan semua modul berfungsi"

& $venvPython -m pytest tests/ -q
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Ada test yang gagal. Periksa output di atas sebelum melanjutkan."
    exit 1
}
Write-Ok "Semua test backend lulus"

# ---------------------------------------------------------------------------
# 5. Install dependency dashboard (Node)
# ---------------------------------------------------------------------------
Write-Step "Menginstall dependency dashboard (npm install)"

$dashboardPath = Join-Path $ProjectRoot "dashboard"
$nodeModules = Join-Path $dashboardPath "node_modules"

Push-Location $dashboardPath
try {
    if (-not (Test-Path $nodeModules)) {
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Fail "Gagal menginstall dependency dashboard."
            exit 1
        }
        Write-Ok "Dependency dashboard terpasang"
    } else {
        Write-Ok "Dependency dashboard sudah terpasang, dilewati"
    }
} finally {
    Pop-Location
}

# ---------------------------------------------------------------------------
# 6. Jalankan backend di jendela terpisah
# ---------------------------------------------------------------------------
Write-Step "Menjalankan backend (FastAPI + WebSocket) di jendela baru"

$backendCmd = "cd `"$ProjectRoot`"; & `"$venvPython`" -m src.api.main"
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Normal

if (Wait-ForHttp -Url $BackendUrl -TimeoutSeconds 60) {
    Write-Ok "Backend aktif di http://localhost:8000"
} else {
    Write-Fail "Backend tidak merespons dalam 60 detik. Cek jendela backend untuk detail error."
    exit 1
}

# ---------------------------------------------------------------------------
# 7. Jalankan dashboard di jendela terpisah
# ---------------------------------------------------------------------------
Write-Step "Menjalankan dashboard (Vite dev server) di jendela baru"

$frontendCmd = "cd `"$dashboardPath`"; npm run dev"
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Normal

if (Wait-ForHttp -Url $FrontendUrl -TimeoutSeconds 60) {
    Write-Ok "Dashboard aktif di $FrontendUrl"
} else {
    Write-Fail "Dashboard tidak merespons dalam 60 detik. Cek jendela dashboard untuk detail error."
    exit 1
}

# ---------------------------------------------------------------------------
# 8. Buka browser
# ---------------------------------------------------------------------------
Write-Step "Membuka dashboard di browser"
Start-Process $FrontendUrl

Write-Host ""
Write-Host "=======================================================" -ForegroundColor DarkGreen
Write-Host "  SEMUA LAYANAN BERJALAN" -ForegroundColor DarkGreen
Write-Host "  Backend  : http://localhost:8000" -ForegroundColor Green
Write-Host "  Dashboard: $FrontendUrl" -ForegroundColor Green
Write-Host "  Tutup jendela backend/dashboard untuk menghentikan layanan." -ForegroundColor DarkGray
Write-Host "=======================================================" -ForegroundColor DarkGreen
