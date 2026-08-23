@echo off
REM Meeting Monitor - Skenario B
REM Wrapper agar start.ps1 bisa dijalankan cukup dengan double-click,
REM tanpa terganjal PowerShell execution policy pengguna.

setlocal
set SCRIPT_DIR=%~dp0

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%start.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Terjadi kesalahan saat menjalankan Meeting Monitor. Lihat pesan di atas.
    pause
)

endlocal
