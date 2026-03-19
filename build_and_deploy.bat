@echo off
echo ========================================
echo   BUILD ET DEPLOIEMENT COMPLET
echo ========================================
echo.

echo Etape 1/3 : Correction des chemins...

echo.
echo Etape 2/3 : Compilation avec PyInstaller...
call deploy.bat

echo.
echo Etape 3/3 : Copie des ressources...
call copy_resources.bat

echo.
echo ========================================
echo   BUILD COMPLET TERMINE !
echo ========================================
echo.
echo L'application est prete dans le dossier dist\
echo Executez dist\HUAHINE.exe pour la tester
echo.
pause
