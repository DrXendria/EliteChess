@echo off
setlocal
echo ========================================================
echo   Elite Chess Tournament Manager - Windows Derleme
echo ========================================================
echo.

echo [1/3] Calisan uygulama varsa kapatiliyor...
taskkill /F /IM Elite_Chess_Manager.exe /T 2>NUL
echo.

echo [2/3] Gerekli bagimliliklar kuruluyor...
pip install -r requirements.txt pyinstaller
echo.

echo [3/3] PyInstaller ile tek dosya EXE olusturuluyor...
python -m PyInstaller ^
    --clean ^
    --noconfirm ^
    --noconsole ^
    --onefile ^
    --name "Elite_Chess_Manager" ^
    --icon "resources/logo.ico" ^
    --paths . ^
    --add-data "resources;resources" ^
    main.py

echo.
if exist "dist\Elite_Chess_Manager.exe" (
    echo ========================================================
    echo   Derleme basariyla tamamlandi!
    echo   Konum: dist\Elite_Chess_Manager.exe
    echo ========================================================
) else (
    echo [HATA] Derleme basarisiz oldu!
)
echo.
pause
