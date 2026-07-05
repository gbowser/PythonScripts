@echo off
cd /d "%~dp0.."
set "GALLERY_URL=http://127.0.0.1:8899/"
choice /C YN /N /M "Open browser at %GALLERY_URL% after starting the server? [Y/N] "
if errorlevel 2 goto run_server
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process '%GALLERY_URL%'"
:run_server
python "Shoulder Recognition Erwin\Build Bar Profile Visual Gallery.py" --pc Laptop --serve --port 8899
pause
