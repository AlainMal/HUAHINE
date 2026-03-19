# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

# ---------------------------------------------------------
# 1. Construire la liste datas AVANT l'appel à Analysis()
# ---------------------------------------------------------

from PyInstaller.utils.hooks import collect_data_files

datas = [
    ('Alain.ui', '.'),
    ('VoilierImage.ico', '.'),
    ('templates', 'templates'),
    ('aide/templates', 'aide/templates'),
    ('aide/static', 'aide/static'),
    ('boat_config.json', '.'),
    ('icones', 'icones'),
]

# Ajouter explicitement tous les fichiers static
static_files = []
for root, dirs, files in os.walk('static'):
    for file in files:
        if not file.endswith('.mbtiles'):  # Exclure les fichiers mbtiles
            src_path = os.path.join(root, file)
            # Le chemin de destination doit préserver la structure de dossiers
            dest_dir = root
            static_files.append((src_path, dest_dir))

datas += static_files

# Ajouter le dossier images (sans .mbtiles)
images_files = [
    (str(p), 'images')
    for p in Path('images').rglob('*')
    if p.is_file() and p.suffix != '.mbtiles'
]

datas += images_files

# ---------------------------------------------------------
# 2. Analysis
# ---------------------------------------------------------

a = Analysis(
    ['HUAHINE.py'],
    pathex=[],
    binaries=[],
    datas=datas,   
    hiddenimports=[
        'quart',
        'hypercorn',
        'hypercorn.asyncio',
        'hypercorn.config',
        'wsproto',
        'h11',
        'h2',
        'priority',
        'flask',
        'flask.templating',
        'jinja2',
        'werkzeug',
        'webCartes',
        'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtWebEngineCore',
        'PyQt5.QtWebChannel',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='HUAHINE',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# ---------------------------------------------------------
# 3. Création des répertoires vides dans dist
# ---------------------------------------------------------

# Les dossiers static sont maintenant copiés automatiquement via datas
# Il faut seulement créer les dossiers pour history et routes (dossiers de travail)
os.makedirs(os.path.join(DISTPATH, 'history'), exist_ok=True)
os.makedirs(os.path.join(DISTPATH, 'routes'), exist_ok=True)