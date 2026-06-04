@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM DXSpot DXCC Monitor v2 — Windows launcher
REM ============================================================
REM Aquest script comprova les dependències i executa el monitor.
REM
REM Ús:
REM   dxcc_clublog_v2.bat --callsign TEUCALL --telegram-token TOKEN --telegram-chat-id ID [altres arguments]
REM
REM Exemple:
REM   dxcc_clublog_v2.bat --callsign EB3AM --telegram-token 123456:ABC --telegram-chat-id 987654
REM
REM Per instal·lar Python i dependències automàticament, executa:
REM   dxcc_clublog_v2.bat --install
REM ============================================================

set SCRIPT_DIR=%~dp0
set SCRIPT=%SCRIPT_DIR%dxcc_clublog_v2.py

:check_args
if "%1"=="" goto :show_help
if /I "%1"=="--install" goto :install_deps
if /I "%1"=="/?" goto :show_help
goto :check_python

:show_help
echo.
echo DXSpot DXCC Monitor v2 — Windows Launcher
echo ==========================================
echo.
echo Us:
echo   dxcc_clublog_v2.bat --callsign TEUCALL [options...]
echo.
echo Per instal lar dependencies:
echo   dxcc_clublog_v2.bat --install
echo.
echo Arguments complets al README.md
echo.
pause
exit /b 0

:check_python
where python3 >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PYTHON=python3
    goto :run
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PYTHON=python
    goto :run
)

echo ERROR: Python no trobat!
echo.
echo Instal la Python desde https://www.python.org/downloads/
echo (Marca "Add Python to PATH" durant la instal lacio)
echo.
echo Despres executa: dxcc_clublog_v2.bat --install
pause
exit /b 1

:install_deps
echo.
echo ==========================================
echo Instal lant dependencies...
echo ==========================================
echo.

call :check_python
if errorlevel 1 exit /b 1

%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install requests adif_io

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Dependencies instalades correctament!
    echo.
    echo Ara pots executar:
    echo   dxcc_clublog_v2.bat --callsign TEUCALL --telegram-token TOKEN --telegram-chat-id ID
) else (
    echo.
    echo ERROR: No s han pogut instal lar les dependencies.
    echo Prova manualment: pip install requests adif_io
)
pause
exit /b %ERRORLEVEL%

:run
echo.
echo ==========================================
echo DXSpot DXCC Monitor v2
echo ==========================================
echo.

REM Executar el script Python amb tots els arguments passats
%PYTHON% -u "%SCRIPT%" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo El monitor s ha aturat amb el codi d error %ERRORLEVEL%.
    echo Prem qualsevol tecla per tancar...
    pause >nul
)
exit /b %ERRORLEVEL%
