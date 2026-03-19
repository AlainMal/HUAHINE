# Guide de déploiement HUAHINE.exe

## Modifications effectuées

### 1. HUAHINE.spec
✅ Ajout des `hiddenimports` pour **Quart** et **Flask**
✅ Inclusion des dossiers `aide/templates` et `aide/static` pour le serveur d'aide
✅ Création automatique des répertoires vides : `static/icone`, `static/CSS`, `static/js`, `history`, `routes`
✅ **Exclusion des fichiers .mbtiles** pour réduire la taille de l'exe

### 2. serveur_aide.py
✅ Ajout de `resource_path()` pour localiser les templates et static de Flask

### 3. deploy.bat
✅ Instructions détaillées pour copier manuellement les ressources
✅ Création automatique de la structure de répertoires

### 4. fix_paths.py (nouveau)
✅ Script pour corriger automatiquement les chemins des icônes PyQt

## Procédure de déploiement

### Étape 1 : Corriger les chemins des icônes
```bash
python fix_paths.py
```

### Étape 2 : Compiler l'application
```bash
deploy.bat
```

### Étape 3 : Copier manuellement les fichiers

#### A. Fichiers MBTiles (dans `dist/static/`)
```
copy static\cartes1.mbtiles dist\static\
copy static\cartes2.mbtiles dist\static\
copy static\cartes3.mbtiles dist\static\
```

#### B. Icônes (dans `dist/static/icone/`)
```
xcopy /E /I static\icone dist\static\icone
```

#### C. CSS (dans `dist/static/CSS/`)
```
xcopy /E /I static\CSS dist\static\CSS
```

#### D. JavaScript (dans `dist/static/js/`)
```
xcopy /E /I static\js dist\static\js
```

#### E. Autres fichiers static (dans `dist/static/`)
```
copy static\*.png dist\static\
copy static\*.ico dist\static\
```

### Étape 4 : Tester l'application
```
cd dist
HUAHINE.exe
```

## Structure finale de dist/

```
dist/
├── HUAHINE.exe
├── VoilierImage.ico
├── Alain.ui
├── boat_config.json
├── templates/
│   └── index.html
├── aide/
│   ├── templates/
│   │   ├── index.html
│   │   ├── enregistre.html
│   │   ├── import.html
│   │   ├── export.html
│   │   ├── cartes.html
│   │   └── install.html
│   └── static/
├── static/
│   ├── cartes1.mbtiles   (à copier manuellement)
│   ├── cartes2.mbtiles   (à copier manuellement)
│   ├── cartes3.mbtiles   (à copier manuellement)
│   ├── icone/            (à copier manuellement)
│   ├── CSS/              (à copier manuellement)
│   └── js/               (à copier manuellement)
├── history/              (vide, pour les parcours)
└── routes/               (vide, pour les routes)
```

## Résolution des problèmes

### Erreur "Internal Server Error" sur Flask
✅ Résolu : Ajout de Flask dans `hiddenimports`
✅ Résolu : Utilisation de `resource_path()` dans `serveur_aide.py`

### Erreur "Internal Server Error" sur Quart
✅ Résolu : Ajout de Quart et ses dépendances dans `hiddenimports`

### Icônes manquantes dans PyQt
✅ Résolu : Utilisation de `resource_path()` pour tous les `QIcon()`
✅ Solution : Exécuter `fix_paths.py` avant chaque compilation

### Images manquantes sur la carte web
✅ Solution : Copier manuellement `static/icone/`, `static/CSS/`, `static/js/`

## Notes importantes

- Les fichiers `.mbtiles` ne sont **pas** inclus dans l'exe pour réduire sa taille
- Vous devez les copier **manuellement** après chaque compilation
- Les répertoires `history/` et `routes/` sont créés automatiquement mais vides
- Le serveur Flask (aide) tourne sur le port 5001
- Le serveur Quart (carte) tourne sur le port 5000
