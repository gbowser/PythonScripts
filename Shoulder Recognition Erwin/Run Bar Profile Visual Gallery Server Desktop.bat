@echo off
cd /d "%~dp0.."
python "Shoulder Recognition Erwin\Build Bar Profile Visual Gallery.py" --pc Desktop --serve --port 8899
pause
