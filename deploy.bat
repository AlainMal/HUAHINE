@echo off
rem Attendre 2 secondes pour s'assurer que tous les processus sont fermés
timeout /t 2

rem Supprime l'ancien dossier dist si existant
if exist dist (
    rmdir /s /q dist
    rem Attendre que la suppression soit terminée
    timeout /t 2
)

rem Compile avec PyInstaller en utilisant le chemin complet
pyinstaller.exe  --clean HUAHINE.spec

rem Attendre que la compilation soit terminée
timeout /t 2

echo.
echo ========================================
echo   COMPILATION TERMINEE
echo ========================================
echo.
echo Fichiers inclus automatiquement :
echo   - Alain.ui
echo   - VoilierImage.ico
echo   - boat_config.json
echo   - templates/
echo   - aide/templates/
echo   - aide/static/
echo   - icones/ (pour PyQt)
echo   - images/ (pour PyQt)
echo.
echo Repertoires vides crees :
echo   - static/icone/
echo   - static/CSS/
echo   - static/js/
echo   - history/
echo   - routes/
echo.
echo ========================================
echo   FICHIERS A COPIER MANUELLEMENT
echo ========================================
echo.
echo Copiez les fichiers suivants dans dist\ :
echo.
echo 1. FICHIERS MBTILES (dans dist\static\) :
echo    copy static\cartes1.mbtiles dist\static\
echo    copy static\cartes2.mbtiles dist\static\
echo    copy static\cartes3.mbtiles dist\static\
echo.
echo 2. ICONES WEB (dans dist\static\icone\) :
echo    xcopy /E /I static\icone dist\static\icone
echo.
echo 3. CSS (dans dist\static\CSS\) :
echo    xcopy /E /I static\CSS dist\static\CSS
echo.
echo 4. JAVASCRIPT (dans dist\static\js\) :
echo    xcopy /E /I static\js dist\static\js
echo.
echo 5. AUTRES FICHIERS STATIC (dans dist\static\) :
echo    copy static\*.png dist\static\
echo    copy static\*.ico dist\static\
echo.
echo ========================================
echo   Deploiement termine !
echo ========================================
echo.
pause
