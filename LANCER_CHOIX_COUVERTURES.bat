@echo off
cd /d "C:\Users\guillaume\Documents\GitHub\soccerfans-miniappv2"
python -c "import PIL" 2>nul
if errorlevel 1 (
  echo Installation de Pillow...
  python -m pip install pillow
  if errorlevel 1 pause & exit /b 1
)
python ".\choisir_couvertures.py"
pause
