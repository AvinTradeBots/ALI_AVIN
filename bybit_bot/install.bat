@echo off
chcp 65001 >nul
title Bybit Trading Bot - Smart Installer
color 0A

cls
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║         Bybit Trading Bot - Smart Installer v2.0           ║
echo ╚═════════════════════════════���══════════════════════════════╝
echo.
echo در حال بررسی سیستم...
echo.

REM ════════════════════════════════════════════════════════════════
REM مرحله 1: چک کردن Python
REM ════════════════════════════════════════════════════════════════
echo [1/7] بررسی نصب Python...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ╔════════════════════════════════════════════════════════════╗
    echo ║                   ❌ خطا: Python یافت نشد!                 ║
    echo ╚════════════════════════════════════════════════════════════╝
    echo.
    echo Python نصب نیست یا به PATH اضافه نشده.
    echo.
    echo 📥 لطفاً Python نصب کنید:
    echo.
    echo   🔗 Python 3.10.11 (توصیه شده):
    echo   https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe
    echo.
    echo   یا
    echo.
    echo   🔗 Python 3.9.13:
    echo   https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe
    echo.
    echo ⚠️  هنگام نصب حتماً تیک بزنید:
    echo    ☑ Add Python to PATH
    echo.
    echo بعد از نصب، کامپیوتر را Restart کنید و دوباره این فایل را اجرا کنید.
    echo.
    pause
    exit /b 1
)

REM دریافت نسخه Python
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo    ✅ Python %PYVER% یافت شد

REM ════════════════════════════════════════════════════════════════
REM مرحله 2: چک کردن نسخه Python
REM ════════════════════════════════════════════════════════════════
echo.
echo [2/7] بررسی سازگاری نسخه Python...

REM چک کردن Python 3.13+
echo %PYVER% | findstr /R "3\.1[3-9]\. 3\.[2-9][0-9]\." >nul
if %errorlevel% equ 0 (
    color 0E
    echo    ⚠️  هشدار: Python %PYVER% خیلی جدید است!
    echo.
    echo    این نسخه با NumPy سازگار نیست و نیاز به Visual Studio دارد.
    echo.
    echo    💡 توصیه: Python 3.10.11 یا 3.9.13 نصب کنید
    echo.
    echo    ❓ میخواهید ادامه دهید؟ (ممکن است خطا بدهد^)
    echo.
    set /p CONTINUE="بله (y) / خیر (n): "
    if /i not "%CONTINUE%"=="y" (
        echo.
        echo نصب لغو شد.
        echo.
        echo لطفاً Python 3.10 نصب کنید و دوباره تلاش کنید.
        pause
        exit /b 1
    )
    color 0A
)

REM چک کردن Python 3.8 یا پایین‌تر
echo %PYVER% | findstr /R "3\.[0-7]\. 2\." >nul
if %errorlevel% equ 0 (
    color 0C
    echo    ❌ خطا: Python %PYVER% خیلی قدیمی است!
    echo.
    echo    حداقل Python 3.9 مورد نیاز است.
    echo.
    echo    لطفاً Python 3.10.11 نصب کنید.
    echo.
    pause
    exit /b 1
)

echo    ✅ نسخه Python سازگار است

REM ════════════════════════════════════════════════════════════════
REM مرحله 3: چک کردن pip
REM ════════════════════════════════════════════════════════════════
echo.
echo [3/7] بررسی pip...

python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo    ⚠️  pip یافت نشد، در حال نصب...
    python -m ensurepip --upgrade
    if %errorlevel% neq 0 (
        color 0C
        echo    ❌ خطا در نصب pip!
        pause
        exit /b 1
    )
)
echo    ✅ pip موجود است

REM ════════════════════════════════════════════════════════════════
REM مرحله 4: آپدیت pip
REM ════════════════════════════════════════════════════════════════
echo.
echo [4/7] به‌روزرسانی pip...

python -m pip install --upgrade pip --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo    ⚠️  خطا در آپدیت pip (ادامه میدهیم...)
) else (
    echo    ✅ pip به‌روز شد
)

REM ════════════════════════════════════════════════════════════════
REM مرحله 5: پاک کردن cache
REM ════════════════════════════════════════════════════════════════
echo.
echo [5/7] پاک کردن cache قبلی...

python -m pip cache purge >nul 2>&1
echo    ✅ Cache پاک شد

REM ════════════════════════════════════════════════════════════════
REM مرحله 6: نصب پکیج‌ها
REM ════════════════════════════════════════════════════════════════
echo.
echo [6/7] نصب پکیج‌های مورد نیاز...
echo.
echo ⏳ این کار ممکن است 2-5 دقیقه طول بکشد...
echo    (بسته به سرعت 