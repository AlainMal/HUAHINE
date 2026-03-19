@echo off
echo ========================================
echo   COPIE DES RESSOURCES DANS DIST
echo ========================================
echo.

rem Vérifier que dist existe
if not exist dist (
    echo ERREUR : Le dossier dist n'existe pas !
    echo Executez d'abord deploy.bat
    pause
    exit /b 1
)

echo Copie des fichiers MBTiles...
copy static\cartes1.mbtiles dist\static\ >nul 2>&1
copy static\cartes2.mbtiles dist\static\ >nul 2>&1
copy static\cartes3.mbtiles dist\static\ >nul 2>&1
echo   [OK] MBTiles copies

echo.
echo Copie des icones web...
xcopy /E /I /Y static\icone dist\static\icone >nul 2>&1
echo   [OK] Icones web copiees

echo.
echo Copie des CSS...
xcopy /E /I /Y static\CSS dist\static\CSS >nul 2>&1
echo   [OK] CSS copies

echo.
echo Copie des JS...
xcopy /E /I /Y static\js dist\static\js >nul 2>&1
echo   [OK] JS copies

echo.
echo Copie des autres fichiers static...
copy static\*.png dist\static\ >nul 2>&1
copy static\*.ico dist\static\ >nul 2>&1
echo   [OK] Autres fichiers copies

echo.
echo ========================================
echo   COPIE TERMINEE !
echo ========================================
echo.
echo Tous les fichiers ont ete copies dans dist\
echo Vous pouvez maintenant executer dist\HUAHINE.exe
echo.
pause
