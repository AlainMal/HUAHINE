# HUAHINE

Outil de navigation NMEA 2000 avec interface PyQt5 et serveur local Quart pour la visualisation cartographique, l’AIS, l’historique et la gestion de routes. Le projet permet:
- Lecture du bus CAN/NMEA2000 via un adaptateur CANUSB
- Visualisation en temps réel (table, instruments, carte embarquée)
- Export/import CSV (conversion NMEA2000)
- Aide intégrée
- Build en exécutable Windows via PyInstaller

Ce README remplace et conserve le guide utilisateur existant (section « Guide d’utilisation ») tout en ajoutant les informations techniques demandées.


## Sommaire
- Aperçu / fonctionnalités
- Pile technique (stack)
- Prérequis
- Installation (dev) et exécution
- Scripts et commandes
- Variables d’environnement
- Tests
- Structure du projet
- Guide d’utilisation (conservé)
- Licence
- TODO


## Aperçu / fonctionnalités
- Importer les données du bus CAN dans une table (PyQt5)
- Exporter des trames en CSV au format NMEA2000
- Carte embarquée (tiles hors-ligne .mbtiles à placer) avec projection, couches (Navionic/SonarChart, selon ressources), AIS
- Enregistrement/lecture d’historique (JSON) et de routes
- Serveur web local (Quart) exposant API + pages
- Aide/manuel via un mini-serveur Flask
- Packaging Windows (PyInstaller)


## Pile technique (stack)
- Langage: Python 3.x (testé et packagé sous Windows)
- GUI: PyQt5
- Asynchrone: asyncio, qasync
- Web: Quart (compatible Flask ASGI), Hypercorn (packagé), Flask pour le serveur d’aide
- Build: PyInstaller (via HUAHINE.spec)
- Données/cartes: fichiers .mbtiles servis par Quart; historique/route en JSON
- Drivers CAN: CANUSB (DLL canusbdrv64.dll), FTDI D2XX (voir section Guide / Drivers)

Gestionnaires/points d’entrée:
- Entrée principale: HUAHINE.py (lance l’UI PyQt5 et le serveur Quart embarqué)
- Serveur d’aide: serveur_aide.py (Flask, démarré en thread)
- Build: HUAHINE.spec + scripts .bat


## Prérequis
- Windows 10/11
- Python 3.9+ recommandé pour le développement (l’exécutable n’a pas besoin de Python installé)
- Outils système:
  - Git (optionnel)
  - PyInstaller (si build local): `pip install pyinstaller`
- Dépendances Python (non exhaustif, à installer en dev):
  - PyQt5
  - qasync
  - quart
  - hypercorn
  - flask
  - jinja2
  - werkzeug
  - wsproto, h11, h2, priority
  - sqlite3 (standard library)
  - autres modules du stdlib: asyncio, csv, subprocess, webbrowser, ctypes, logging, os, sys, json

Note: il n’y a pas de requirements.txt dans le dépôt. Voir TODO.

Drivers/Matériel (optionnel en dev):
- Adaptateur CANUSB + driver FTDI D2XX
- DLL canusbdrv64.dll fonctionnelle (voir Guide d’utilisation)


## Installation (dev) et exécution
Cloner le dépôt, puis installer les dépendances:

- Avec pip (exemple):
  - `py -3 -m venv .venv`
  - `.venv\Scripts\activate`
  - `pip install pyqt5 qasync quart hypercorn flask jinja2 werkzeug wsproto h11 h2 priority`

Lancer l’application en mode source (développement):
- `py -3 HUAHINE.py`

