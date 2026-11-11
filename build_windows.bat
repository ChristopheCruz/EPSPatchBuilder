@echo off
rem Construit EPSBuilder.exe (Windows). Necessite Python 3.10 ou plus recent.
setlocal
cd /d "%~dp0"

where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% --version || (echo Python est introuvable. Installez-le depuis python.org puis relancez. & pause & exit /b 1)

if not exist .venv (
    %PY% -m venv .venv || (echo Creation de l'environnement impossible. & pause & exit /b 1)
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller || (echo Installation des composants impossible. & pause & exit /b 1)

python tests\test_epsbuilder.py || (echo Les tests ont echoue, compilation annulee. & pause & exit /b 1)

pyinstaller --noconfirm --clean --windowed --onefile --name EPSBuilder --collect-all _soundfile_data --add-data "epsbuilder\MANUEL.md;epsbuilder" --add-data "epsbuilder\MANUAL.md;epsbuilder" --add-data "epsbuilder\LICENCE.txt;epsbuilder" run_gui.py || (echo La compilation a echoue. & pause & exit /b 1)

echo.
echo Termine : dist\EPSBuilder.exe
pause
