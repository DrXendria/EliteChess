@echo off
echo Uygulama kapatiliyor (eger aciksa)...
taskkill /F /IM Elite_Chess_Manager.exe /T 2>NUL
echo.
echo PyInstaller kuruluyor (gerekirse)...
pip install pyinstaller
echo.
echo Uygulama EXE dosyasina donusturuluyor...
python -m PyInstaller --clean --noconsole --onefile --name "Elite_Chess_Manager" --paths . --add-data "resources;resources" main.py
echo.
echo Derleme tamamlandi! 
echo Elite_Chess_Manager.exe dosyasi 'dist' klasoru icerisinde olusturuldu.
pause