Remarques:
- Les cartes .mbtiles sont attendues dans `static\` au runtime. Voir section Build/Resources pour la copie.
- Des dossiers sont utilisés/attendus: `static\`, `history\`, `routes\`.


## Scripts et commandes
Scripts batch fournis:
- build_and_deploy.bat
  - Orchestration: corrige chemins (placeholder), appelle deploy.bat, puis copy_resources.bat
- deploy.bat
  - Supprime `dist\` puis lance `pyinstaller.exe --clean HUAHINE.spec`
  - Rappelle quoi copier dans `dist\static\` (mbtiles, icones, CSS, JS)
- copy_resources.bat
  - Copie des ressources (selon son contenu). Vérifiez/editez au besoin.

Spécification PyInstaller: HUAHINE.spec
- Inclut: Alain.ui, VoilierImage.ico, boat_config.json, templates/, aide/templates, aide/static, icones/, images/, static/
- Crée dans `dist\` des dossiers vides utiles: `static\icone`, `static\CSS`, `static\js`, `history`, `routes`

Exécutable Windows après build:
- `dist\HUAHINE.exe`


## Variables d’environnement
Aucune variable obligatoire détectée dans le code actuel.
- TODO: documenter d’éventuelles clés/API ou chemins spécifiques si ajoutés ultérieurement.


## Tests
Un script de simulation est fourni pour générer un historique de navigation factice:
- `test_simulation.py`
  - Crée/alimente `static\boat_history.json` avec des positions simulées.
  - Usage:
    - Dev: `py -3 test_simulation.py` (ou appeler `main()` depuis un runner)

Aucun framework de tests automatisés (pytest/unittest) n’est configuré pour l’instant. TODO ci-dessous.


## Structure du projet
Racine (extrait):
- HUAHINE.py — Entrée principale (PyQt5 + serveur Quart + logique NMEA2000)
- HUAHINE.spec — Spéc PyInstaller
- serveur_aide.py — Serveur Flask d’aide (thread dédié)
- test_simulation.py — Générateur de traces pour tests manuels
- Package/ — Modules applicatifs (CAN_dll, TempsReel, NMEA_2000, CANApplication, Constante, ...)
- templates/ — Templates web (Quart)
- static/ — Ressources web (CSS, icones, JS, tiles .mbtiles, JSON d’historique)
- aide/ — Site d’aide (templates + static)
- history/ — Dossier de sauvegarde d’historiques (créé/attendu)
- routes/ — Dossier de sauvegarde des routes (créé/attendu)
- images/, icones/ — Ressources GUI
- Alain.ui — Fichier UI Qt Designer
- VoilierImage.ico — Icône de l’application
- build_and_deploy.bat, deploy.bat, copy_resources.bat — Scripts Windows de build/copie
- README_DEPLOYMENT.md — Informations de déploiement complémentaires (si existant à consulter)


## Guide d’utilisation (conservé)
Vous avez HUAHINE.exe dans le répertoire 'dist'

![ecran](https://github.com/AlainMal/HUAHINE3/blob/master/aide/static/images/ecran.png)

Bienvenue dans le guide d'utilisation de HUAHINE. Cette application vous permet de gérer et visualiser vos données géographiques.
Fonctionnalités principales
 
    Importer les données du bus CAN sur la table
    Exporter le résultat en CSV sur NMEA 2000

Comment utiliser l'application

    Lancez l'application
    Raccordez l'adaptateur sur un port USB
    Raccordez sur le bus CAN le H et L
    Cliquez sur le bouton "OPEN"
    Cliquez sur le bouton "Lecture du bus CAN"
    Vous pouvez visualiser votre position sur la carte.
    Vous voyez aussi votre projection ainsi que les autres bateaux sur AIS

Enregister et importer en cliquant sur le bouton 'Ouvrir le fichier texte'

    Enregistrez le bus CAN en cochant la case à cocher
    Vous vous arrêtez quand vous voulez
    Cliquez sur le bouton "Importer le fichier CAN"
    Vous pouvez voir sur la table les différentes lignes importées
    Cliquez sur la table et vous voyez le résultat en NMEA 2000 sur la gauche

Exporter le NMEA 2000 en cliquant sur le bouton 'Exporter en NMEA 2000'

    Choisissez votre fichier au format .csv
    Enregistrez puis vous validez ou choisissez d'autres lignes à exporter
    Vous pouvez voir le fichier en .csv en cliquant sur "Yes"

Visualiser la carte en cliquant sur le bouton en forme de voilier

    Vous voyez où est votre bateau sur la carte, avec sa projection.
    Vous pouvez voir l'ensemble des bateaux AIS avec leurs projections.
    Vous pouvez changer le temps de projection<
    Vous pouvez changer la vue en "Navionic" ou en "SonarChart"
    Vous avez la possibilité d'enregistrer votre parcours et de le visualiser plus tard
    Vous avez la possibilité d'enregistrer une route et de la suivre plus tard
    Vous voyez le vent réel et apparent
    Vous voyez les instruments disponibles sur NMEA 2000
    Vous pouvez centrer votre bateau en cliquant sûr 👁️
    Vous pouvez diminuer ou augmenter le zoom.
    
![carte](https://github.com/AlainMal/HUAHINE3/blob/master/aide/static/images/Carte.png)

Comment installer l'application (binaire)

    Il faut simplement récuperer le répertoire "HUAHINE". Il n'y a pas d'installation à faire.
    Il faut éxécuter le fichier "HUAHINE.exe" dans le répertoire "HUAHINE".

    Il faut, pour l'instant, installer le CANUSB.
        Récupérez le driver "D2XX".
        Exécutez le CDM2123620_Setup.exe, situé dans le fichier importé.
        Je vous recommande de récupérer la dll "canusbdrv64.dll" situé sur ce dernier téléchargement.
        Car il y a un problème sur 'canusb_Status' sur la "canusbdrv64.dll" fournit avec le setup du CANUSB;
        Donc, il faut copiez le fichier "canusbdrv64.dll" dans le répertoire :Windows/system32. 

Branchement sur le bus NMEA 2000.

![cia102](https://github.com/AlainMal/HUAHINE3/blob/master/aide/static/images/cia102.gif)
![canusb-con-diagram](https://github.com/AlainMal/HUAHINE3/blob/master/aide/static/images/canusb-con-diagram.png)

![PriseNMEA2000](https://github.com/AlainMal/HUAHINE3/blob/master/aide/static/images/PriseNMEA2000.png)
![BorneNMEA2000](https://github.com/AlainMal/HUAHINE3/blob/master/aide/static/images/BorneNMEA2000.png)

Vous n'avez qu'à brancher les bornes CAN_H et CAN_L sur les pins 4 et 5 du NMEA2000.

Remarque : Si vous êtes branché à la place de la terminaison, il faut ajouter une resistance de 120 Ohms.

    Maintenant, vous avez tout raccordé et mis vos drivers dans votre PC.
        Mettez en route votre réseau NMEA 2000.
        Utilisez l'application, HUAHINE.exe


## Licence
- TODO: le dépôt ne contient pas de fichier de licence explicite. Ajouter LICENCE (MIT/GPL/… selon choix de l’auteur) et compléter cette section.


## TODO
- Ajouter un requirements.txt précis (versions testées), ou Pipfile/poetry si souhaité
- Documenter les versions minimales Python/Windows exactes validées
- Lister précisément les dépendances côté Quart/Hypercorn selon le pack PyInstaller
- Documenter le port du serveur Quart (déterminé dans HUAHINE.py) et éventuels endpoints publiquement exposés
- Ajouter des tests automatisés (pytest) et un workflow CI si pertinent
- Fournir des exemples de fichiers .mbtiles et préciser leur source/licence

## Remarque d'ordre générale :
- Cette application est un projet personnel,
        elle évolue en permanence. Je me suis fait aider des AI, pour le JavaScript, le Python et le CSS,
        certaine sont gratuites, mais les payantes sont excellentes. D'autre part je suis partie depuis le USBCAN dont
        j'ai traduit les codes pour les transformer en
        NMEA 2000, à l'aide de <a href="https://canboat.github.io/canboat/canboat.html" target="_blank"> 'CANBoat'</a>, je n'ai pas tous convertit,
        mais j'ai tout ce qu'il y a sur mon bateau, j'ai réalisé les cartes maritimes à l'aide de
        <a href="https://sasplanet.geojamal.com/search/label/Download" target ="_blank">'SASPlanet'</a> sous <a href="https://leafletjs.com/" target ="_blank">'Leaflet'</a> sur
        lesquels j'ai mis mon bateau et les autres sous AIS avec une projection en minutes, j'ai installé le suivi
        de mon bateau en temps réel que j'enregistre et peut revoir mes parcours, j'ai aussi installé les routes
        que je peux charger pour plus tard, j'ai aussi installé un écran du vent qui me donne la direction et la force
        du vent en réel et apparent, j'ai aussi installé la liste des instruments NMEA 2000 qui est un gadget qui
        permet de voir tous les instruments connectés.<br>
        Je n'ai pas suivi le programme standard, car j'avais dèjà réaliser un programme sous Excel, j'avais déjà pensé
        à utiliser une trame de 64 bits, mais il était impossible de le faire en VBA et je comprends mieux maintenant
        le PyThon et j'aurais du l'exploité au mieux en
        utilisant des trames de 64 bits. J'ai remarqué que les octets de numéro de trames ne sont pas décrit dans 'CANBoat',
        et cela me posait des problèmes pour savoir sur quel octet on est censé être. J'ai découvert <a href="https://github.com/tomer-w/nmea2000" target ="_blank">'tomer-w'</a> qui est excellent
        sur GitHub, mais je ne suis pas fort en PyThon et je n'ai pas encore compris comment il fait pour compter les bits
        en laissant les numéros de trames de côté, peut-être en prenant les 6 octets pour la trame 0 et les 7 octets pour les autres de poids fort, simplement sur les
        trames qui ont plus de 8 octets (fast-packet PGN) et je pense qu'il prend toutes les trames d'un même PGN et aprés qu'il lance le décodage de tous les bits,
        moi, je décode trame par trame et je fais une mise en mémoire pour les trames dont les codes se situent sur
        plusieurs trames.
