// ==============================================
// 1. CONFIGURATION ET CONSTANTES GLOBALES
// ==============================================
let historyLayers = [];

const CONFIG = {
    MAP: {
        initialPosition: [43.2438, 5.3656],
        initialZoom: 13,
        minZoom: 2,
        maxZoom: 18
    },
    UPDATES: {
        positionInterval: 5000, // Temps de rafraichissement de ma position (en ms)
        aisInterval: 10000,     // Temps de rafraichissement des AIS (en ms)
        defaultProjection: 0.0,
        defaultSaveInterval: 3
    },
    MESSAGES: {
        duration: 5000,         // Durée d'affichage du message temporaire.
        fadeInDuration: 300,
        fadeOutDuration: 300
    }
};

// ==============================================
// 2. ÉTAT DE L'APPLICATION CENTRALISÉE
// ==============================================
const AppState = {
    // Interface utilisateur
    isInfoVisible: true,
    activeMessageElement: null,
    forceKeepOpen: false,
    IsVentVisible: true,
    IsConnected: false,
    IsIntervenantVisible: false,

    // Enregistrement et suivi
    projectionHours: CONFIG.UPDATES.defaultProjection,
    scrutationCount: 0,
    saveInterval: CONFIG.UPDATES.defaultSaveInterval,
    lastSavedFilename: null,
    isRecordingActive: false,

    isTraceDisplayed: false,

    // Éléments de carte
    shipMarker: null,
    persistentPopup: null,
    updateInterval: null,
    aisUpdateInterval: null,

    // Récupérer le MMSI du bateau
    myMmsi: nettoyerMmsi(window.coordinates?.boat_info?.mmsi || ""),

    // Suivi d'interaction souris
    isDragging: false,

    dragStartPos: null,

    IsNoDisplay : false,

    // Méthodes de gestion d'état
    setRecordingActive(active) {
        this.isRecordingActive = active;
        this.scrutationCount = 0;
    },

    setTraceDisplayed(displayed) {
        this.isTraceDisplayed = displayed;
    },

    resetScrutationCount() {
        this.scrutationCount = 0;
    },

    incrementScrutationCount() {
        this.scrutationCount++;
        console.log(`🧮 scrutationCount = ${this.scrutationCount}/${this.saveInterval}`);

        return this.scrutationCount >= this.saveInterval;
    },

    updateSaveInterval(newInterval) {
        console.log("⏳ updateSaveInterval appelée avec", newInterval);

    if (newInterval >= 1 && newInterval <= 60) {
        this.saveInterval = newInterval;
        //this.scrutationCount = 0; // 🔁 Réinitialise le compteur
        console.log("🔴 saveInterval = 0");
        return true;
    }
        return false;
    },

    updateProjectionHours(minutes) {
        if (minutes >= 0 && minutes <= 1440) {
            this.projectionHours = minutes / 60;
            return true;
        }
        return false;
    }
};

const AppData = {
    positionHistory: [],
    aisMarkers: {},
    sogLines: {},

    // Fonction pour obtenir la couleur en fonction de la vitesse
    getSpeedColor(speed) {
        if (speed < 0.5) return '#000000';    // Noir
        else if (speed < 1) return '#4B0082'; // Violet
        else if (speed < 2) return '#8B0000'; // Rouge foncé
        else if (speed < 3) return '#D2691E'; // Orange
        else if (speed < 4) return '#F4A460'; // Jaune orangé
        else if (speed < 5) return '#FFD700'; // Jaune
        else if (speed < 6) return '#9ACD32'; // Vert clair
        else if (speed < 7) return '#87CEFA'; // bleu
        else if (speed < 8) return '#7FFFD4'; // Cyan
        else if (speed < 9) return '#E0FFFF'; // bleu très clair
        else return '#FFFFFF';                // Blanc
    }
};

// ==============================================
// 2. UTILITAIRES ANGLE VENT (affichage)
// ==============================================
function normalizeDeg(val){
    var v = Number(val);
    if (isNaN(v)) return null;
    v = v % 360;
    if (v < 0) v += 360;
    return v;
}
// Normalise en angle signé dans [-180, 180]
function normalizeSignedDeg(val){
    var v = Number(val);
    if (isNaN(v)) return null;
    v = v % 360;
    if (v > 180) v -= 360;
    if (v <= -180) v += 360;
    return v;
}
function reduceAngleTo180(angle){
    var a = normalizeDeg(angle);
    if (a === null) return null;
    return a <= 180 ? a : (360 - a);
}
function reduceAngleTo90(angle){
    var a = normalizeDeg(angle);
    if (a === null) return null;
    var r = a <= 180 ? a : (360 - a);
    return r <= 90 ? r : (180 - r);
}
function computeAttitudeFromAngle(angle){
    // Gère les angles signés (-180..180) et non signés (0..360)
    if (typeof angle === 'number' && angle >= -180 && angle <= 180) {
        if (angle === 180 || angle === -180 || angle === 0) {
            // 180/0 sont ambigus par défaut, on considère Tribord sauf -180 explicite
            return angle < 0 ? 'Bd' : 'Td';
        }
        return angle < 0 ? 'Bd' : 'Td';
    }
    var a = normalizeDeg(angle);
    if (a === null) return '';
    return (a >= 0 && a < 180) ? 'Td' : 'Bd';
}
function angle90Enabled(){
    try { return localStorage.getItem('angle90') === '1'; } catch(e){ return false; }
}
function formatWind(angle){
    if (typeof angle !== 'number') return 'N/A';
    var side = computeAttitudeFromAngle(angle);
    var val = angle90Enabled() ? reduceAngleTo90(angle) : reduceAngleTo180(angle);
    if (val === null) return 'N/A';
    return (side === 'Td' ? 'Tribord ' : 'Babord ') + Math.round(val) + '°';
}


// ==============================================
// 3. UTILITAIRES
// ==============================================
function nettoyerMmsi(valeur) {
      return String(valeur).replace(/\D+/g, ''); // supprime tout sauf chiffres
    }

function showMapModal(title, message) {
  return new Promise((resolve) => {
    const modal = document.getElementById("mapModal");
    document.getElementById("modal-title").textContent = title;
    document.getElementById("modal-message").textContent = message;
    modal.style.display = "block";

    const okBtn = document.getElementById("modal-ok");
    const cancelBtn = document.getElementById("modal-cancel");

    // Nettoyage des anciens handlers
    okBtn.onclick = () => {
      modal.style.display = "none";
      resolve(true);   // OK choisi
    };
    cancelBtn.onclick = () => {
      modal.style.display = "none";
      resolve(false);  // Annuler choisi
    };
  });
};

const MessageUtils = {
    show(message, type = 'info', persistent = false) {
        this.clear();
        if (!message) return;

        const messageElement = this.createElement(message, type);
        this.applyStyles(messageElement, type);
        document.body.appendChild(messageElement);

        if (persistent) {
            AppState.activeMessageElement = messageElement;
        } else {
            this.scheduleRemoval(messageElement);
        }
    },

    createElement(message, type) {
        const element = document.createElement('div');
        element.innerHTML = message;
        element.className = `app-message app-message--${type}`;
        return element;
    },

    applyStyles(element, type) {
        const baseStyles = {
            position: 'fixed',
            top: '100px',
            left: '50%',
            transform: 'translate(-50%, 0)',
            backgroundColor: 'white',
            padding: '20px 30px',
            borderRadius: '8px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
            zIndex: '2000',
            fontFamily: 'Arial, sans-serif',
            maxWidth: '80%',
            textAlign: 'center',
            animation: `fadeIn ${CONFIG.MESSAGES.fadeInDuration}ms ease-out`,
            fontSize: '16px',
            fontWeight: 'bold'
        };

        const typeStyles = this.getTypeStyles(type);
        Object.assign(element.style, baseStyles, typeStyles);
    },

    getTypeStyles(type) {
        const styles = {
            error: { color: '#d32f2f', border: '2px solid #d32f2f' },
            success: { color: '#2e7d32', border: '2px solid #2e7d32' },
            info: { color: '#00008B', border: '2px solid #00008B' }
        };
        return styles[type] || styles.info;
    },

    scheduleRemoval(element) {
        setTimeout(() => {
            element.style.animation = `fadeOut ${CONFIG.MESSAGES.fadeOutDuration}ms ease-in`;
            setTimeout(() => {
                if (element.parentNode) {
                    element.remove();
                }
                if (AppState.activeMessageElement === element) {
                    AppState.activeMessageElement = null;
                }
            }, CONFIG.MESSAGES.fadeOutDuration);
        }, CONFIG.MESSAGES.duration);
    },

    clear() {
        if (AppState.activeMessageElement) {
            AppState.activeMessageElement.remove();
            AppState.activeMessageElement = null;
        }
    }
};

const showMessage = (message, type = 'info', persistent = false) => {
    MessageUtils.show(message, type, persistent);
};
// Expose global for HTML inline handlers and other scripts
window.showMessage = showMessage;

const showNotification = (message, type = 'info', persistent = false) => {
    showMessage(message, type, persistent);
};

const nauticalMilesToDegrees = (nauticalMiles) => {
    return nauticalMiles / 60;
};

const normalizeFilename = (name) => {
    name = name.trim();
    return name.endsWith(".json") ? name : `${name}.json`;
};

// ==============================================
// 4. INITIALISATION DE LA CARTE ET DES COUCHES
// ==============================================
const map = L.map('map', {
    center: CONFIG.MAP.initialPosition,
    zoomDelta: 1,
    minZoom: CONFIG.MAP.minZoom,
    maxZoom: CONFIG.MAP.maxZoom,
    keepInView: false,
    maxBounds: null,
    maxBoundsViscosity: 0
}).setView(CONFIG.MAP.initialPosition, CONFIG.MAP.initialZoom);

const pinIcon = L.divIcon({
    html: '<img src="./static/icone/pointeur.png" alt="Historique" width="16" height="16">',
    className: 'pin-icon',
    iconSize: [20, 20],
    iconAnchor: [10, 20],
    interactive: false
});


// Couches de cartes MBTiles
const mondeTileLayer = L.tileLayer('/tile/cartes1.mbtiles/{z}/{x}/{y}', {
    tms: true,
    opacity: 0.7,
    attribution: 'MBTiles Map - Monde',
    maxZoom: 18,
    minZoom: 2
});

const merTileLayer = L.tileLayer('/tile/cartes2.mbtiles/{z}/{x}/{y}', {
    tms: true,
    opacity: 0.7,
    attribution: 'MBTiles Map - Marseille',
    maxZoom: 18,
    minZoom: 2
});

const navionicsTileLayer = L.tileLayer('/tile/cartes3.mbtiles/{z}/{x}/{y}', {
    tms: true,
    opacity: 0.7,
    attribution: 'MBTiles Map - Navionics',
    maxZoom: 18,
    minZoom: 2
});

// Ajout de la couche par défaut
mondeTileLayer.addTo(map);

// Contrôle des couches
const baseMaps = {
    "Carte Plan&egrave;te": mondeTileLayer,
    "Carte SonarChart": merTileLayer,
    "Carte Navionics": navionicsTileLayer
};
L.control.layers(baseMaps, null, {
    collapsed: false,
    position: 'topleft'  // Ajout de cette ligne pour forcer la position à gauche
}).addTo(map);

const updateStatusIndicator = (isActive) => {
    const indicator = document.getElementById('status-indicator');
    if (!indicator) return;

    if (isActive) {
        AppState.IsConnected = true;
        indicator.classList.add('active');
        indicator.classList.remove('inactive');
        indicator.title = "Actif : Vous êtes connecté";
    } else {
        AppState.IsConnected = false;
        indicator.classList.add('inactive');
        indicator.classList.remove('active');
        indicator.title = "Inactif : Vous n'êtes pas connecté au NMEA 2000";
    }
};

// Demande si on est connecté au NMEA2000
setInterval(() => {
    fetch('/status')
        .then(res => {
            if (!res.ok) throw new Error("Réponse non OK");
            return res.json();
        })
        .then(data => {
            updateStatusIndicator(data.active);
        })
        .catch(err => {
            console.warn("Erreur de connexion au backend :", err);
            updateStatusIndicator(false); // force l’état inactif si erreur
        });
}, 2000);

// ==============================================
// 5. ÉLÉMENTS DE LA CARTE (MARQUEURS, LIGNES)
// ==============================================
// Popup persistant
const persistentPopup = L.popup({
    autoClose: false,
    closeOnClick: false,
    closeButton: true
});

persistentPopup.on('remove', () => {
    AppState.forceKeepOpen = false;
});

// Suivi de la position
let polyline = L.polyline([CONFIG.MAP.initialPosition], {
    color: 'blue',
    weight: 2,
    opacity: 0.7
}).addTo(map);


// Ligne de projection
const projectionLine = L.polyline([], {
    color: '#1e88e5',
    weight: 2,
    opacity: 0.8,
    dashArray: '7, 7',
    className: 'animated-dash'
}).addTo(map);

// ==============================================
// 6. FONCTIONS DE GESTION DES MARQUEURS
// ==============================================
const createCustomIcon = (angle = 0, shouldFlip = false) => {
    const adjustedAngle = angle - 270;
    return L.divIcon({
        html: `<div class="ship-icon" id="unique-ship-icon">
            <img src="/static/VoilierImage.png"
                 style="transform:
                        rotate(${adjustedAngle}deg)
                        scaleY(${shouldFlip ? -1 : 1});
                        width: 30px; height: 30px;
                        transition: all 0.3s ease;">
        </div>`,
        className: 'custom-ship-icon',
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });
};

const updateShipMarker = (position, angle) => {
    let normalizedAngle = ((angle % 360) + 360) % 360;
    const shouldFlip = normalizedAngle > 0 && normalizedAngle < 180;
    const icon = createCustomIcon(angle, shouldFlip);

    if (AppState.shipMarker) {
        AppState.shipMarker.setLatLng(position);
        AppState.shipMarker.setIcon(icon);
    } else {
        AppState.shipMarker = L.marker(position, { icon }).addTo(map);
    }
};

const clearAllMarkers = () => {
    map.eachLayer((layer) => {
        if (layer instanceof L.Marker) {
            map.removeLayer(layer);
        }
    });
    AppState.shipMarker = null;
};

const initializeShip = () => {
    updateShipMarker(CONFIG.MAP.initialPosition, 0);
};

// Désactive/active temporairement les interactions du marqueur du bateau
// Utilisé pour éviter que le clic sur le bateau intercepte les clics de la carte
function setShipMarkerInteractive(isInteractive) {
    if (!AppState || !AppState.shipMarker) return;
    try {
        // Empêcher le clic sur le marqueur pendant le mode mesure
        if (!isInteractive) {
            AppState.shipMarker.off('click');
        }
        const iconEl = AppState.shipMarker._icon;
        const shadowEl = AppState.shipMarker._shadow;
        if (iconEl) iconEl.style.pointerEvents = isInteractive ? 'auto' : 'none';
        if (shadowEl) shadowEl.style.pointerEvents = isInteractive ? 'auto' : 'none';
    } catch (e) {
        console.warn('setShipMarkerInteractive error:', e);
    }
}

// ==============================================
// 7. GESTION DES AIS, QUI SONT SUR LA CARTE
// ==============================================
// Variable pour contrôler la visibilité des bateaux AIS
let aisVisible = true;

const toggleAISVisibility = () => {
    const button = document.getElementById('aisVisibilityButton');

    if (aisVisible) {
        // Masquer tous les marqueurs et lignes AIS
        hideAllAISMarkers();
        aisVisible = false;
        button.style.background = '#f44336'; // Rouge

        button.title = 'Afficher les bateaux AIS sur la carte';
        showMessage('Bateaux AIS masqués.', 'error');
        console.log("🔴 Marqueurs AIS masqués");
    } else {
        // Afficher tous les marqueurs et lignes AIS
        showAllAISMarkers();
        aisVisible = true;
        button.style.background = '#FFFFFF'; // Vert

        button.title = 'Masquer les bateaux AIS sur la carte';
        showMessage('Bateaux AIS Affichés.', 'info');
        console.log("🟢 Marqueurs AIS affichés");
    }
};

const hideAllAISMarkers = () => {
    // Masquer tous les marqueurs AIS
    Object.keys(AppData.aisMarkers).forEach(mmsi => {
        if (map.hasLayer(AppData.aisMarkers[mmsi])) {
            map.removeLayer(AppData.aisMarkers[mmsi]);
        }
    });

    // Masquer toutes les lignes de projection SOG
    Object.keys(AppData.sogLines).forEach(mmsi => {
        if (map.hasLayer(AppData.sogLines[mmsi])) {
            map.removeLayer(AppData.sogLines[mmsi]);
        }
    });
};

const showAllAISMarkers = () => {
    // Afficher tous les marqueurs AIS
    Object.keys(AppData.aisMarkers).forEach(mmsi => {
        if (!map.hasLayer(AppData.aisMarkers[mmsi])) {
            AppData.aisMarkers[mmsi].addTo(map);
        }
    });

    // Afficher toutes les lignes de projection SOG
    Object.keys(AppData.sogLines).forEach(mmsi => {
        if (!map.hasLayer(AppData.sogLines[mmsi])) {
            AppData.sogLines[mmsi].addTo(map);
        }
    });
};

const updateAISMarker = (ship) => {
    console.log("Mise à jour/création du marqueur pour MMSI:", ship.mmsi);

    // Vérifications de sécurité pour les données
    // N'ignorent pas les coordonnées valant 0 ; on vérifie uniquement null/undefined/vides/'N/A'
    const latRaw = ship.latitude;
    const lonRaw = ship.longitude;
    if (latRaw === undefined || latRaw === null || lonRaw === undefined || lonRaw === null || latRaw === '' || lonRaw === '' || latRaw === 'N/A' || lonRaw === 'N/A') {
        console.warn(`Navire ${ship.mmsi} ignoré - coordonnées manquantes ou invalides:`, ship.latitude, ship.longitude);
        return;
    }

    // Si le bateau-porte le même MMSI que moi, l'ignorer
    const myMmsi = nettoyerMmsi(window.coordinates?.boat_info?.mmsi);
    const shipMmsi = nettoyerMmsi(ship?.mmsi);

    if (myMmsi && shipMmsi === myMmsi) {
      console.log(`Navire ignoré (MMSI identique au mien) : ${ship.mmsi}`);
      return;
    }

    // Conversion sécurisée des coordonnées
    let lat, lon;
    try {
        lat = parseFloat(ship.latitude);
        lon = parseFloat(ship.longitude);

        if (isNaN(lat) || isNaN(lon)) {
            console.warn(`Navire ${ship.mmsi} ignoré - coordonnées non numériques`);
            return;
        }
    } catch (e) {
        console.warn(`Erreur de conversion des coordonnées pour ${ship.mmsi}:`, e);
        return;
    }

    // Classe A = bleue, Classe B = orange
    // const shipColor = ship.classe === 'A' ? '#1E90FF' : '#FF9800' ; // ✅ Utilise 'classe' au lieu de 'class'

    // shipIconFactory.js
    function getShipIcon(ship) {
      const mmsi = nettoyerMmsi(ship?.mmsi);
      const classe = ship?.classe || 'A';
      const cog = ship?.cog || 0;

      const couleur = getShipColor(mmsi, classe);
      const forme = getShipShape(mmsi);
      const tooltip = getShipTooltip(ship);

      return L.divIcon({
        html: `<div class="ship-icon" style="transform: rotate(${cog}deg);" title="${tooltip}">
                 <svg viewBox="0 0 100 100" style="width: 24px; height: 24px;">
                   ${forme(couleur)}
                 </svg>
               </div>`,
        className: 'ship-marker',
        iconSize: [12, 12],
        iconAnchor: [6, 6]
      });
    }

    function nettoyerMmsi(valeur) {
      return String(valeur).replace(/\D+/g, '');
    }

    function getShipColor(mmsi, classe) {
      const first = mmsi.toString()[0]; // premier chiffre du MMSI

      // MMSI commençant par 8 → priorité : vert
      if (first === '8') return '#00FF00'; // vert

      // MMSI commençant par 0
      if (first === '0') return '#FFD700'; // jaune

      // MMSI commençant par 1
      if (first === '1') return '#9E9E9E'; // gris

      // MMSI commençant par 9
      if (first === '9') return '#000000'; // noir

      // MMSI commençant par 2 à 7
      if (['2','3','4','5','6','7'].includes(first)) {
        return classe === 'A' ? '#FF0000' : '#0000FF'; // bleu (A) ou rouge (B)
      }

      // Par défaut
      return '#000000';
    }


    function getShipShape(mmsi) {
        const first = mmsi.toString()[0];
         if (['2','3','4','5','6','7'].includes(first)) {
            return (color) => `<path fill="${color}" stroke="white" stroke-width="2"
                             d="M50,10 L80,80 L50,65 L20,80 Z"/>`;
          }
          if (first === '0') {
            return (color) => `<polygon points="50,20 80,50 50,80 20,50" fill="${color}" stroke="white" stroke-width="2"/>`;
          }
          return (color) => `<path fill="${color}" stroke="white" stroke-width="2"
                             d="M50,10 L80,80 L50,65 L20,80 Z"/>`;
    }

    function getShipTooltip(ship) {
      const name = ship?.name || 'Inconnu';
      const mmsi = nettoyerMmsi(ship?.mmsi);
      const classe = ship?.classe || 'A';
      return `Nom: ${name}\nMMSI: ${mmsi}\nClasse: ${classe}`;
    }

    const sog = parseFloat(ship.sog) || 0;
    const cog = parseFloat(ship.cog) || 0;
    const distanceInNauticalMiles = sog * AppState.projectionHours;
    const distanceInDegrees = nauticalMilesToDegrees(distanceInNauticalMiles);
    const headingRad = (cog * Math.PI) / 180;
    const endLat = lat + distanceInDegrees * Math.cos(headingRad);
    const endLon = lon + distanceInDegrees * Math.sin(headingRad);

    // Mise à jour de la ligne de vitesse
    if (AppData.sogLines[ship.mmsi]) {
        AppData.sogLines[ship.mmsi].setLatLngs([
            [lat, lon],
            [endLat, endLon]
        ]);
    } else {
        AppData.sogLines[ship.mmsi] = L.polyline(
            [[lat, lon], [endLat, endLon]],
            {
                color: '#FF0000',
                weight: 2,
                opacity: 0.8,
                dashArray: '5, 5'
            }
        );

        // N'ajouter à la carte que si AIS est visible
        if (aisVisible) {
            AppData.sogLines[ship.mmsi].addTo(map);
        }
    }

    const formatValue = v => (v > 0 ? v : '__');

    const sizeLigne = `Longueur=${formatValue(ship.long)} Largeur=${formatValue(ship.large)}<br>`;

    const projectionMinutes = Math.round(AppState.projectionHours * 60); // number
    let projectionLigne;
    if (projectionMinutes > 0) {
        projectionLigne = `Distance projetée: ${distanceInNauticalMiles.toFixed(1)} NM sur ${projectionMinutes} min<br>`;
    } else {
        projectionLigne = `Distance projetée: __`;
    }

    const popupContent = `
        <strong>${ship.name || 'Navire inconnu'}</strong><br>
        <strong>Navire AIS Classe ${ship.classe}</strong><br>
        MMSI: ${ship.mmsi}<br>
        Position: ${lat.toFixed(5)}, ${lon.toFixed(5)}<br>
        Cap: ${cog}°<br>
        Vitesse: ${sog.toFixed(1)} nœuds<br>
        Distance: ${ship.distance || 'N/A'}<br>
        ${sizeLigne}
        ${projectionLigne}
    `;

    const icon = getShipIcon(ship); // ← génère l'icône adaptée (forme, couleur, rotation)

   if (AppData.aisMarkers[ship.mmsi]) {
        AppData.aisMarkers[ship.mmsi].setLatLng([lat, lon]);
        AppData.aisMarkers[ship.mmsi].setIcon(icon);
        AppData.aisMarkers[ship.mmsi].getPopup().setContent(popupContent);

        // S'assurer que le marqueur est bien sur la carte seulement si AIS visible
        if (aisVisible && !map.hasLayer(AppData.aisMarkers[ship.mmsi])) {
            console.log(`Rajout du marqueur ${ship.mmsi} sur la carte`);
            AppData.aisMarkers[ship.mmsi].addTo(map);
        }
    } else {
        console.log(`Création nouveau marqueur pour ${ship.mmsi} à [${lat}, ${lon}]`);
        AppData.aisMarkers[ship.mmsi] = L.marker([lat, lon], {
            icon: icon
        });
        AppData.aisMarkers[ship.mmsi].bindPopup(popupContent);

        // N'ajouter à la carte que si AIS est visible
        if (aisVisible) {
            AppData.aisMarkers[ship.mmsi].addTo(map);
        }
    }
}

const updateAISData = async () => {
    try {
        const response = await fetch('/api/ais_ships');  // ✅ Utilise la nouvelle route avec distance
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Données AIS reçues:', data);

        if (data.success && Array.isArray(data.ships)) {
            data.ships.forEach(ship => {
                if (ship && ship.mmsi) {
                    updateAISMarker(ship);
                }
            });
            console.log(`✅ ${data.ships.length} navires AIS traités`);
        } else {
            console.warn('❌ Format de données AIS invalide:', data);
        }
    } catch (error) {
        console.error('Erreur lors de la récupération des données AIS:', error);
    }
}

// ==============================================
// 8. FONCTIONS DE GESTION DE LA TABLE DES NAVIRES AIS
// ==============================================
// Variables globales pour MMSI
let mmsiModal = null;
let mmsiData = [];

// Fonction pour ouvrir/fermer le modal MMSI
const toggleMMSITable = () => {
    mmsiModal = document.getElementById('mmsiModal');
    if (mmsiModal.style.display === 'none') {
        showMMSITable();
    } else {
        closeMMSIModal();
    }
};

const showMMSITable = () => {
    mmsiModal = document.getElementById('mmsiModal');
    mmsiModal.style.display = 'flex';
    refreshMMSIData();
};

const closeMMSIModal = () => {
    mmsiModal = document.getElementById('mmsiModal');
    mmsiModal.style.display = 'none';
};

// Fonction pour récupérer et afficher les données MMSI
const refreshMMSIData = async () => {
    try {
        const response = await fetch('/api/ais_ships');
        const data = await response.json();

        if (data.success) {
            mmsiData = data.ships;
            updateMMSITable();
            document.getElementById('mmsiCount').textContent = data.total;
        } else {
            console.error('Erreur lors de la récupération des données MMSI:', data.error);
            showNotification('Erreur lors de la récupération des données MMSI', 'error');
        }
    } catch (error) {
        console.error('Erreur réseau:', error);
        showNotification('Erreur de communication avec le serveur', 'error');
    }
}

// Fonction pour mettre à jour le tableau
const updateMMSITable = () => {
    const tbody = document.getElementById('mmsiTableBody');
    tbody.innerHTML = '';

    if (mmsiData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="11" style="text-align: center; padding: 30px; color: #666; font-style: italic;">
                    <div>
                        <img src="./static/icone/bateau.png" alt="Aucun navire" width="32" height="32" style="opacity: 0.3; margin-bottom: 10px;"><br>
                        <strong>Aucun navire AIS détecté</strong><br>
                        <small>En attente de réception des signaux MMSI...</small>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    // ✅ TRI DES DONNÉES PAR DISTANCE (du plus petit au plus grand)
    const sortedMmsiData = [...mmsiData].sort((a, b) => {
        // Fonction pour extraire la valeur numérique de la distance
        const getDistanceValue = (distance) => {
            if (distance === 'N/A' || !distance) return Infinity; // Les N/A en dernier

            // Extraire la partie numérique de "2.5 NM" → 2.5
            const match = distance.toString().match(/^([0-9]*\.?[0-9]+)/);
            return match ? parseFloat(match[1]) : Infinity;
        };

        const distanceA = getDistanceValue(a.distance);
        const distanceB = getDistanceValue(b.distance);

        return distanceA - distanceB; // Tri croissant (plus petit au plus grand)
    });

    // Utiliser les données triées au lieu de mmsiData
    sortedMmsiData.forEach((ship, index) => {
        const row = document.createElement('tr');
        row.style.backgroundColor = index % 2 === 0 ? '#f9f9f9' : 'white';

        // Vérifier si la position est valide
        const hasValidPosition = ship.latitude !== 'N/A' && ship.longitude !== 'N/A' &&
                                ship.latitude && ship.longitude &&
                                !isNaN(parseFloat(ship.latitude)) && !isNaN(parseFloat(ship.longitude));

        row.innerHTML = `
            <td style="font-family: monospace; font-weight: bold;">${ship.mmsi}</td>
            <td style="max-width: 120px; overflow: hidden; text-overflow: ellipsis;" title="${safeText(ship.name)}">${safeText(ship.name)}</td>
            <td style="text-align: center;">
                <span class="class-badge ${ship.classe === 'A' ? 'class-a' : 'class-b'}">
                    ${ship.classe}
                </span>
            </td>
            <td style="font-family: monospace; font-size: 11px;">${formatCoordinate(ship.latitude, 'lat')}</td>
            <td style="font-family: monospace; font-size: 11px;">${formatCoordinate(ship.longitude, 'lon')}</td>
            <td style="text-align: right;">${formatValue(ship.cog, '°')}</td>
            <td style="text-align: right;">${formatValue(ship.sog, ' nœuds')}</td>
            <td style="text-align: right;">${formatValue(ship.long, ' m')}</td>
            <td style="text-align: right;">${formatValue(ship.large, ' m')}</td>
            <td style="text-align: right; font-weight: bold; color: ${getDistanceColor(ship.distance)};">${safeText(ship.distance)}</td>
            <td style="text-align: center; white-space: nowrap;">
                <div style="display: flex; gap: 2px; justify-content: center;">
                    ${hasValidPosition ? `
                        <button onclick="centerOnShip('${ship.mmsi}', ${ship.latitude}, ${ship.longitude})" 
                                class="action-button btn-locate"
                                title="Centrer la carte sur ce navire">
                            📍
                        </button>
                        <button onclick="trackShip('${ship.mmsi}', ${JSON.stringify(safeText(ship.name))})" 
                                class="action-button btn-track"
                                title="Suivre ce navire">
                            👁️
                        </button>
                    ` : `
                        <span style="color: #999; font-size: 10px;" title="Position non disponible">❌</span>
                    `}
                    <button onclick="showShipDetails('${ship.mmsi}')" 
                            class="action-button btn-info"
                            title="Afficher les détails">
                        ℹ️
                    </button>
                    <button onclick="removeShip('${ship.mmsi}')" 
                            class="action-button btn-delete"
                            title="Supprimer de la liste">
                        🗑️
                    </button>
                </div>
            </td>
        `;

        tbody.appendChild(row);
    });
}

// ✅ Fonction pour colorer les distances selon la proximité
const getDistanceColor = (distance) => {
    if (distance === 'N/A' || !distance) return '#999';

    const match = distance.toString().match(/^([0-9]*\.?[0-9]+)/);
    if (!match) return '#333';

    const value = parseFloat(match[1]);

    if (value < 1) return '#f44336';      // Rouge-très proche (< 1 NM)
    if (value < 3) return '#FF9800';      // Orange-proche (1-3 NM)
    if (value < 10) return '#4CAF50';     // Vert-distance modérée (3-10 NM)
    return '#2196F3';                     // Bleu-loin (> 10 NM)
};

// ✅ Fonction utilitaire pour formater la distance avec icône
const formatDistanceWithIcon = (distance) => {
    if (distance === 'N/A' || !distance) return '❓ N/A';

    const match = distance.toString().match(/^([0-9]*\.?[0-9]+)/);
    if (!match) return distance;

    const value = parseFloat(match[1]);

    if (value < 1) return `🔴 ${distance}`;      // Rouge-très proche
    if (value < 3) return `$ffff00 {distance}`;      // Orange-proche
    if (value < 10) return `🟢 ${distance}`;     // Vert-distance modérée
    return `🔵 ${distance}`;                     // Bleu-loin
};


// Fonctions utilitaires
const safeText = (v) => {
    if (v === undefined || v === null) return '';
    const s = String(v).trim();
    if (s.toLowerCase() === 'n/a' || s.toLowerCase() === 'null') return '';
    return s;
};
const formatCoordinate = (value, type) => {
    if (value === 'N/A' || value === undefined || value === null || value === '') return '';
    const coord = parseFloat(value);
    if (isNaN(coord)) return '';

    const abs = Math.abs(coord);
    const deg = Math.floor(abs);
    const min = ((abs - deg) * 60).toFixed(3);
    const dir = type === 'lat' ? (coord >= 0 ? 'N' : 'S') : (coord >= 0 ? 'E' : 'W');
    return `${deg}°${min}'${dir}`;
};

const formatValue = (value, unit) => {
    if (value === 'N/A' || value === undefined || value === null || value === '') return '';
    const num = parseFloat(value);
    if (isNaN(num)) return '';
    return num.toFixed(1) + unit;
};

const formatMeters = (value) => {
    if (value === 'N/A' || value === undefined || value === null) return 'N/A';
    const num = parseFloat(value);
    if (isNaN(num)) return 'N/A';
    return num.toFixed(1) + ' m';
};

window.centerOnShip = (mmsi, lat, lon) => {
    if (lat !== 'N/A' && lon !== 'N/A') {
        const latitude = parseFloat(lat);
        const longitude = parseFloat(lon);
        if (!isNaN(latitude) && !isNaN(longitude)) {
            map.setView([latitude, longitude], 12);
            showNotification(`Centrage sur le navire ${mmsi}`, 'success');
        }
    } else {
        showNotification('Position non disponible pour ce navire', 'warning');
    }
};

window.trackShip = (mmsi, name) => {
    // Activer le suivi du navire (à implémenter selon vos besoins)
    showNotification(`Suivi activé pour ${name || mmsi}`, 'info');

    // Vous pouvez implémenter
    // – Suivi automatique sur la carte.
    // – Alerte si le navire sort d'une zone.
    // – Historique de trajectoire.
    console.log(`Début du suivi du navire ${mmsi}`);
};

let shipDetailsWindow = null;

window.showShipDetails = (mmsi) => {
    const ship = mmsiData.find(s => s.mmsi === mmsi);
    if (!ship) return;

    // Fermer la fenêtre existante si elle est ouverte
    if (shipDetailsWindow) {
        shipDetailsWindow.remove();
    }

    // Créer une fenêtre flottante non-modale
    shipDetailsWindow = document.createElement('div');
    shipDetailsWindow.id = 'shipDetailsWindow';
    shipDetailsWindow.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        width: 350px;
        background: white;
        border: 2px solid #1e88e5;
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        z-index: 1500;
        font-family: Arial, sans-serif;
        resize: both;
        overflow: auto;
        min-width: 300px;
        min-height: 200px;
        max-width: 500px;
        max-height: 600px;
    `;

    shipDetailsWindow.innerHTML = `
        <div id="shipDetailsHeader" style="
            background: linear-gradient(135deg, #1e88e5, #1565c0);
            color: white;
            padding: 12px 15px;
            cursor: move;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-radius: 6px 6px 0 0;
            user-select: none;
        ">
            <h3 style="margin: 0; font-size: 14px;">
                📡 Détails du navire ${ship.mmsi}
            </h3>
            <button onclick="closeShipDetailsWindow()" style="
                background: rgba(255,255,255,0.2);
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
            ">
                ✕
            </button>
        </div>
        
        <div style="padding: 15px; max-height: 500px; overflow-y: auto;">
            <div style="display: grid; gap: 12px;">ESW
                
                <!-- Informations principales -->
                <div style="background: #f8f9fa; padding: 12px; border-radius: 6px; border-left: 4px solid #1e88e5;">
                    <h4 style="margin: 0 0 8px 0; color: #1e88e5; font-size: 13px;">🚢 IDENTIFICATION</h4>
                    <div style="display: grid; gap: 6px; font-size: 12px;">
                        <div><strong>MMSI:</strong> <span style="font-family: monospace;">${ship.mmsi}</span></div>
                        <div><strong>Nom:</strong> ${ship.name || 'Non disponible'}</div>
                        <div><strong>Classe AIS:</strong> 
                            <span style="background: ${ship.classe === 'A' ? '#FF0000' : '#0000FF'}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">
                                ${ship.classe}
                            </span>
                        </div>
                    </div>
                </div>

                <!-- Position -->
                <div style="background: #f0f8ff; padding: 12px; border-radius: 6px; border-left: 4px solid #2196f3;">
                    <h4 style="margin: 0 0 8px 0; color: #2196f3; font-size: 13px;">📍 POSITION</h4>
                    <div style="display: grid; gap: 6px; font-size: 12px;">
                        <div><strong>Latitude:</strong> <span style="font-family: monospace;">${formatCoordinate(ship.latitude, 'lat')}</span></div>
                        <div><strong>Longitude:</strong> <span style="font-family: monospace;">${formatCoordinate(ship.longitude, 'lon')}</span></div>
                        <div><strong>Distance:</strong> ${ship.distance || 'N/A'}</div>
                    </div>
                </div>

                <!-- Navigation -->
                <div style="background: #fff3e0; padding: 12px; border-radius: 6px; border-left: 4px solid #ff9800;">
                    <h4 style="margin: 0 0 8px 0; color: #ff9800; font-size: 13px;">🧭 NAVIGATION</h4>
                    <div style="display: grid; gap: 6px; font-size: 12px;">
                        <div><strong>Cap (COG):</strong> ${formatValue(ship.cog, '°')}</div>
                        <div><strong>Vitesse (SOG):</strong> ${formatValue(ship.sog, ' nœuds')}</div>
                    </div>
                </div>

                <!-- Actions -->
                <div style="display: flex; gap: 8px; margin-top: 10px;">
                    ${ship.latitude !== 'N/A' && ship.longitude !== 'N/A' ? `
                        <button onclick="centerOnShip('${ship.mmsi}', ${ship.latitude}, ${ship.longitude}); closeShipDetailsWindow();" style="
                            background: #1e88e5; color: white; border: none; padding: 8px 12px; 
                            border-radius: 4px; cursor: pointer; font-size: 11px; flex: 1;
                        ">
                            📍 Centrer sur carte
                        </button>
                        <button onclick="trackShip('${ship.mmsi}', '${ship.name}');" style="
                            background: #FF9800; color: white; border: none; padding: 8px 12px; 
                            border-radius: 4px; cursor: pointer; font-size: 11px; flex: 1;
                        ">
                            👁️ Suivre
                        </button>
                    ` : ''}
                </div>

                <!-- Informations techniques -->
                <div style="background: #ecf3d3; padding: 12px; border-radius: 6px; border-left: 4px solid #9db44b;">
                    <h4 style="margin: 0 0 8px 0; color: #228B22; font-size: 13px;">📏 DIMENSIONS</h4>
                    <div style="display: grid; gap: 6px; font-size: 12px;">
                        <div><strong>Longueur:</strong> ${formatMeters(ship.long)}</div>
                        <div><strong>Largeur:</strong> ${formatMeters(ship.large)}</div>
                        <div style="text-align: center";font-size: 10px; color: #666;;><strong>Dernière mise à jour:</strong> ${ship.last_update || 
                                                                new Date().toLocaleTimeString('fr-FR')}</div>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(shipDetailsWindow);

    // Rendre la fenêtre déplaçable
    makeDraggable(shipDetailsWindow);

    console.log(`Fenêtre de détails ouverte pour le navire ${ship.mmsi}`);
}

// Fonction pour fermer la fenêtre de détails
window.closeShipDetailsWindow = () =>  {
    if (shipDetailsWindow) {
        shipDetailsWindow.remove();
        shipDetailsWindow = null;
        console.log('Fenêtre de détails fermée');
    }
};

// Fonction pour rendre la fenêtre déplaçable
const makeDraggable = (element) => {
    let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
    const header = element.querySelector('#shipDetailsHeader');

    if (header) {
        header.onmousedown = dragMouseDown;
    }

    const dragMouseDown = (e) => {
        e = e || window.event;
        e.preventDefault();
        pos3 = e.clientX;
        pos4 = e.clientY;
        document.onmouseup = closeDragElement;
        document.onmousemove = elementDrag;
        header.style.cursor = 'grabbing';
    };

    const elementDrag = (e) => {
        e = e || window.event;
        e.preventDefault();
        pos1 = pos3 - e.clientX;
        pos2 = pos4 - e.clientY;
        pos3 = e.clientX;
        pos4 = e.clientY;

        let newTop = element.offsetTop - pos2;
        let newLeft = element.offsetLeft - pos1;

        // Empêcher la fenêtre de sortir de l'écran
        newTop = Math.max(0, Math.min(newTop, window.innerHeight - 50));
        newLeft = Math.max(0, Math.min(newLeft, window.innerWidth - 100));

        element.style.top = newTop + "px";
        element.style.left = newLeft + "px";
    };

    const closeDragElement = () => {
        document.onmouseup = null;
        document.onmousemove = null;
        header.style.cursor = 'move';
    };
};

window.removeShip = (mmsi) => {
    if (confirm(`Voulez-vous supprimer le navire ${mmsi} de la liste ?\n(Il réapparaîtra s'il émet encore des signaux)`)) {
        // Appeler l'API pour supprimer temporairement
        fetch(`/api/ais_ships/${mmsi}`, { method: 'DELETE' })
            .then(() => {
                showNotification(`Navire ${mmsi} supprimé`, 'success');
                refreshMMSIData();
            })
            .catch(err => {
                console.error('Erreur lors de la suppression:', err);
                showNotification('Erreur lors de la suppression', 'error');
            });
    }
}

// Remplacer aussi la fonction showCustomModal par une version non-modale si vous le souhaitez
const showCustomModal = (title, content) => {
    // Utiliser la même approche que showShipDetails pour d'autres fenêtres
    console.log('Affichage non-modal de:', title);

    // Vous pouvez créer une version similaire à showShipDetails
    // mais plus générique pour d'autres types de contenu
}


// Actualisation automatique toutes les 30 secondes si le modal est ouvert
setInterval(() => {
    if (mmsiModal && mmsiModal.style.display === 'flex') {
        refreshMMSIData();
    }
}, 30000);


// ==============================================
// 9. OUTIL DE MESURE DE DISTANCE
// ==============================================
const measureTool = {
    mode: false,
    points: [],
    lines: [],
    markers: [],
    labels: [],
    waypoints: [],  // Noms personnalisés pour chaque point
    control: null,
    map: null,
    firstPointOnBoat: false,
    lastPointOnBoat: false,
    boatPosition: null,
    domClickHandler: null,
    keyPressHandler: null,
    isLoadedRoute: false,
    isEditingLoadedRoute: false,  // Flag pour indiquer qu'on édite une route chargée (insertion/drag autorisés, mais pas ajout libre)
    isModifWaypoint: false,    // Flag pour éviter l'ajout lors de la modification du nom du waypoint
    cpt : 0,                    // Compteur pour faire un front montant sur les modifications de waypoint.

    init: function(map) {
        console.log("Init measureTool appelé");
        if (!map) {
            console.error("La carte n'est pas définie");
            return;
        }
        this.map = map;
        console.log("Carte assignée au measureTool:", this.map);
        this.addControl();
    },

    addControl: function() {
        console.log("AddControl appelé");
        const self = this;
        this.control = L.control({
            position: 'topleft'
        });

        this.control.onAdd = function(map) {
            const div = L.DomUtil.create('div', 'measure-button-container');

            div.innerHTML = `
                <a href="#" id="distanceMeasureButton" class="measure-button" title="Etablir les distances d'une route.">
                    <img src="./static/icone/mesure.png" alt="Mesure" width="16" height="16">
                </a>
                <a href="#" id="toggle-labels" class="measure-button" title="Masquer les étiquettes de distance.">
                    <img src="./static/icone/distance.png" alt="Mesure" width="16" height="16">
                </a>
                <a href="#" id="saveRouteButton" class="measure-button" title="Sauvegarder la route" >
                    <img src="./static/icone/enregistrer.png" alt="Sauvegarder" width="16" height="16">
                </a>
                <a href="#" id="downloadRouteButton" class="measure-button" title="Télécharger la route en JSON" >
                    <img src="./static/icone/telecharge.png" alt="Télécharger" width="16" height="16">
                </a>
                <a href="#" id="loadRouteButton" class="measure-button" title="Charger une route">
                    <img src="./static/icone/charger.png" alt="Charger" width="25" height="25">
                </a>`;


            L.DomEvent.disableClickPropagation(div);
            L.DomEvent.disableScrollPropagation(div);

            // Bouton principal de mesure
            const button = div.querySelector('#distanceMeasureButton');
            if (button) {
                L.DomEvent.on(button, 'click', function(e) {
                    L.DomEvent.stop(e);
                    self.toggle();
                });
            }

            // Bouton de sauvegarde
            const saveButton = div.querySelector('#saveRouteButton');
            if (saveButton) {
                L.DomEvent.on(saveButton, 'click', function(e) {
                    L.DomEvent.stop(e);
                    self.saveRoute();
                });
            }

            // Bouton de téléchargement
            const downloadButton = div.querySelector('#downloadRouteButton');
            if (downloadButton) {
                L.DomEvent.on(downloadButton, 'click', function(e) {
                    L.DomEvent.stop(e);
                    self.downloadRoute();
                });
            }

            // Bouton de chargement
            const loadButton = div.querySelector('#loadRouteButton');
            if (loadButton) {
                L.DomEvent.on(loadButton, 'click', function(e) {
                    L.DomEvent.stop(e);
                    self.loadRoute();
                });
            }

            return div;
        };

        try {
            this.control.addTo(this.map);
            console.log("Control ajouté à la carte avec succès");
        } catch (error) {
            console.error("Erreur lors de l'ajout du control:", error);
        }
    },

   isClickOnUIElement: function(target) {
        const uiSelectors = [
            '.leaflet-control',
            '.legend',
            'button',
            'input',
            'select',
            '.toggle-menu',
            '.center-button',
            //'.toggle-info-button',
            '.action-btn',
            '#fileModal',
            '.leaflet-popup'
        ];

        let element = target;
        while (element && element !== document.body) {
            for (let selector of uiSelectors) {
                if (element.matches && element.matches(selector)) {
                    return true;
                }
            }
            element = element.parentElement;
        }
        return false;
    },

    handleMapClick: function(e) {
        if (!this.mode) return;

        // Empêcher le mode mesure si un drag est en cours
        if (AppState.isDragging) {
            console.log("Drag détecté, clic ignoré");
            return;
        }

        // En mode lecture seule, ne pas intercepter les clics
        if (this.isLoadedRoute) {
            console.log("Mode lecture seule, clic non intercepté");
            return;
        }

        // Si on est en modification du waypoint, on sort.
        if (this.isModifWaypoint) {
            this.isModifWaypoint=false
            return;
        }

        // En mode édition d'une route chargée, empêcher l'ajout libre de points
        if (this.isEditingLoadedRoute) {
            console.log("Mode édition route chargée - Ajout libre de points désactivé (utilisez les lignes pour insérer)");
            showMessage('Pour ajouter des points, cliquez sur une ligne rouge', 'info', false);
            //return; // On peut ajouter des points librement
        }

        console.log("Clic sur la carte en mode mesure");

        // Avec map.on('click'), e.latlng contient directement la position
        const point = e.latlng;

        console.log("Position cliquée:", point);
        this.addMeasurePoint(point);
    },

    addMeasurePoint: function(clickedPoint) {
        console.log("=== AJOUT POINT DE MESURE ===");
        console.log("Position cliquée:", clickedPoint);

        // Bloquer l'ajout de points si c'est une route chargée (sans message)
        if (this.isLoadedRoute) {
            console.log("❌ Ajout de point interdit : route chargée en mode lecture seule");
            return;
        }

        // Faire un front montant si on est en modification du waypoint
        if (this.isModifWaypoint && this.cpt>=1) {
            this.isModifWaypoint=false;
            this.cpt=0;
        }

        // Si on est en modification du waypoint, on sort.
        if (this.isModifWaypoint) {
            this.cpt += 1;
            return;
        }

        const currentBoatPosition = this.getCurrentBoatPosition();
        let isThisPointOnBoat = false;
        let actualPoint = clickedPoint;

        // Vérifier si le clic est proche du bateau
        if (currentBoatPosition) {
            const distanceToBoat = clickedPoint.distanceTo(currentBoatPosition);
            console.log("Distance au bateau:", distanceToBoat, "mètres");

            if (distanceToBoat <= 100) {
                isThisPointOnBoat = true;
                actualPoint = currentBoatPosition;
                console.log("✅ POINT ACCROCHÉ AU BATEAU");
            }
        }

        if (this.points.length === 0) {
            // Premier point
            this.boatPosition = currentBoatPosition;

            if (isThisPointOnBoat) {
                this.firstPointOnBoat = true;
                this.points.push(actualPoint);
                // Afficher un message temporaire
                showMessage(`Premier point accroché au bateau`, 'success', false);
            } else {
                this.firstPointOnBoat = false;
                this.points.push(actualPoint);
                // Pas de message, le message permanent "Mode mesure ACTIVÉ" reste affiché
            }
        } else {
            // Points suivants (y compris le dernier)
            if (this.lastPointOnBoat) {
                // Interdire l'ajout de nouveaux points si le dernier est déjà accroché au bateau
                console.log("❌ Ajout de point interdit : le dernier point est déjà accroché au bateau");
                showMessage(`Impossible d'ajouter un point : la route est terminée (vous pouvez appuyer sur 'Echappe')`, 'error', false);
                return;
            } else if (isThisPointOnBoat && !this.firstPointOnBoat) {
                // Accrocher le dernier point au bateau uniquement si le premier n'est pas accroché
                this.lastPointOnBoat = true;
                this.points.push(actualPoint);
                console.log("✅ DERNIER POINT ACCROCHÉ AU BATEAU - Route inversée");
            } else if (isThisPointOnBoat && this.firstPointOnBoat) {
                // Si le premier point est déjà accroché, ne pas accrocher le dernier
                this.lastPointOnBoat = false;
                this.points.push(clickedPoint);
                // Pas de message, le message "Distance totale" sera affiché par updateDistances()
            } else {
                this.lastPointOnBoat = false;
                this.points.push(actualPoint);
                // Pas de message, le message "Distance totale" sera affiché par updateDistances()
            }
        }

        const markerPosition = this.points[this.points.length - 1];
        const pointIndex = this.points.length - 1;

        // Ajouter un nom par défaut pour ce waypoint
        this.waypoints.push(`Point ${pointIndex + 1}`);

        // Couleur différente pour les points accrochés au bateau
        const isFirstAndAttached = (this.points.length === 1 && this.firstPointOnBoat);
        const isLastAndAttached = (this.points.length > 1 && this.lastPointOnBoat &&
                                   this.points.length === this.markers.length + 1);

        // Créer un marqueur draggable sauf s'il est accroché au bateau
        const isDraggable = !isFirstAndAttached && !isLastAndAttached;

        const marker = L.marker(markerPosition, {
            icon: pinIcon,
            interactive: true,
            draggable: isDraggable
        }).addTo(this.map);

        if (isFirstAndAttached || isLastAndAttached) {
            marker.setIcon(L.divIcon({
                className: 'boat-attached-marker',
                html: '<div style="background: #ff4444; border: 2px solid #ffffff; border-radius: 50%; width: 14px; height: 14px; cursor: grab;"></div>',
                iconSize: [14, 14],
                iconAnchor: [7, 7]
            }));
            console.log("✅ Marqueur rouge créé pour le point accroché (non draggable)");
        } else {
            // Ajouter le tooltip pour indiquer que le point est draggable
            marker.bindTooltip(`Point ${pointIndex + 1} - Cliquez pour déplacer ou cliquez à droite`, {
                permanent: false,
                direction: 'top'
            });
        }

        // Gestionnaire de drag pour mettre à jour la position
        if (isDraggable) {
            marker.on('dragstart', () => {
                console.log(`Début du drag du point ${pointIndex + 1}`);
            });

            marker.on('drag', (e) => {
                // Mettre à jour la position dans le tableau
                const newLatLng = e.target.getLatLng();
                this.points[pointIndex] = newLatLng;

                // Recalculer les distances en temps réel
                this.updateDistances(this.lastPointOnBoat);
            });

            marker.on('dragend', (e) => {
                const newLatLng = e.target.getLatLng();
                this.points[pointIndex] = newLatLng;
                console.log(`Point ${pointIndex + 1} déplacé vers:`, newLatLng);

                // Recalculer les distances après le drag
                this.updateDistances(this.lastPointOnBoat);

                // Afficher un message de confirmation
                const isRouteCompleted = this.lastPointOnBoat;
                if (!isRouteCompleted) {
                    showMessage(`Point ${pointIndex + 1} déplacé avec succès`, 'success', false);
                }
            });

            // Menu contextuel (clic droit) pour renommer ou supprimer le point
            marker.on('contextmenu', (e) => {
                L.DomEvent.stopPropagation(e);
                const markerIndex = this.markers.indexOf(marker);
                const waypointName = this.waypoints[markerIndex] || `Point ${markerIndex + 1}`;

                // Créer un popup personnalisé avec boutons de renommage et suppression
                const contextMenu = `
                    <div style="padding: 10px; text-align: center;">
                        <strong>${waypointName}</strong><br>
                        <button onclick="measureTool.renamePointAtIndex(${markerIndex}); return false;"
                                style="margin-top: 8px; padding: 8px 16px; background: #4CAF50; color: white;
                                       border: none; border-radius: 4px; cursor: pointer; font-size: 14px; margin-right: 5px;">
                            ✏️ Renommer
                        </button>
                        <button onclick="measureTool.deletePointAtIndex(${markerIndex}); return false;"
                                style="margin-top: 8px; padding: 8px 16px; background: #ff4444; color: white;
                                       border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">
                            🗑️ Supprimer
                        </button>
                    </div>
                `;

                marker.bindPopup(contextMenu).openPopup();
            });
        }

        this.markers.push(marker);
        console.log("Marqueur créé à la position:", markerPosition);

        // Vérifier si c'est une route inversée qui vient d'être complétée
        const isRouteCompleted = (this.lastPointOnBoat && isLastAndAttached);

        if (this.points.length > 1) {
            // Passer un flag à updateDistances pour ne pas afficher de message si route complétée
            this.updateDistances(isRouteCompleted);
        }

        // Si c'est une route inversée qui vient d'être complétée, afficher le message final
        if (isRouteCompleted) {
            this.showInvertedRouteMessage();
        }
    },

    getCurrentBoatPosition: function() {
        console.log("Recherche position du bateau...");

        // Priorité 1: AppState.shipMarker
        if (AppState && AppState.shipMarker) {
            const pos = AppState.shipMarker.getLatLng();
            console.log("Position trouvée via AppState.shipMarker:", pos);
            return pos;
        }

        // Priorité 2 : Cordonnées globales
        if (window.coordinates && window.coordinates.latitude && window.coordinates.longitude) {
            const pos = L.latLng(window.coordinates.latitude, window.coordinates.longitude);
            console.log("Position trouvée via window.coordinates:", pos);
            return pos;
        }

        console.log("❌ Position du bateau non trouvée");
        return null;
    },

    getCurrentBoatSpeed: function() {
        // Priorité 1 : Récupérer depuis les données globales mises à jour par updatePosition()
        if (window.coordinates && window.coordinates.hasOwnProperty('sog')) {
            const speed = parseFloat(window.coordinates.sog);
            console.log("Vitesse trouvée via window.coordinates:", speed, "nœuds");
            return speed;
        }

        // Priorité 2 : Récupérer depuis le dernier point d'historique (si enregistrement actif)
        if (AppData.positionHistory && AppData.positionHistory.length > 0) {
            const lastPoint = AppData.positionHistory[AppData.positionHistory.length - 1];
            if (lastPoint.hasOwnProperty('sog')) {
                const speed = parseFloat(lastPoint.sog) || 0;
                console.log("Vitesse trouvée via historique:", speed, "nœuds");
                return speed;
            }
        }

        console.log("❌ Vitesse réelle non trouvée");
        return null;
    },

    getDefaultCruisingSpeed: function() {
        // Récupérer la vitesse de croisière depuis la configuration du bateau
        if (window.coordinates && window.coordinates.boat_info && window.coordinates.boat_info.speed) {
            return parseFloat(window.coordinates.boat_info.speed);
        }

        // Valeur de fallback si la configuration n'est pas disponible
        return 6.0;  // Valeur par défaut correspondant à boat_config.json
    },


    formatTime: function(hours) {
        if (hours < 0.1) {
            return "< 6 min";
        }

        if (hours < 1) {
            const minutes = Math.round(hours * 60);
            return `${minutes} min`;
        }

        if (hours < 24) {
            const h = Math.floor(hours);
            const m = Math.round((hours - h) * 60);
            if (m === 0) {
                return `${h}h`;
            }
            return `${h}h${m.toString().padStart(2, '0')}`;
        }

        const days = Math.floor(hours / 24);
        const remainingHours = Math.floor(hours % 24);
        return `${days}j ${remainingHours}h`;
    },

    updateFirstPointPosition: function() {
        console.log("=== updateFirstPointPosition APPELÉE ===");
        console.log("firstPointOnBoat:", this.firstPointOnBoat);
        console.log("lastPointOnBoat:", this.lastPointOnBoat);
        console.log("points.length:", this.points.length);

        if ((!this.firstPointOnBoat && !this.lastPointOnBoat) || this.points.length === 0) {
            return;
        }

        const newBoatPosition = this.getCurrentBoatPosition();
        if (!newBoatPosition) {
            console.log("❌ Impossible de récupérer la nouvelle position du bateau");
            return;
        }

        let hasUpdated = false;

        // Mettre à jour le premier point si accroché au bateau
        if (this.firstPointOnBoat) {
            console.log("=== MISE À JOUR PREMIER POINT ===");
            const oldPosition = this.points[0];
            const displacement = oldPosition.distanceTo(newBoatPosition);
            console.log("Déplacement premier point:", displacement, "mètres");

            if (displacement > 0.1) {
                this.points[0] = newBoatPosition;

                if (this.markers[0]) {
                    this.markers[0].setLatLng(newBoatPosition);
                    console.log("✅ Marqueur du premier point mis à jour");
                }

                hasUpdated = true;
                console.log("✅ PREMIER POINT MIS À JOUR - Déplacement:", displacement.toFixed(1), "m");
            }
        }

        // Mettre à jour le dernier point si accroché au bateau
        if (this.lastPointOnBoat && this.points.length > 1) {
            console.log("=== MISE À JOUR DERNIER POINT ===");
            const lastIndex = this.points.length - 1;
            const oldPosition = this.points[lastIndex];
            const displacement = oldPosition.distanceTo(newBoatPosition);
            console.log("Déplacement dernier point:", displacement, "mètres");

            if (displacement > 0.1) {
                this.points[lastIndex] = newBoatPosition;

                if (this.markers[lastIndex]) {
                    this.markers[lastIndex].setLatLng(newBoatPosition);
                    console.log("✅ Marqueur du dernier point mis à jour");
                }

                hasUpdated = true;
                console.log("✅ DERNIER POINT MIS À JOUR - Déplacement:", displacement.toFixed(1), "m");
            }
        }

        // Recalculer les distances si au moins un point a été mis à jour
        if (hasUpdated && this.points.length > 1) {
            console.log("🔄 Re-calcul des distances...");
            // Si la route est complétée (dernier point accroché), ne pas afficher de message
            this.updateDistances(this.lastPointOnBoat);

            // Si le dernier point est accroché, mettre à jour le message permanent
            if (this.lastPointOnBoat) {
                this.showInvertedRouteMessage();
            }
        }
    },

    showInvertedRouteMessage: function() {
        // Supprimer le message temporaire s'il existe
        MessageUtils.clear();

        // Calculer la distance totale
        let totalDistance = 0;
        for (let i = 1; i < this.points.length; i++) {
            totalDistance += this.points[i-1].distanceTo(this.points[i]);
        }
        const totalDistanceNM = (totalDistance / 1852).toFixed(2);

        // Calculer le temps estimé
        const currentSpeed = this.getCurrentBoatSpeed();
        let speedToUse = (currentSpeed && currentSpeed > 0.5) ? currentSpeed : this.getDefaultCruisingSpeed();
        const timeHours = totalDistanceNM / speedToUse;
        const timeFormatted = this.formatTime(timeHours);

        const messageContent = `<img src="./static/icone/mesure.png" alt="Mesure" width="16" height="16">
            Votre départ a lieu inversé - Distance : ${totalDistanceNM} NM -
            <img src="./static/icone/minuteur.png" alt="Temps" width="16" height="16">
            Temps estimé : ${timeFormatted}`;

        // Créer ou mettre à jour le message permanent dédié avec le type success (vert)
        this.updatePermanentMessage(messageContent, 'info');
    },

    updatePermanentMessage: function(content, type = 'success') {
        // Chercher le message permanent existant ou le créer
        let permanentMsg = document.getElementById('measureToolPermanentMessage');

        // Définir les couleurs selon le type
        const colors = {
            success: { color: '#2e7d32', border: '2px solid #2e7d32' },
            info: { color: '#00008B', border: '2px solid #1e88e5' },
            error: { color: '#d32f2f', border: '2px solid #d32f2f' }
        };
        const style = colors[type] || colors.success;

        if (!permanentMsg) {
            // Créer le message permanent
            permanentMsg = document.createElement('div');
            permanentMsg.id = 'measureToolPermanentMessage';
            document.body.appendChild(permanentMsg);
        }

        // Appliquer les styles
        permanentMsg.style.cssText = `
            position: fixed;
            top: 10px;
            left: 50%;
            transform: translate(-50%, 0);
            background-color: white;
            padding: 20px 30px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            z-index: 2001;
            font-family: Arial, sans-serif;
            max-width: 80%;
            text-align: center;
            font-size: 16px;
            font-weight: bold;
            color: ${style.color};
            border: ${style.border};
        `;

        // Mettre à jour le contenu
        permanentMsg.innerHTML = content;
    },

    clearPermanentMessage: function() {
        const permanentMsg = document.getElementById('measureToolPermanentMessage');
        if (permanentMsg) {
            permanentMsg.remove();
        }
    },

    updateDistances: function(skipMessage = false) {
    console.log("=== MISE À JOUR DES DISTANCES ===");

    this.lines.forEach(line => this.map.removeLayer(line));
    this.labels.forEach(label => this.map.removeLayer(label));
    this.lines = [];
    this.labels = [];

    let totalDistance = 0;
    for (let i = 1; i < this.points.length; i++) {
        const distance = this.points[i-1].distanceTo(this.points[i]);
        const distanceNM = (distance / 1852).toFixed(2);
        totalDistance += distance;

        console.log(`Segment ${i-1} -> ${i}: ${distanceNM} NM (${distance.toFixed(1)}m)`);

        const line = L.polyline([
            this.points[i-1],
            this.points[i]
            ], {
                color: 'red',
                weight: 2,
                dashArray: '5, 5'
            }).addTo(this.map);

        // Ajouter un gestionnaire de clic sur la ligne pour insérer un point
        const segmentIndex = i - 1;

        line.on('click', (e) => {
            console.log(`🔵 Clic sur le segment ${segmentIndex} -> ${segmentIndex + 1}`);

            // Si c'est une route chargée, activer le mode édition (mais sans ajout libre de points)
            if (this.isLoadedRoute) {
                console.log("Route chargée détectée - Activation du mode édition");
                this.isLoadedRoute = false;
                this.isEditingLoadedRoute = true;  // Activer le mode édition spécial pour routes chargées
                showMessage('Mode édition activé - Cliquez sur les lignes pour insérer des points', 'info', false);
            }


            // Bloquer la propagation pour éviter que map.on('click') ne se déclenche
            L.DomEvent.stopPropagation(e);
            if (e.originalEvent) {
                e.originalEvent.stopPropagation();
            }

            // Récupérer la position du clic
            const clickedLatLng = e.latlng;

            // Insérer le nouveau point après le point de départ du segment
            this.insertPointAtIndex(segmentIndex + 1, clickedLatLng);
        });

        // Changer le curseur au survol de la ligne
        line.on('mouseover', () => {
            // Permettre le survol même pour les routes chargées
            line.setStyle({ weight: 5, opacity: 1, cursor: 'pointer' });
        });

        line.on('mouseout', () => {
            line.setStyle({ weight: 3, opacity: 0.8 });
        });

        this.lines.push(line);

        const midPoint = L.latLng(
            (this.points[i-1].lat + this.points[i].lat) / 2,
            (this.points[i-1].lng + this.points[i].lng) / 2
        );

        const p1 = this.map.project(this.points[i-1]);
        const p2 = this.map.project(this.points[i]);
        let angle = Math.atan2(p2.y - p1.y, p2.x - p1.x) * 180 / Math.PI;

        if (angle > 90 || angle < -90) {
            angle += 180;
        }

        const customElement = L.divIcon({
            className: 'custom-label',
            html: `<div class="distance-label" style="
                position: absolute;
                transform: translate(-50%, -100%) rotate(${angle}deg);
                background-color: rgba(255, 255, 255, 0.8);
                border: 1px solid red;
                border-radius: 3px;
                padding: 2px 4px;
                font-size: 11px;
                font-weight: bold;
                color: red;
                white-space: nowrap;
                pointer-events: none;
                box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                ${AppState.IsNoDisplay ? 'display: none;' : ''}
            ">${distanceNM} NM</div>`,
            iconSize: [1, 1],
            iconAnchor: [0, 0]
        });


        const label = L.marker(midPoint, {
            icon: customElement,
            interactive: false,
            clickable: false,
            keyboard: false
            }).addTo(this.map);

            this.labels.push(label);
        };


    const totalDistanceNM = (totalDistance / 1852).toFixed(2);

    // Calculer le temps estimé pour parcourir cette distance
    let statusText;
    if (this.firstPointOnBoat || this.lastPointOnBoat) {
        const currentSpeed = this.getCurrentBoatSpeed();
        let speedToUse = currentSpeed;
        let speedSource = "";

        // Si vitesse actuelle > 0.5 nœud, l'utiliser
        if (currentSpeed && currentSpeed > 0.5) {

            speedToUse = currentSpeed;
            speedSource = "vitesse actuelle";
        }
        // Sinon, utiliser une vitesse moyenne de référence (bateau à l'arrêt)
        else {
            speedToUse = this.getDefaultCruisingSpeed();

            speedSource = "vitesse de croisière estimée (bateau à l'arrêt)";
        }

        const timeHours = totalDistanceNM / speedToUse;
        const timeFormatted = this.formatTime(timeHours);

        // Déterminer quel point est accroché
        let attachmentInfo = "";
        if (this.firstPointOnBoat) {
            attachmentInfo = "premier point suit le bateau";
        } else if (this.lastPointOnBoat) {
            attachmentInfo = "dernier point suit le bateau";
        }

        statusText = `<img src="./static/icone/mesure.png" alt="Historique" width="16" height="16">
                &nbsp;Distance : ${totalDistanceNM} NM (${attachmentInfo}) -
                <img src="./static/icone/minuteur.png" alt="Historique" width="16" height="16">
                Temps estimé : ${timeFormatted} à ${speedToUse.toFixed(1)} nds (${speedSource})`;
    } else {
        // Pour un parcours fixe, utiliser aussi une estimation
        const defaultSpeed = this.getDefaultCruisingSpeed();
        const timeHours = totalDistanceNM / defaultSpeed;
        const timeFormatted = this.formatTime(timeHours);

        statusText = `<img src="./static/icone/mesure.png" alt="Historique" width="16" height="16">
            &nbsp;Distance totale : ${totalDistanceNM} NM -
            <img src="./static/icone/minuteur.png" alt="Historique" width="16" height="16">
            Temps : ${timeFormatted} à la vitesse de croisière définie à ${defaultSpeed.toFixed(1)} nds<br>
            Allez dans configuration du bateau pour modifier cette valeur.`;
    }

    console.log("Distance totale:", totalDistanceNM, "NM");

    // N'afficher le message que si on ne doit pas le sauter (route non complétée.)
    if (!skipMessage) {
        // Afficher le message dans le message permanent en haut de l'écran
        this.updatePermanentMessage(statusText, 'info');
    }
},

handleKeyPress: function(e) {
    if (!this.mode) return;

    const key = e.key.toLowerCase();

    // Échappe
    if (key === 'escape' || e.keyCode === 27) {
        console.log("Touche Échappe détectée");
        this.removeLastPoint();
        return;
    }

    // Ctrl + Z → Undo
    if ((e.ctrlKey || e.metaKey) && key === 'z') {
        console.log("Ctrl+Z détecté");
        this.removeLastPoint(); // ou ActionManager.undo()
        e.preventDefault();
        return;
    }

    // Ctrl + Y → Redo
    if ((e.ctrlKey || e.metaKey) && key === 'y') {
        console.log("Ctrl+Y détecté");
        this.redoLastPoint?.(); // ou ActionManager.redo()
        e.preventDefault();
        return;
    }
},
    redoLastPoint: function() {
        if (this.deletedPointsStack.length === 0) {
            console.log("Aucun point à restaurer");
            showMessage('Aucun point à restaurer', 'info', true);
            return;
        }

        const { point, marker } = this.deletedPointsStack.pop();

        // Restaurer le point
        this.points.push(point);
        this.markers.push(marker);
        this.map.addLayer(marker);

        console.log("Point restauré :", point);
        showMessage('Point restauré', 'info', false);

        // Recalculer les distances si nécessaire
        if (this.points.length >= 2) {
            this.updateDistances();
        }
    },

    insertPointAtIndex: function(index, latLng) {
        console.log(`=== INSERTION D'UN POINT À L'INDEX ${index} ===`);
        console.log("Position du nouveau point:", latLng);

        if (this.lastPointOnBoat) {
            showMessage('Impossible d\'insérer un point : la route est terminée (dernier point accroché au bateau)', 'error', false);
            return;
        }

        // Insérer le nouveau point dans le tableau
        this.points.splice(index, 0, latLng);
        // Insérer un nom de waypoint par défaut au même index pour conserver l'alignement noms/index
        if (!Array.isArray(this.waypoints)) this.waypoints = [];
        this.waypoints.splice(index, 0, `Point ${index + 1}`);

        // Créer un nouveau marqueur draggable
        const marker = L.marker(latLng, {
            icon: pinIcon,
            interactive: true,
            draggable: true
        }).addTo(this.map);

        // Ajouter le tooltip avec le nom du waypoint (sans modifier les noms existants)
        const insertedWaypointName = this.waypoints[index] || `Point ${index + 1}`;
        marker.bindTooltip(`${insertedWaypointName} - Cliquez pour déplacer ou cliquez à droite`, {
            permanent: false,
            direction: 'top'
        });

        // Gestionnaire de drag
        marker.on('dragstart', () => {
            console.log(`Début du drag du point ${index + 1}`);
        });

        marker.on('drag', (e) => {
            const markerIndex = this.markers.indexOf(marker);
            const newLatLng = e.target.getLatLng();
            this.points[markerIndex] = newLatLng;
            this.updateDistances(this.lastPointOnBoat);
        });

        marker.on('dragend', (e) => {
            const markerIndex = this.markers.indexOf(marker);
            const newLatLng = e.target.getLatLng();
            this.points[markerIndex] = newLatLng;
            console.log(`Point ${markerIndex + 1} déplacé vers:`, newLatLng);
            this.updateDistances(this.lastPointOnBoat);
            showMessage(`Point ${markerIndex + 1} déplacé avec succès`, 'success', false);
        });

        // Menu contextuel (clic droit) pour renommer ou supprimer le point inséré
        marker.on('contextmenu', (e) => {
            L.DomEvent.stopPropagation(e);
            const markerIndex = this.markers.indexOf(marker);
            const waypointName = this.waypoints[markerIndex] || `Point ${markerIndex + 1}`;

            const contextMenu = `
                <div style="padding: 10px; text-align: center;">
                    <strong>${waypointName}</strong><br>
                    <button onclick="measureTool.renamePointAtIndex(${markerIndex}); return false;"
                            style="margin-top: 8px; padding: 8px 16px; background: #4CAF50; color: white;
                                   border: none; border-radius: 4px; cursor: pointer; font-size: 14px; margin-right: 5px;">
                        ✏️ Renommer
                    </button>
                    <button onclick="measureTool.deletePointAtIndex(${markerIndex}); return false;"
                            style="margin-top: 8px; padding: 8px 16px; background: #ff4444; color: white;
                                   border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">
                        🗑️ Supprimer
                    </button>
                </div>
            `;

            marker.bindPopup(contextMenu).openPopup();
        });

        // Insérer le marqueur à la bonne position
        this.markers.splice(index, 0, marker);

        console.log(`✅ Point inséré à l'index ${index}. Nombre total de points: ${this.points.length}`);

        // Renuméroter tous les marqueurs (affichage uniquement)
        this.renumberMarkers();

        // Recalculer les distances
        this.updateDistances(this.lastPointOnBoat);

        // Afficher un message de confirmation
        showMessage(`Point ${index + 1} inséré avec succès. Route renumérotée.`, 'success', false);
    },

    renumberMarkers: function() {
        console.log("=== RENUMÉROTATION DES MARQUEURS ===");

        this.markers.forEach((marker, index) => {
            // Vérifier si c'est un point accroché au bateau
            const isFirstAndAttached = (index === 0 && this.firstPointOnBoat);
            const isLastAndAttached = (index === this.markers.length - 1 && this.lastPointOnBoat);

            // Ne pas modifier les marqueurs accrochés au bateau
            if (!isFirstAndAttached && !isLastAndAttached) {
                // Utiliser le nom du waypoint existant s'il est défini, sinon un nom par défaut
                const waypointName = (Array.isArray(this.waypoints) ? this.waypoints[index] : null) || `Point ${index + 1}`;

                // Mettre à jour le tooltip sans altérer this.waypoints
                marker.unbindTooltip();
                marker.bindTooltip(`${waypointName} - Cliquez pour déplacer`, {
                    permanent: false,
                    direction: 'top'
                });

                // Mettre à jour le popup s'il existe
                if (marker.getPopup()) {
                    const latLng = marker.getLatLng();
                    marker.getPopup().setContent(`
                        <strong>${waypointName}</strong><br>
                        Position: ${latLng.lat.toFixed(5)}, ${latLng.lng.toFixed(5)}<br>
                        <small>Cliquez et faites glisser pour déplacer</small>
                    `);
                }

                console.log(`Marqueur ${index} mis à jour (affichage) avec le nom: ${waypointName}`);
            }
        });

        console.log("✅ Renumérotation terminée (affichage uniquement, noms conservés)");
    },

    deletePointAtIndex: function(index) {
        console.log(`=== SUPPRESSION DU POINT À L'INDEX ${index} ===`);

        // Vérifier qu'il reste au moins 2 points après suppression
        if (this.points.length <= 2) {
            showMessage('Impossible de supprimer : une route doit contenir au moins 2 points', 'error', false);
            return;
        }

        // Vérifier si c'est un point accroché au bateau
        const isFirstAndAttached = (index === 0 && this.firstPointOnBoat);
        const isLastAndAttached = (index === this.markers.length - 1 && this.lastPointOnBoat);

        if (isFirstAndAttached || isLastAndAttached) {
            showMessage('Impossible de supprimer un point accroché au bateau', 'error', false);
            return;
        }

        console.log(`Suppression du point ${index + 1}/${this.points.length}`);

        // Supprimer le point du tableau
        this.points.splice(index, 1);
        // Supprimer le nom de waypoint correspondant pour conserver l'alignement noms/index
        if (Array.isArray(this.waypoints) && index >= 0 && index < this.waypoints.length) {
            this.waypoints.splice(index, 1);
        }

        // Supprimer et retirer le marqueur de la carte
        const markerToRemove = this.markers[index];
        if (markerToRemove) {
            this.map.removeLayer(markerToRemove);
            this.markers.splice(index, 1);
            console.log(`✅ Marqueur ${index + 1} supprimé`);
        }

        // Renuméroter tous les marqueurs (affichage uniquement)
        this.renumberMarkers();

        // Recalculer les distances
        this.updateDistances(this.lastPointOnBoat);

        // Message de confirmation
        showMessage(`Point supprimé avec succès. ${this.points.length} points restants.`, 'success', false);
    },

    renamePointAtIndex: function(index) {
        console.log(`=== RENOMMAGE DU POINT À L'INDEX ${index} ===`);

        // Vérifier que l'index est valide
        if (index < 0 || index >= this.points.length) {
            showMessage('Index de point invalide', 'error', false);
            return;
        }

        // Met cette variable à True pour éviter d'ajouter un point lors du renommage
        this.isModifWaypoint = true;

        // Récupérer le nom actuel
        const currentName = this.waypoints[index] || `Point ${index + 1}`;

         // Demander le nouveau nom avec un prompt
        const newName = prompt(`Renommer le waypoint:\n\nNom actuel: ${currentName}\nNouveau nom:`, currentName);

        // Si l'utilisateur annule ou entre un nom vide, ne rien faire
        if (newName === null || newName.trim() === '') {
            console.log("Renommage annulé");
            return;
        }

        // Mettre à jour le nom du waypoint
        this.waypoints[index] = newName.trim();
        console.log(`✅ Waypoint ${index + 1} renommé en "${newName.trim()}"`);

        // Mettre à jour le tooltip du marqueur
        const marker = this.markers[index];
        if (marker) {
            marker.unbindTooltip();
            marker.bindTooltip(`${newName.trim()} - Cliquez pour déplacer ou cliquez à droite`, {
                permanent: false,
                direction: 'top'
            });

            // Mettre à jour le popup s'il existe
            if (marker.getPopup()) {
                const latLng = marker.getLatLng();
                marker.getPopup().setContent(`
                    <strong>${newName.trim()}</strong><br>
                    Position: ${latLng.lat.toFixed(5)}, ${latLng.lng.toFixed(5)}<br>
                    <small>Cliquez et faites glisser pour déplacer</small>
                `);
            }
        }
        // Message de confirmation
        showMessage(`Waypoint renommé en "${newName.trim()}"`, 'success', false);
    },

    removeLastPoint: function() {
        console.log("=== SUPPRESSION DU DERNIER POINT ===");

        if (this.points.length === 0) {
            console.log("Aucun point à supprimer");
            showMessage('Aucun point à supprimer', 'info', true);
            return;
        }

        // Supprimer le dernier point du tableau
        this.points.pop();
        // Supprimer également le dernier nom de waypoint pour conserver l'alignement
        if (Array.isArray(this.waypoints) && this.waypoints.length > this.points.length) {
            this.waypoints.pop();
        }
        console.log(`Point supprimé. Points restants: ${this.points.length}`);

        // Supprimer le dernier marqueur de la carte
        if (this.markers.length > 0) {
            const lastMarker = this.markers.pop();
            this.map.removeLayer(lastMarker);
            console.log("Marqueur supprimé de la carte");
        }

        // Gérer les flags selon le nombre de points restants
        if (this.points.length === 0) {
            this.firstPointOnBoat = false;
            this.lastPointOnBoat = false;
            this.boatPosition = null;
            console.log("Tous les points supprimés, flags réinitialisés");
            showMessage('Tous les points ont été supprimés', 'info', false);

        } else if (this.points.length === 1) {
            // Si on revient à un seul point, réinitialiser le flag du dernier point
            this.lastPointOnBoat = false;
            showMessage(`Point supprimé. ${this.points.length} point restant`, 'info', false);
        } else {
            // Si on a supprimé un point intermédiaire, vérifier si le nouveau dernier point est accroché
            // Le flag lastPointOnBoat doit être réinitialisé, car on ne sait pas si l'avant-dernier point était accroché
            this.lastPointOnBoat = false;
            showMessage(`Point supprimé. ${this.points.length} point(s) restant(s)`, 'info', false);
        }

        // Recalculer les distances si au moins 2 points restent
        if (this.points.length >= 2) {
            console.log("Re-calcul des distances...");
            this.updateDistances();
        } else if (this.points.length === 1) {
            // S'il ne reste qu'un point, supprimer toutes les lignes et labels
            this.lines.forEach(line => this.map.removeLayer(line));
            this.labels.forEach(label => this.map.removeLayer(label));
            this.lines = [];
            this.labels = [];
            console.log("Un seul point restant, lignes et labels supprimés");
        }
    },

    saveRoute: async function() {
        console.log("=== SAUVEGARDE DE LA ROUTE ===");

        if (this.points.length < 2) {
            showMessage('Au moins 2 points sont nécessaires pour sauvegarder une route', 'error', false);
            return;
        }

        // Récupérer la liste des routes existantes
        let existingRoutes = [];
        try {
            const response = await fetch('/list_route_files');
            existingRoutes = await response.json();
            if (!Array.isArray(existingRoutes)) {
                existingRoutes = [];
            }
        } catch (error) {
            console.error("Erreur lors de la récupération des routes:", error);
        }

        // Demander le nom de la route
        const routeName = prompt("Nom de la route qui sera en lecture seule:\n\n" +
            (existingRoutes.length > 0 ?
                "Routes existantes:\n- " + existingRoutes.map(f => f.replace('.json', '')).join('\n- ') :
                "Aucune route existante"));

        if (!routeName) return;

        // Vérifier si le nom existe déjà
        const filename = `${routeName}.json`;
        if (existingRoutes.includes(filename)) {
            const confirmReplace = confirm(`La route "${routeName}" existe déjà.\n\nVoulez-vous la remplacer ?`);
            if (!confirmReplace) {
                showMessage('Sauvegarde annulée. Veuillez choisir un autre nom.', 'info', false);
                return;
            }
        }

        // Calculer la distance totale
        let totalDistance = 0;
        for (let i = 1; i < this.points.length; i++) {
            totalDistance += this.points[i-1].distanceTo(this.points[i]);
        }
        const totalDistanceNM = (totalDistance / 1852).toFixed(2);

        // Créer l'objet de route à sauvegarder
        const routeData = {
            name: routeName,
            created: new Date().toISOString(),
            firstPointOnBoat: this.firstPointOnBoat,
            lastPointOnBoat: this.lastPointOnBoat,
            totalDistanceNM: parseFloat(totalDistanceNM),
            pointsCount: this.points.length,
            points: this.points.map((point, index) => ({
                index: index,
                lat: point.lat,
                lng: point.lng,
                name: this.waypoints[index] || `Point ${index + 1}`
            }))
        };

        // Envoyer au serveur
        try {
            // Log de débogage pour vérifier les données avant l'envoi
            console.log("=== DONNÉES À ENVOYER ===");
            console.log("Nombre de points:", this.points.length);
            console.log("Nombre de waypoints:", this.waypoints.length);
            console.log("RouteData complet:", JSON.stringify(routeData, null, 2));

            const response = await fetch('/save_route', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    filename: filename,
                    route: routeData
                })
            });
            const result = await response.json();

            console.log("Route sauvegardée:", routeData);
            showMessage(result.message || `Route "${routeName}" sauvegardée (${this.points.length} points, ${totalDistanceNM} NM)`, result.status === 'success' ? 'success' : 'error', false);
        } catch (error) {
            console.error("Erreur lors de la sauvegarde:", error);
            showMessage(`Erreur : ${error.message}`, "error", true);
        }
    },

    downloadRoute: function() {
        console.log("=== TÉLÉCHARGEMENT DE LA ROUTE ===");

        if (this.points.length < 2) {
            showMessage('Au moins 2 points sont nécessaires pour télécharger une route', 'error', false);
            return;
        }

        // Demander le nom de la route
        const routeName = prompt("Nom du fichier à télécharger :", "MaRoute");
        if (!routeName) return;

        // Calculer la distance totale
        let totalDistance = 0;
        for (let i = 1; i < this.points.length; i++) {
            totalDistance += this.points[i-1].distanceTo(this.points[i]);
        }
        const totalDistanceNM = (totalDistance / 1852).toFixed(2);

        // Créer l'objet de route avec les noms des waypoints
        const routeData = {
            name: routeName,
            created: new Date().toISOString(),
            firstPointOnBoat: this.firstPointOnBoat,
            lastPointOnBoat: this.lastPointOnBoat,
            totalDistanceNM: parseFloat(totalDistanceNM),
            pointsCount: this.points.length,
            points: this.points.map((point, index) => ({
                index: index,
                lat: point.lat,
                lng: point.lng,
                name: this.waypoints[index] || `Point ${index + 1}`
            }))
        };

        // Créer le blob JSON
        const jsonString = JSON.stringify(routeData, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });

        // Créer un lien de téléchargement
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;

        // Formater le nom du fichier avec la date
        const dateStr = new Date().toISOString().split('T')[0];
        link.download = `${routeName}_${dateStr}.json`;

        // Déclencher le téléchargement
        document.body.appendChild(link);
        link.click();

        // Nettoyer
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        console.log("Route téléchargée:", routeData);
        showMessage(`Route "${routeName}" téléchargée avec succès sur 'téléchargement' (${this.points.length} points, ${totalDistanceNM} NM)`, 'success', false);
    },

    loadRoute: function() {
        console.log("=== CHARGEMENT D'UNE ROUTE ===");
        // Appeler directement la fonction pour afficher le modal
        loadRouteList();
    },

    loadRouteFromData: function(routeData) {
        console.log("=== CHARGEMENT D'UNE ROUTE DEPUIS LE SERVEUR ===");

        try {
            // Valider la structure du fichier
            if (!routeData.points || !Array.isArray(routeData.points)) {
                throw new Error("Format de fichier invalide: points manquants");
            }

            if (routeData.points.length < 2) {
                throw new Error("La route doit contenir au moins 2 points");
            }

            console.log("Route chargée:", routeData);

            // Nettoyer les mesures actuelles
            this.clear();

            // Activer le mode mesure si nécessaire
            if (!this.mode) {
                this.toggle();
            }

            // AJOUT : Marquer cette route comme chargée (lecture seule)
            this.isLoadedRoute = true;

            // Changer le curseur en main pour indiquer le mode lecture seule
            const mapContainer = this.map.getContainer();
            mapContainer.style.cursor = 'grab';

            // Restaurer les propriétés de la route
            this.firstPointOnBoat = routeData.firstPointOnBoat || false;
            this.lastPointOnBoat = routeData.lastPointOnBoat || false;

            // Charger les waypoints depuis le fichier JSON (ou créer des noms par défaut)
            this.waypoints = [];
            console.log("📦 Données routeData.points :", routeData.points);

            if (routeData.waypoints && Array.isArray(routeData.waypoints)) {
                // Charger les noms personnalisés depuis le JSON
                this.waypoints = routeData.waypoints.map(name => name || `Point ${this.waypoints.length + 1}`);
                console.log("✅ Waypoints chargés depuis le fichier:", this.waypoints);
            } else if (routeData.points && Array.isArray(routeData.points)) {
                    // Nouveau format : noms intégrés dans les points
                    this.waypoints = routeData.points.map((point, i) => point.name || `Point ${i + 1}`);
                    console.log("✅ Waypoints extraits depuis les points:", this.waypoints);
            } else {
                // Créer des noms par défaut si pas de waypoints dans le JSON
                routeData.points.forEach((point, index) => {
                    this.waypoints.push(`Point ${index + 1}`);
                });
                console.log("✅ Waypoints par défaut créés (ancien fichier sans waypoints)");
            }

            // Recréer les points avec possibilité de drag
            routeData.points.forEach((point, index) => {
                const latLng = L.latLng(point.lat, point.lng);
                this.points.push(latLng);

                // Couleur différente pour les points accrochés au bateau
                const isFirstAndAttached = (index === 0 && this.firstPointOnBoat);
                const isLastAndAttached = (index === routeData.points.length - 1 && this.lastPointOnBoat);

                // Les points accrochés au bateau ne sont pas draggable
                const isDraggable = !isFirstAndAttached && !isLastAndAttached;

                // Créer le marqueur DRAGGABLE pour permettre la modification
                const marker = L.marker(latLng, {
                    icon: pinIcon,
                    interactive: true,
                    draggable: isDraggable
                }).addTo(this.map);

                // Récupérer le nom du waypoint depuis le fichier JSON
                const waypointName = point.name || `Point ${index + 1}`;

                // Ajouter un popup au marqueur avec le nom personnalisé
                const popupContent = isDraggable
                    ? `<strong>${waypointName}</strong><br>
                       Position: ${point.lat.toFixed(5)}, ${point.lng.toFixed(5)}<br>
                       <small>Cliquez et faites glisser pour déplacer</small>`
                    : `<strong>${waypointName} - Accroché au bateau</strong><br>
                       Position: ${point.lat.toFixed(5)}, ${point.lng.toFixed(5)}<br>
                       <small>Point fixé au bateau (non déplaçable)</small>`;

                marker.bindPopup(popupContent);

                if (isFirstAndAttached || isLastAndAttached) {
                    marker.setIcon(L.divIcon({
                        className: 'boat-attached-marker',
                        html: '<div style="background: #ff4444; border: 2px solid #ffffff; border-radius: 50%; width: 14px; height: 14px; cursor: not-allowed;"></div>',
                        iconSize: [14, 14],
                        iconAnchor: [7, 7]
                    }));
                } else {
                    // Ajouter le tooltip pour les points draggable avec le nom personnalisé
                    marker.bindTooltip(`${waypointName} - Cliquez pour déplacer ou cliquez à droite`, {
                        permanent: false,
                        direction: 'top'
                    });
                }

                // Gestionnaire de drag pour les routes chargées
                if (isDraggable) {
                    marker.on('dragstart', () => {
                        console.log(`Début du drag du point ${index + 1} de la route`);
                        // Désactiver le mode lecture seule lors du premier drag
                        if (this.isLoadedRoute) {
                            this.isLoadedRoute = false;
                            this.isEditingLoadedRoute = true;
                            showMessage('Mode édition activé - N\'oubliez pas de sauvegarder vos modifications', 'info', false);
                        }
                    });

                    marker.on('drag', (e) => {
                        // Mettre à jour la position dans le tableau
                        const newLatLng = e.target.getLatLng();
                        this.points[index] = newLatLng;

                        // Mettre à jour le popup avec le nom du waypoint
                        marker.getPopup().setContent(`
                            <strong>${waypointName}</strong><br>
                            Position: ${newLatLng.lat.toFixed(5)}, ${newLatLng.lng.toFixed(5)}<br>
                            <small>En déplacement...</small>
                        `);

                        // Recalculer les distances en temps réel
                        this.updateDistances(this.lastPointOnBoat);
                    });

                    marker.on('dragend', (e) => {
                        const newLatLng = e.target.getLatLng();
                        this.points[index] = newLatLng;
                        console.log(`${waypointName} de la route déplacé vers:`, newLatLng);

                        // Mettre à jour le popup final avec le nom du waypoint
                        marker.getPopup().setContent(`
                            <strong>${waypointName}</strong><br>
                            Position: ${newLatLng.lat.toFixed(5)}, ${newLatLng.lng.toFixed(5)}<br>
                            <small>Modifié - Sauvegardez pour conserver les changements</small>
                        `);

                        // Recalculer les distances après le drag
                        this.updateDistances(this.lastPointOnBoat);


                    });

                    // Menu contextuel (clic droit) pour renommer ou supprimer le point
                    marker.on('contextmenu', (e) => {
                        L.DomEvent.stopPropagation(e);
                        const markerIndex = this.markers.indexOf(marker);

                        // Activer automatiquement le mode édition lors du clic droit
                        if (this.isLoadedRoute) {
                            this.isLoadedRoute = false;
                            this.isEditingLoadedRoute = true;
                            showMessage('Mode édition activé', 'info', false);
                        }

                        // Récupérer le nom du waypoint
                        const waypointName = this.waypoints[markerIndex] || `Point ${markerIndex + 1}`;

                        // Créer un popup personnalisé avec boutons de renommage et suppression
                        const contextMenu = `
                            <div style="padding: 10px; text-align: center;">
                                <strong>${waypointName}</strong><br>
                                <button onclick="measureTool.renamePointAtIndex(${markerIndex}); return false;"
                                        style="margin-top: 8px; padding: 8px 16px; background: #4CAF50; color: white;
                                               border: none; border-radius: 4px; cursor: pointer; font-size: 14px; margin-right: 5px;">
                                    ✏️ Renommer
                                </button>
                                <button onclick="measureTool.deletePointAtIndex(${markerIndex}); return false;"
                                        style="margin-top: 8px; padding: 8px 16px; background: #ff4444; color: white;
                                               border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">
                                    🗑️ Supprimer
                                </button>
                            </div>
                        `;

                        marker.bindPopup(contextMenu).openPopup();
                    });
                }

                this.markers.push(marker);
            });

            // Mettre à jour les distances
            if (this.points.length > 1) {
                // Si le dernier point est accroché, ne pas afficher le message normal
                this.updateDistances(this.lastPointOnBoat);
            }

            // Centrer la carte sur la route
            const bounds = L.latLngBounds(this.points);
            this.map.fitBounds(bounds, { padding: [50, 50] });

            const routeName = routeData.name || "Route";

            // Si c'est une route inversée, afficher le message approprié
            if (this.lastPointOnBoat) {
                this.showInvertedRouteMessage();
            } else {
                showMessage(`Route "${routeName}" chargée avec succès (${this.points.length} points)`, 'success', false);
            }

        } catch (error) {
            console.error("Erreur lors du chargement de la route:", error);
            showMessage(`Erreur: ${error.message}`, 'error', true);
        }
    },

    clear: function() {
        console.log("=== NETTOYAGE DES MESURES ===");

        this.labels.forEach(label => {
            this.map.removeLayer(label);
        });
        this.labels = [];

        this.lines.forEach(line => {
            this.map.removeLayer(line);
        });
        this.lines = [];

        this.markers.forEach(marker => {
            this.map.removeLayer(marker);
        });
        this.markers = [];

        this.points = [];
        this.firstPointOnBoat = false;
        this.lastPointOnBoat = false;
        this.boatPosition = null;
        this.isLoadedRoute = false;
        this.isEditingLoadedRoute = false;  // Réinitialiser aussi le mode édition

        // Supprimer le message permanent s'il existe
        this.clearPermanentMessage();

        console.log("✅ Nettoyage terminé");
    },

    toggle: async function() {
        this.mode = !this.mode;
        const button = document.getElementById('distanceMeasureButton');
        const mapContainer = this.map.getContainer();

        if (this.mode) {
            console.log("=== ACTIVATION MODE MESURE ===");
            button.classList.add('active');

            // Désactiver l'interactivité du bateau pour ne pas capter les clics en mode mesure
            setShipMarkerInteractive(false);

            // Afficher le message d'activation en haut de l'écran
            this.updatePermanentMessage('<img src="./static/icone/mesure.png" alt="Historique" width="16" height="16"> ' +
                '&nbsp;Mode mesure ACTIVÉ (Cliquez près du bateau pour le suivre, Échappe pour supprimer le dernier point, Cliquez sur une ligne pour ajouter un point).', 'info');

            mapContainer.style.cursor = 'crosshair';

            // Utiliser le système de gestion de clics de Leaflet au lieu d'addEventListener
            // Cela permet aux polylines d'intercepter les clics en premier
            this.mapClickHandler = this.handleMapClick.bind(this);
            this.map.on('click', this.mapClickHandler);

            // Ajouter l'écouteur de clavier
            this.keyPressHandler = this.handleKeyPress.bind(this);
            document.addEventListener('keydown', this.keyPressHandler);

            console.log("✅ Mode mesure activé");

        } else {
            console.log("=== DÉSACTIVATION MODE MESURE ===");

            // Si un point est accroché au bateau (début ou fin), demander confirmation
            if (this.firstPointOnBoat || this.lastPointOnBoat) {
                const confirmStop = await showMapModal('Confirmation', 'Voulez-vous arrêter le suivi de votre bateau ?');
                if (!confirmStop) {
                    // L'utilisateur ne veut pas arrêter : rester en mode mesure
                    this.mode = true; // réactiver le flag
                    // S'assurer que l'état visuel reste actif (rien n'a été démonté à ce stade)
                    button.classList.add('active');
                    // Conserver l'interactivité du bateau désactivée en mode mesure
                    setShipMarkerInteractive(false);
                    console.log('❎ Désactivation annulée: suivi du bateau maintenu');
                    return;
                }
            }

            button.classList.remove('active');

            if (this.mapClickHandler) {
                this.map.off('click', this.mapClickHandler);
                this.mapClickHandler = null;
            }

            // Retirer l'écouteur de clavier
            if (this.keyPressHandler) {
                document.removeEventListener('keydown', this.keyPressHandler);
                this.keyPressHandler = null;
            }

            mapContainer.style.cursor = 'grab';

            this.clear();
            // Réactiver l'interactivité du bateau
            setShipMarkerInteractive(true);
            showMessage('Mode mesure DÉSACTIVÉ.', 'info');
            console.log("✅ Mode mesure désactivé");
        }
    }
};


// ==============================================
// 10. FONCTIONS DE MISE À JOUR DE VOTRE POSITION
// ==============================================
const updatePosition = async () => {
    try {
        const response = await fetch('/api/get_coordinates');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        if (data.latitude && data.longitude) {
             // Mettre à jour les coordonnées globales avec la vitesse réelle ET le vent
            window.coordinates = {
                latitude: data.latitude,
                longitude: data.longitude,
                sog: data.sog || 0,
                cog: data.cog || 0,
                w_speed_true: data.w_speed_true || 0,
                w_angle_true: normalizeDeg(data.w_angle_true),
                w_speed_app: data.w_speed_app || 0,
                w_angle_app: normalizeDeg(data.w_angle_app),
                boat_info: data.boat_info
            };

            const newLatLng = new L.LatLng(data.latitude, data.longitude);

            // Si on est en enregistrement, ont push la position toutes les 'sec' défini dans l'historique.
            if (AppState.isRecordingActive) {
                if (AppState.incrementScrutationCount()) {
                    // Si la vitesse est > 0.5 Nœud, on enregistre le point
                    if (Math.round(data.sog * 10) / 10 > 0.5) {
                        AppData.positionHistory.push({
                            latitude: data.latitude,
                            longitude: data.longitude,
                            cog: data.cog || 0,
                            sog: data.sog,
                            w_speed_true: data.w_speed_true || 0,
                            w_angle_true: normalizeDeg(data.w_angle_true),
                            w_speed_app: data.w_speed_app || 0,
                            w_angle_app: data.w_angle_app || 0,
                            timestamp: new Date().toISOString()
                        });
                    }

                    updateCurrentTrackStats();

                    document.getElementById('saveIntervalInfo').innerHTML =
                        `<span class="pulse-enregistrement">🔴</span> ENREGISTREMENT<br>
                            Dernière à ${new Date().toLocaleTimeString('fr-FR', {
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                            hour12: false
                        })} - ${AppData.positionHistory.length} points`;

                    AppState.resetScrutationCount();

                    if (AppData.positionHistory.length > 14400) {
                        AppData.positionHistory.shift();
                    }

                    const lastPoint = AppData.positionHistory[AppData.positionHistory.length - 1];

                    polyline.addLatLng([lastPoint.latitude, lastPoint.longitude]);

                    const speed = lastPoint.sog || 0;
                    const arrowColor = AppData.getSpeedColor(speed);

                    const liveArrowIcon = L.divIcon({
                        className: 'live-arrow-icon',
                        html: `<div style="
                            width: 0;
                            height: 0;
                            border-left: 5px solid transparent;
                            border-right: 5px solid transparent;
                            border-bottom: 10px solid ${arrowColor};
                            transform: rotate(${lastPoint.cog}deg);
                            filter: drop-shadow(0 0 1px #000);
                        "></div>`,
                        iconSize: [10, 10],
                        iconAnchor: [5, 5]
                    });

                    const historyLiveMarker = L.marker([lastPoint.latitude, lastPoint.longitude], {
                        icon: liveArrowIcon
                    }).addTo(map).bindPopup(`
                        <strong>Position historique</strong><br>
                        Heure: ${new Date(lastPoint.timestamp).toLocaleTimeString('fr-FR', {
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                            hour12: false
                        })}<br>
                        Position: ${lastPoint.latitude.toFixed(5)}, ${lastPoint.longitude.toFixed(5)}<br>
                        COG: ${lastPoint.cog}°<br>
                        SOG: ${lastPoint.sog.toFixed(1)} nœuds<br>
                        Vent: ${formatWind(lastPoint.w_angle_true)}  - 
                        Vitesse : ${typeof normalizedPoint.w_speed_true === 'number' ? normalizedPoint.w_speed_true.toFixed(1) : 'N/A'}`,

                        { className: 'transparent-popup' });
                    historyLiveMarker.on('mouseover', function () { this.openPopup(); })
                                     .on('mouseout', function () { this.closePopup(); });
                }
            }

            updateShipMarker([data.latitude, data.longitude], data.cog || 0);

            // Mettre à jour le premier point de mesure s'il est accroché au bateau
            if (measureTool && measureTool.updateFirstPointPosition) {
                measureTool.updateFirstPointPosition();
            }

            const sog = data.sog || 0;
            const cog = data.cog || 0;

            const distanceInNauticalMiles = sog * AppState.projectionHours;
            const distanceInDegrees = nauticalMilesToDegrees(distanceInNauticalMiles);
            const headingRad = (cog * Math.PI) / 180;
            const endLat = data.latitude + distanceInDegrees * Math.cos(headingRad);
            const endLon = data.longitude + distanceInDegrees * Math.sin(headingRad);

            projectionLine.setLatLngs([
                [data.latitude, data.longitude],
                [endLat, endLon]
            ]);

            if (AppState.shipMarker) {
                console.log('shipMarker existe');
                AppState.shipMarker.off('click').on('click', function() {
                    AppState.forceKeepOpen = !AppState.forceKeepOpen;
                    if (AppState.forceKeepOpen) {
                        const boatName = data.boat_info ? data.boat_info.name : 'HUAHINE';
                        const boatType = data.boat_info ? data.boat_info.type : 'Voilier';
                        const boatLength = data.boat_info ? data.boat_info.length : 'N/A';
                        const boatWidth = data.boat_info ? data.boat_info.width : 'N/A';
                        const boatDraft = data.boat_info ? data.boat_info.draft : 'N/A';
                        const boatSpeed = data.boat_info ? data.boat_info.speed : 'N/A';
                        const boatMmsi= data.boat_info ? data.boat_info.mmsi : 'N/A';


                        persistentPopup
                            .setLatLng(AppState.shipMarker.getLatLng())
                            .setContent(`
                                <strong>${boatName}</strong> <small>(${boatType})</small><br>
                                <small style="color: #666;">L: ${boatLength}m | l: ${boatWidth}m | TE: ${boatDraft}m</small><br>
                                Position: ${data.latitude.toFixed(5)}, ${data.longitude.toFixed(5)}<br>
                                Cap: ${cog}°<br>
                                Vitesse: ${sog.toFixed(1)} nœuds<br>
                                Distance projetée: ${distanceInNauticalMiles.toFixed(1)} NM sur ${(AppState.projectionHours * 60).toFixed(0)} min
                            `)
                            .addTo(map);
                    } else {
                        map.closePopup(persistentPopup);
                    }
                });
            }

            updateInfo(`
                Zoom: ${map.getZoom()}<br>
                Position: ${data.latitude.toFixed(5)}, ${data.longitude.toFixed(5)}<br>
                Cap: ${cog}°<br>
                Vitesse: ${sog.toFixed(1)} nœuds
            `);
        }
    } catch (err) {
        console.error("Erreur de mise à jour des coordonnées:", err);
    }
};

// ==============================================
// 11. FONCTIONS DE GESTION DES STATISTIQUES
// ==============================================
const updateTrackStats = (totalDistance, averageSpeed, durationHours) => {
    const distanceElement = document.getElementById('totalDistanceInfo');
    const speedElement = document.getElementById('averageSpeedInfo');
    const totalTimeElement = document.getElementById('totalTimeInfo');

    if (distanceElement && speedElement) {
        distanceElement.innerHTML = `Distance totale: ${totalDistance.toFixed(2)} NM`;
        speedElement.innerHTML = `Vitesse moyenne: ${averageSpeed.toFixed(1)} nœuds`;
        if (typeof durationHours === 'number' && isFinite(durationHours) && totalTimeElement) {
            const totalSeconds = Math.max(0, Math.round(durationHours * 3600));
            const h = Math.floor(totalSeconds / 3600);
            const m = Math.floor((totalSeconds % 3600) / 60);
            const s = totalSeconds % 60;
            const mm = m.toString().padStart(2, '0');
            const ss = s.toString().padStart(2, '0');
            totalTimeElement.innerHTML = `Temps passé: ${h}h ${mm}m ${ss}s`;
        }
    }
};

const updateCurrentTrackStats = () => {
    if (AppData.positionHistory.length < 2) {
        clearTrackStats();
        return;
    }

    let totalDistanceNM = 0;
    for (let i = 1; i < AppData.positionHistory.length; i++) {
        const currentLatLng = L.latLng(AppData.positionHistory[i].latitude, AppData.positionHistory[i].longitude);
        const prevLatLng = L.latLng(AppData.positionHistory[i-1].latitude, AppData.positionHistory[i-1].longitude);
        const distanceMeters = currentLatLng.distanceTo(prevLatLng);
        totalDistanceNM += distanceMeters / 1852;
    }

    const firstPoint = AppData.positionHistory[0];
    const lastPoint = AppData.positionHistory[AppData.positionHistory.length - 1];
    const startTime = new Date(firstPoint.timestamp);
    const endTime = new Date(lastPoint.timestamp);
    const durationHours = (endTime - startTime) / (1000 * 60 * 60);
    const averageSpeed = durationHours > 0 ? totalDistanceNM / durationHours : 0;

    updateTrackStats(totalDistanceNM, averageSpeed, durationHours);
};

const clearTrackStats = () => {
    const distanceElement = document.getElementById('totalDistanceInfo');
    const speedElement = document.getElementById('averageSpeedInfo');
    const totalTimeElement = document.getElementById('totalTimeInfo');

    if (distanceElement && speedElement) {
        distanceElement.innerHTML = ``;
        speedElement.innerHTML = ``;
    }
    if (totalTimeElement) {
        totalTimeElement.innerHTML = ``;
    }
};

// ==============================================
// 12. FONCTIONS D'ENREGISTREMENT, HISTORIQUE
// ==============================================
const clearCurrentMemory = () => {
    AppData.positionHistory.length = 0;
    polyline.setLatLngs([]);

    // Nettoyer seulement les anciens layers d'historique
    historyLayers.forEach(layer => {
        if (map.hasLayer(layer)) {
            map.removeLayer(layer);
        }
    });
    historyLayers = [];

    clearTrackStats();
    console.log("Mémoire et trace effacées");
};

// Fonction qui lance l'enregistrement
const updateSaveInterval = () => {
    if (AppState.isRecordingActive) {
        endSaveInterval();
        return;
    }

    const intervalInput = document.getElementById('saveInterval');
    const newInterval = parseInt(intervalInput.value);
    console.log("Enregistrement en COURS... (interval: ", newInterval, " secondes");
    if (AppState.updateSaveInterval(newInterval)) {
        AppState.setRecordingActive(true);
        clearCurrentMemory();
        AppState.resetScrutationCount();

        const intervalMs = CONFIG.UPDATES.positionInterval; // ex: 10000
        let remainingSeconds = AppState.saveInterval * (intervalMs / 1000);
        const seuilSecondes = intervalMs / 1000;
        const saveInfoElement = document.getElementById('saveIntervalInfo');

        const timer = setInterval(() => {
          if ((remainingSeconds > seuilSecondes +2) && AppState.isRecordingActive ){
            saveInfoElement.innerHTML = `
              <img src="./static/icone/enregistrement.png" alt="Historique" width="16" height="16">
              ENREGISTREMENT <br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Dans ${remainingSeconds} secondes
            `;
          } else {
              clearInterval(timer);
            saveInfoElement.innerHTML = `
              <img src="./static/icone/enregistrement.png" alt="Historique" width="16" height="16">
              ENREGISTREMENT <br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<strong>Départ en cours…</strong>
            `;
          }

          if ((remainingSeconds < seuilSecondes) ||  !AppState.isRecordingActive ){
            clearInterval(timer); // Stoppe proprement
          }

          remainingSeconds--;
        }, 1000);

        // Instructions complémentaires immédiates
        document.getElementById("enregistre").innerHTML = `⏸️ Arrêter`;

        setTimeout(() => {
          el.classList.remove("pulse-enregistrement");
        }, 500);

        if (AppState.IsConnected) {
            showMessage(
                `Départ du parcours - Enregistrement en mémoire dans ${remainingSeconds}s.`,
                "success"
            )
        }else{
            showNotification("Vous n'êtes pas connecté,<br>Vous enregistrez les valeurs par défaut", 'error');
        }

    } else {
        alert('Veuillez entrer une valeur entre 1 et 60');
        intervalInput.value = AppState.saveInterval;
    }
};

// Fonction de mesure d'intervalle
function initializeSaveInterval() {
    const intervalInput = document.getElementById('saveInterval');
    const currentValue = parseInt(intervalInput.value) || AppState.saveInterval;

    if (AppState.updateSaveInterval(currentValue)) {
        document.getElementById('saveIntervalInfo').innerHTML =
            `<img src="./static/icone/carre.png" alt="Historique" width="16" height="16"> 
                PRÊT <br>Départ toutes les ${AppState.saveInterval*CONFIG.UPDATES.positionInterval/1000} secondes`;
    }
};

function endSaveInterval() {
    if (!AppState.isRecordingActive){
            return;
        }
    AppState.setRecordingActive(false);

    if (AppData.positionHistory.length > 0) {
        updateCurrentTrackStats();

        const firstPoint = AppData.positionHistory[0];
        const lastPoint = AppData.positionHistory[AppData.positionHistory.length - 1];
        const startTime = new Date(firstPoint.timestamp);
        const endTime = new Date(lastPoint.timestamp);
        const durationMinutes = (endTime - startTime) / (1000 * 60);

        document.getElementById('saveIntervalInfo').innerHTML =
            `<img src="./static/icone/carre.png" alt="Historique" width="16" height="16">
                ENREGISTREMENT ARRÊTÉ<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                Durée: ${durationMinutes.toFixed(1)} minutes - ${AppData.positionHistory.length} points`;

        showMessage(`Fin du parcours - ${AppData.positionHistory.length} points enregistrés en ${durationMinutes.toFixed(1)} minutes,<br>
                Vous pouvez "Sauver" votre parcours.`, "info");
        document.getElementById("enregistre").innerHTML = `▶️ Départ`;
    } else {
        document.getElementById('saveIntervalInfo').innerHTML =
            `<img src="./static/icone/carre.png" alt="Historique" width="16" height="16">
                ENREGISTREMENT ARRÊTÉ<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Aucun point enregistré`;

        document.getElementById("enregistre").innerHTML = `▶️ Départ`;

        showMessage("Enregistrement arrêté - Aucun point n'a été enregistré.", "info");
    }
};

const drawHistory = (data, filename) => {
    AppData.positionHistory.length = 0;

    // Nettoyage des couches existantes
    historyLayers.forEach(layer => {
        if (map.hasLayer(layer)) {
            map.removeLayer(layer);
        }
    });
    historyLayers = [];

    if (polyline) {
        map.removeLayer(polyline);
    }

    // Tu peux ignorer la polyligne globale si tu veux des segments colorés
    let totalDistanceNM = 0;

    // 🟢 Boucle pour créer les points et remplir AppData.positionHistory
    data.forEach((point, index) => {
        if (!point.latitude || !point.longitude || !point.timestamp ||
            (!point.speed && !point.sog) || (!point.cog && !point.cog)) {
            console.warn(`Point invalide à l'index ${index}:`, point);
            return;
        }

        const normalizedPoint = {
            latitude: point.latitude,
            longitude: point.longitude,
            timestamp: point.timestamp,
            cog: point.cog,
            speed: point.speed || point.sog,
            allure: point.w_angle_true,
            w_speed_true: point.w_speed_true
        };

        AppData.positionHistory.push(normalizedPoint);


        const speed = normalizedPoint.speed || 0;
        const fillColor = AppData.getSpeedColor(speed);

        const arrowIcon = L.divIcon({
            className: 'history-arrow-icon',
            html: `<div style="
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 10px solid ${fillColor};
                transform: rotate(${normalizedPoint.cog}deg);
                filter: drop-shadow(0 0 1px #000);
            "></div>`,
            iconSize: [10, 10],
            iconAnchor: [5, 5]
        });

        const marker = L.marker([normalizedPoint.latitude, normalizedPoint.longitude], {
            icon: arrowIcon
        }).bindPopup(`
            <strong>Position historique</strong><br>
            Heure: ${new Date(normalizedPoint.timestamp).toLocaleTimeString('fr-FR', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            })}<br>
            Position: ${normalizedPoint.latitude.toFixed(5)}°N, ${normalizedPoint.longitude.toFixed(5)}°E<br>
            COG: ${typeof normalizedPoint.cog === 'number' ? normalizedPoint.cog.toFixed(1) : 'N/A'}°<br>
            SOG: ${typeof normalizedPoint.speed === 'number' ? normalizedPoint.speed.toFixed(1) : 'N/A'} nœuds.<br>
            Vent : ${formatWind(normalizedPoint.allure)}  - 
            Vitesse : ${typeof normalizedPoint.w_speed_true === 'number' ? normalizedPoint.w_speed_true.toFixed(1) : 'N/A'} nœuds.
        `, { className: 'transparent-popup' });


        marker.on('mouseover', function () { this.openPopup(); })
              .on('mouseout', function () { this.closePopup(); });
        historyLayers.push(marker);
        marker.addTo(map);
    });

    // 🔁 Boucle pour dessiner les segments colorés
    for (let i = 1; i < AppData.positionHistory.length; i++) {
        const p1 = AppData.positionHistory[i - 1];
        const p2 = AppData.positionHistory[i];

        const latlngs = [
            [p1.latitude, p1.longitude],
            [p2.latitude, p2.longitude]
        ];

        const speed = p2.speed || 0;
        const color = AppData.getSpeedColor(speed);

        const segment = L.polyline(latlngs, {
        color: color,
        weight: 2,
        opacity: 0.8
        }).addTo(map);
        /*
        .bindPopup(`
            <strong>Historique ${i}</strong><br>
            De ${new Date(p1.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}<br>
            A ${new Date(p2.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}<br>
            Cap: ${p2.cog.toFixed(1)}°
            Vitesse: ${p2.speed.toFixed(1)} nœuds<br>
        `)
         */

    historyLayers.push(segment);
        /*
        segment.on('mouseover', function () { this.openPopup(); })
               .on('mouseout', function () { this.closePopup(); });
        */
        const distMeters = L.latLng(p1.latitude, p1.longitude).distanceTo(L.latLng(p2.latitude, p2.longitude));
        totalDistanceNM += distMeters / 1852;
    }

    // Mise à jour des stats et centrage
    if (AppData.positionHistory.length > 0) {
        const first = AppData.positionHistory[0];
        const last = AppData.positionHistory[AppData.positionHistory.length - 1];
        const durationHours = (new Date(last.timestamp) - new Date(first.timestamp)) / (1000 * 60 * 60);
        const averageSpeed = durationHours > 0 ? totalDistanceNM / durationHours : 0;

        updateTrackStats(totalDistanceNM, averageSpeed, durationHours);

        // Créer les bounds à partir de tous les points du parcours
        const bounds = L.latLngBounds(
            AppData.positionHistory.map(point => [point.latitude, point.longitude])
        );

        // Centrer la carte sur le parcours avec un padding
        map.fitBounds(bounds, { padding: [50, 50] });

        showMessage(`Historique chargé depuis ${filename} (${AppData.positionHistory.length} points).`, "success");
    } else {
        showMessage("Aucune donnée d'historique disponible.", "info");
    }
};

const createArrowIcon = (cog) => {
    return L.divIcon({
        className: 'arrow-icon',
        html: `<div style="
            width: 0;
            height: 0;
            border-left: 6px solid transparent;
            border-right: 6px solid transparent;
            border-bottom: 12px solid red;
            transform: rotate(${cog}deg);
        "></div>`,
        iconSize: [12, 12],
        iconAnchor: [6, 6]
    });
};

// ==============================================
// 13. FONCTIONS DE GESTION DE FICHIERS
// ==============================================
const saveHistory = () => {
    const rawName = document.getElementById("filenameInput").value;
    if (!rawName) {
        showMessage(`Saisissez un nom de parcours.`, "error");
        return;
    }
    if (AppState.isTraceDisplayed) {
        showMessage(`Impossible, car ce fichier est déjà visualisé, <br>Effacez la trace!`, "error");
        return;
    }
    const filename = normalizeFilename(rawName);
    AppState.lastSavedFilename = filename;

    if (!filename) {
        alert("Veuillez entrer un nom de fichier");
        return;
    }

    if (AppData.positionHistory.length === 0) {
        alert("Aucune donnée à sauvegarder");
        return;
    }

    const payload = {
        filename: filename,
        history: AppData.positionHistory
    };

    fetch('/save_history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            showMessage(`Sauvegarde réussie dans ${filename}.`, "success");
        } else {
            alert("Erreur : " + data.message);
        }
    })
    .catch(err => {
        console.error("Erreur de sauvegarde :", err);
        alert("Erreur lors de la sauvegarde");
    });
}

const loadHistory = async () => {
    try {
        if (AppState.isRecordingActive){
            showMessage(`Impossible, car un enregistrement est en cours,<br>Ouvrez la carte sur un nouvel onglet (touche F2).`, "error");
            return;
        }
        const response = await fetch('/list_json_files');
        const files = await response.json();

        if (!Array.isArray(files) || files.length === 0) {
            showMessage("Aucun fichier de parcours disponible.");
        }

        const selector = document.getElementById("fileSelector");
        selector.innerHTML = "";
        files.forEach(file => {
            const option = document.createElement("option");
            option.value = file;
            baseName = file.split('.').slice(0, -1).join('.');
            option.textContent = baseName;
            selector.appendChild(option);
        });

        document.getElementById("fileModal").style.display = "flex";

    } catch (error) {
        console.error("Erreur lors de la récupération des fichiers :", error);
        showMessage(`Il n'y a pas de fichier enregistré`, "error");
    }
}

const closeFileModal = () => {
    document.getElementById("fileModal").style.display = "none";
}

const confirmFileSelection = () => {
    const filename = document.getElementById("fileSelector").value;

    baseName = filename.split('.').slice(0, -1).join('.');
    document.getElementById("filenameInput").value = baseName;

    closeFileModal();
    loadHistoryFromFile(filename);
    AppState.setTraceDisplayed(true);
}

const loadHistoryFromFile = async (filename) => {
    try {
        const response = await fetch('/load_history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename })
        });

        const data = await response.json();

        if (!Array.isArray(data)) {
            throw new Error(data.message || "Format de données invalide");
        }

        // 🔁 Appel de la fonction de dessin
        drawHistory(data, filename);

    } catch (error) {
        console.error("Erreur de chargement :", error);
        showMessage(`Il n'y a pas de fichier enregistré`, "error");
    }
}

// ========================================== FONCTIONS DE GESTION DES ROUTES =====================================
// Afficher le modal avec la liste des routes
async function loadRouteList() {
    try {
        const response = await fetch('/list_route_files');
        const files = await response.json();

        if (!Array.isArray(files) || files.length === 0) {
            showMessage("Aucun fichier de route disponible.");
            return;
        }

        const selector = document.getElementById("routeSelector");
        selector.innerHTML = "";
        files.forEach(file => {
            const option = document.createElement("option");
            option.value = file;
            const baseName = file.split('.').slice(0, -1).join('.');
            option.textContent = baseName;
            selector.appendChild(option);
        });

        document.getElementById("routeModal").style.display = "flex";

    } catch (error) {
        console.error("Erreur lors de la récupération des routes :", error);
        showMessage(`Erreur : ${error.message}`, "error");
    }
}

// Charger une route depuis le serveur
async function loadRouteFromServer(filename) {
    try {
        const response = await fetch('/load_route', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({filename: filename})
        });
        const routeData = await response.json();

        if (routeData.status === 'error') {
            throw new Error(routeData.message);
        }

        // Appeler la fonction de measureTool pour afficher la route
        if (measureTool && routeData.points) {
            measureTool.loadRouteFromData(routeData);
        }

    } catch (error) {
        console.error("Erreur lors du chargement de la route:", error);
        showMessage(`Erreur : ${error.message}`, "error");
    }
}

// Confirmer la sélection d'une route
function confirmRouteSelection() {
    const filename = document.getElementById("routeSelector").value;
    if (!filename) {
        showMessage("Veuillez sélectionner une route", "error");
        return;
    }
    closeRouteModal();
    loadRouteFromServer(filename);
}

// Fermer le modal des routes
function closeRouteModal() {
    document.getElementById("routeModal").style.display = "none";
}

// Supprimer une route
async function deleteSelectedRoute() {
    const filename = document.getElementById("routeSelector").value;
    if (!filename) {
        showMessage("Veuillez sélectionner une route", "error");
        return;
    }

    if (!confirm(`Supprimer la route "${filename}" ?`)) return;

    try {
        const response = await fetch('/delete_route', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({filename: filename})
        });
        const result = await response.json();
        showMessage(result.message, result.status === 'success' ? 'success' : 'error');
        if (result.status === 'success') {
            loadRouteList(); // Recharger la liste
        }
    } catch (error) {
        console.error("Erreur lors de la suppression:", error);
        showMessage(`Erreur : ${error.message}`, "error");
    }
}

// ========================================== FIN FONCTIONS DE GESTION DES ROUTES ===================================

// ========================================== FONCTION DE SUPPRESSION DE L'HISTORIQUE ===============================
// Supprimer un historique depuis le modal
async function deleteSelectedHistory() {
    const filename = document.getElementById("fileSelector").value;
    if (!filename) {
        showMessage("Veuillez sélectionner un historique", "error");
        return;
    }

    if (!confirm(`Supprimer l'historique "${filename}" ?`)) return;

    try {
        const response = await fetch('/delete_history', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({filename: filename})
        });
        const result = await response.json();
        showMessage(result.message, result.status === 'success' ? 'success' : 'error');
        if (result.status === 'success') {
            loadHistory(); // Recharger la liste
        }
    } catch (error) {
        console.error("Erreur lors de la suppression:", error);
        showMessage(`Erreur : ${error.message}`, "error");
    }
}

// ========================================== FIN FONCTION DE SUPPRESSION DE L'HISTORIQUE ===========================

function clearTrace() {
    if (AppState.isRecordingActive){
        showMessage(`Impossible, car un enregistrement est en cours.<br>Cliquez sur '⏸️ Arrêter'`, "error");
        return;
    }
    if (!AppState.isTraceDisplayed) {
        showMessage("Aucun historique tracé sur l'écran, \nCliquez sur le bouton 'Charger' les historiques.","error");
        initializeSaveInterval();
        return;
    }

    AppData.positionHistory.length = 0;

    // Effacer seulement les layers d'historique
    historyLayers.forEach(layer => {
        if (map.hasLayer(layer)) {
            map.removeLayer(layer);
        }
    });
    historyLayers = [];

    polyline.setLatLngs([]);

    clearTrackStats();
    showMessage("Trace d'historique effacée.", "success");
    initializeSaveInterval();
    AppState.setTraceDisplayed(false);
}

// ==============================================
// 15. FONCTIONS DE SUPPRESSION
// ==============================================
function showSimpleConfirm(message, onConfirm) {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.5); z-index: 2000; display: flex;
        justify-content: center; align-items: center;
    `;

    modal.innerHTML = `
        <div style="background: white; padding: 25px; border-radius: 8px; text-align: center; max-width: 350px;">
            <h3 style="color: #d32f2f; margin-bottom: 15px;"><img src="./static/icone/warning.png" alt="Historique" width="16" height="16"> 
                Confirmation</h3>
            <p style="margin-bottom: 20px; line-height: 1.4;">${message}</p>
            <button id="confirmBtn" style="background: #d32f2f; color: white; padding: 10px 20px; border: none; border-radius: 4px; margin-right: 10px; cursor: pointer;">
                Supprimer
            </button>
            <button id="cancelBtn" style="background: #666; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer;">
                Annuler
            </button>
        </div>
    `;

    document.body.appendChild(modal);

    modal.querySelector('#confirmBtn').onclick = () => {
        modal.remove();
        onConfirm();
    };

    modal.querySelector('#cancelBtn').onclick = () => modal.remove();
    modal.onclick = (e) => e.target === modal && modal.remove();
}

function deleteFile(filename, filenameInput) {
    fetch('/delete_history', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ filename: filename })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showMessage(`<img src="./static/icone/succes.png" alt="Historique" width="16" height="16"> 
                    Fichier "${filename}" supprimé avec succès.`, "success");
            filenameInput.value = '';
        } else {
            showMessage(`<img src="./static/icone/croix.png" alt="Historique" width="16" height="16">  : ${data.message}.`, "error");
        }
    })
    .catch(error => {
        console.error('Erreur lors de la suppression:', error);
        showMessage('<img src="./static/icone/croix.png" alt="Historique" width="16" height="16"> Erreur lors de la suppression du fichier.', "error");
    });
}

// ==============================================
// 16. CONFIGURATION DU BATEAU
// ==============================================
let boatConfig = '';
function showBoatConfigModal() {
    fetch('/get_boat_config')
    .then(response => response.json())
    .then(config => {
        boatConfig = config;
        createBoatConfigModal(config);
    })
    .catch(error => {
        console.error('Erreur lors du chargement de la configuration:', error);
        createBoatConfigModal({
            name: "HUAHINE",
            type: "Voilier",
            length: "12.0",
            width: "3.8",
            draft: "1.8",
            mmsi: "999 999 999",
            speed: "6.0"
        });
    });
}

function createBoatConfigModal(config) {
    const existingModal = document.getElementById('boatConfigModal');
    if (existingModal) {
        existingModal.remove();
    }

    const modal = document.createElement('div');
    modal.id = 'boatConfigModal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.6);
        z-index: 2001;
        display: flex;
        justify-content: center;
        align-items: center;
        animation: fadeIn 0.3s ease-out;
    `;

    const modalContent = document.createElement('div');
    modalContent.style.cssText = `
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 30px;
        border-radius: 15px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        max-width: 450px;
        width: 90%;
        border: 2px solid #1e88e5;
        position: relative;
    `;

    modalContent.innerHTML = `
        <div style="text-align: center; margin-bottom: 25px;">
            <h2 style="margin: 0; color: #1e88e5; font-size: 24px; display: flex; align-items: center; justify-content: center; gap: 10px;">
                ⚓ Configuration du Bateau
            </h2>
        </div>

        <form id="boatConfigForm" style="display: flex; flex-direction: column; gap: 15px;">
            <div style="display: flex; flex-direction: column;">
                <label style="font-weight: bold; color: #333; margin-bottom: 5px; display: flex; align-items: center; gap: 5px;">
                    <img src="./static/icone/etiquette.png" alt="Mesures" width="16" height="16">
                        Nom du bateau:
                </label>
                <input type="text" id="boatName" value="${config.name}"
                       style="padding: 10px; border: 2px solid #ddd; border-radius: 8px; font-size: 14px; transition: border-color 0.3s;"
                       placeholder="Ex: HUAHINE">
            </div>

            <div style="display: flex; flex-direction: column;">
                <label style="font-weight: bold; color: #333; margin-bottom: 5px; display: flex; align-items: center; gap: 5px;">
                    <img src="./static/icone/VoilierImage.ico" alt="Mesures" width="16" height="16">
                        Type de bateau:
                </label>
                <input type="text" id="boatType" value="${config.type}"
                       style="padding: 10px; border: 2px solid #ddd; border-radius: 8px; font-size: 14px; transition: border-color 0.3s;"
                       placeholder="Ex: Voilier, Moteur, Catamaran">
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
                 <div style="display: flex; flex-direction: column;">
                    <label style="font-weight: bold; color: #333; margin-bottom: 5px; font-size: 12px; text-align: center;">
                        ️<img src="./static/icone/largeur.png" alt="Mesures" width="16" height="16"> Longueur (m):
                    </label>
                    <input type="number" step="0.1" min="0" max="50" id="boatLength" value="${config.length}"
                           style="padding: 8px; border: 2px solid #ddd; border-radius: 6px; font-size: 13px; width: 80px; margin: 0 auto;"
                           placeholder="12.0">
                </div>

                <div style="display: flex; flex-direction: column;">
                    <label style="font-weight: bold; color: #333; margin-bottom: 5px; font-size: 12px; text-align: center;">
                        <img src="./static/icone/longueur.png" alt="Mesures" width="16" height="16"> Largeur (m):
                    </label>
                    <input type="number" step="0.1" min="0" max="50" id="boatWidth" value="${config.width}"
                           style="padding: 8px; border: 2px solid #ddd; border-radius: 6px; font-size: 13px; width: 80px; margin: 0 auto;"
                           placeholder="3.8">
                </div>

                <div style="display: flex; flex-direction: column;">
                    <label style="font-weight: bold; color: #333; margin-bottom: 5px; font-size: 12px; text-align: center;">
                        ⚓ T. d'eau (m):
                    </label>
                    <input type="number" step="0.1" min="0" max="50" id="boatDraft" value="${config.draft}"
                           style="padding: 8px; border: 2px solid #ddd; border-radius: 6px; font-size: 13px; width: 80px; margin: 0 auto;"
                           placeholder="1.8">
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                     
                <div style="display: flex; flex-direction: column;">
                    <label style="font-weight: bold; color: #333; margin-bottom: 5px; display: flex; align-items: center; gap: 5px;">
                        ️<img src="./static/icone/information.png" alt="Historique" width="16" height="16">
                            Numéro MMSI:
                    </label>
                    <input type="text" id="boatMmsi" value="${config.mmsi}"
                           style="padding: 10px; border: 2px solid #ddd; border-radius: 8px; font-size: 14px; transition: border-color 0.3s;"
                           placeholder="Ex: 275 303 123">
                </div>
                
                <div style="display: flex; flex-direction: column;">
                    <label style="font-weight: bold; color: #333; margin-bottom: 5px; display: flex; align-items: center; gap: 5px;">
                        <img src="./static/icone/speedometer.png" alt="Historique" width="16" height="16">
                            Vitesse de croisière NM:
                    </label>
                    <input type="text" id="boatSpeed" value="${config.speed}"
                           style="padding: 10px; border: 2px solid #ddd; border-radius: 8px; font-size: 14px; transition: border-color 0.3s;"
                           placeholder="Ex: 6.0">
                </div>
            </div>

        </form>

        <div style="display: flex; gap: 15px; justify-content: center; margin-top: 25px;">
            <button id="cancelConfigBtn" style="
                background: linear-gradient(135deg, #757575, #616161);
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: bold;
                font-size: 14px;
                transition: all 0.3s ease;
                box-shadow: 0 3px 10px rgba(117, 117, 117, 0.3);
            ">
                <img src="./static/icone/croix.png" alt="Historique" width="16" height="16">
                    Annuler
            </button>
            &nbsp;&nbsp;
            <button id="saveConfigBtn" style="
                background: linear-gradient(135deg, #4CAF50, #45a049);
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: bold;
                font-size: 14px;
                transition: all 0.3s ease;
                box-shadow: 0 3px 10px rgba(76, 175, 80, 0.3);
            ">
                <img src="./static/icone/disquette.png" alt="Historique" width="16" height="16">
                    Sauvegarder
            </button>
        </div>
    `;

    modal.appendChild(modalContent);
    document.body.appendChild(modal);

    const saveBtn = modal.querySelector('#saveConfigBtn');
    const cancelBtn = modal.querySelector('#cancelConfigBtn');

    saveBtn.onmouseover = () => {
        saveBtn.style.transform = 'translateY(-2px)';
        saveBtn.style.boxShadow = '0 5px 15px rgba(76, 175, 80, 0.4)';
    };
    saveBtn.onmouseout = () => {
        saveBtn.style.transform = 'translateY(0)';
        saveBtn.style.boxShadow = '0 3px 10px rgba(76, 175, 80, 0.3)';
    };

    cancelBtn.onmouseover = () => {
        cancelBtn.style.transform = 'translateY(-2px)';
        cancelBtn.style.boxShadow = '0 5px 15px rgba(117, 117, 117, 0.4)';
    };
    cancelBtn.onmouseout = () => {
        cancelBtn.style.transform = 'translateY(0)';
        cancelBtn.style.boxShadow = '0 3px 10px rgba(117, 117, 117, 0.3)';
    };

    const inputs = modal.querySelectorAll('input');
    inputs.forEach(input => {
        input.onfocus = () => {
            input.style.borderColor = '#1e88e5';
            input.style.boxShadow = '0 0 8px rgba(30, 136, 229, 0.3)';
        };
        input.onblur = () => {
            input.style.borderColor = '#ddd';
            input.style.boxShadow = 'none';
        };
    });

    saveBtn.onclick = () => saveBoatConfig();
    cancelBtn.onclick = () => modal.remove();

    document.addEventListener('keydown', function escapeHandler(e) {
        if (e.key === 'Escape') {
            modal.remove();
            document.removeEventListener('keydown', escapeHandler);
        }
    });

    modal.onclick = (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    };
}

function closeBoatModal() {
    const modal = document.getElementById('boatConfigModal');
    if (modal) {
        modal.remove();
    }
}

function deepEqual(a, b) {
  return JSON.stringify(a, Object.keys(a).sort()) === JSON.stringify(b, Object.keys(b).sort());
}

function formaterMmsi(valeur) {
  const brut = valeur.replace(/\D+/g, ''); // supprime tout sauf chiffres
  return brut.replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1 ');
}

function saveBoatConfig() {
  const brutMmsi = document.getElementById('boatMmsi').value.trim();
  const mmsiNettoye = brutMmsi.replace(/\D+/g, ''); // pour la logique interne
  const mmsiFormaté = formaterMmsi(brutMmsi);       // pour l'affichage

  // Met à jour le champ avec le format visuel
  document.getElementById('boatMmsi').value = mmsiFormaté;

  const config = {
    name: document.getElementById('boatName').value.trim() || "HUAHINE",
    type: document.getElementById('boatType').value.trim() || "Voilier",
    length: document.getElementById('boatLength').value.trim() || "12.0",
    width: document.getElementById('boatWidth').value.trim() || "3.8",
    draft: document.getElementById('boatDraft').value.trim() || "1.8",
    mmsi: mmsiFormaté || "999 999 999", // version nettoyée pour la logique
    speed: document.getElementById('boatSpeed').value.trim() || "1.8"
  };


    console.log( config , boatConfig  );
    if (deepEqual(boatConfig , config)) {
        console.log("Aucune modification détectée. Sauvegarde ignorée.");
        closeBoatModal();
        return; // ⛔ Sortie de la fonction
    }


    fetch('/save_boat_config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Mettre à jour la vitesse en mémoire et rafraîchir le message de mesure si nécessaire
            try {
                // Met à jour la configuration en mémoire utilisée par getDefaultCruisingSpeed()
                window.coordinates = window.coordinates || {};
                window.coordinates.boat_info = window.coordinates.boat_info || {};
                window.coordinates.boat_info.speed = parseFloat(config.speed) || parseFloat(window.coordinates.boat_info.speed) || 6.0;
            } catch (e) {
                console.warn('Impossible de mettre à jour window.coordinates.boat_info.speed', e);
            }
            suptext=''
            if (typeof measureTool !== 'undefined' && measureTool && Array.isArray(measureTool.points)
                && measureTool.points.length >= 2 && config.speed !== boatConfig.speed) {
                // Recalculer les distances et afficher à nouveau le message avec la nouvelle vitesse
                measureTool.updateDistances(false);
                suptext = '<br>Vous avez mis à jour la vitesse de croisière ' + config.speed + ' nds'
            }
            showMessage(`<img src="./static/icone/succes.png" alt="Historique" width="16" height="16">
                Configuration du bateau "${config.name}" sauvegardée.`+ suptext, "success");
            document.getElementById('boatConfigModal').remove();
        } else {
            showMessage(`<img src="./static/icone/croix.png" alt="Historique" width="16" height="16">
                Erreur : ${data.message}`, "error");
        }
    })
    .catch(error => {
        console.error('Erreur lors de la sauvegarde:', error);
        showMessage(' <img src="./static/icone/croix.png" alt="Historique" width="16" height="16">' +
            'Erreur lors de la sauvegarde de la configuration.', "error");
    });
}

// ==============================================
// 17. FONCTIONS D'INTERFACE UTILISATEUR
// ==============================================
const updateInfoVisibility = (visible) => {
  document.querySelectorAll('.legend, .history-controls').forEach(element => {
    if (visible) {
      element.classList.remove('hidden');
    } else {
      element.classList.add('hidden');
    }
  });
};

function updateProjectionTime() {
    updatePosition();
    const input = document.getElementById('projectionTime');
    const minutes = parseFloat(input.value);

    if (AppState.updateProjectionHours(minutes)) {
        document.getElementById('projectionInfo').innerHTML =
          minutes > 0
            ? `Projection sur ${minutes.toFixed(0)} minutes`
            : 'Cliquez ci-dessus pour faire une projection';
        updateAISData();
    } else {
        showMessage('Veuillez entrer une valeur inférieur à 1440 minutes soit 24 heures.',"error");
        input.value = AppState.projectionHours * 60;
    }
}

const info = document.getElementById('info');
function updateInfo(text) {
    info.innerHTML = text;
}

function centerOnBoat() {
    if (AppState.shipMarker) {
        const currentPosition = AppState.shipMarker.getLatLng();
        const currentZoom = map.getZoom();
        map.setView(currentPosition, currentZoom);
    }
}

// ==============================================
// 18. INITIALISATION ET GESTIONNAIRES D'ÉVÉNEMENTS
// ==============================================
// Avertissement de sortie ne pas appeler preventDefault (cause problèmes sur Firefox après "Rester sur la page")
window.addEventListener("beforeunload", (e) => {
    e.preventDefault();

    // Déclenche un prompt natif uniquement si nécessaire
    // Laisser la chaîne vide suffit pour Chrome/Edge ; Firefox affiche un message générique.
    e.returnValue = "";
});

// Attendre que la carte soit prête
map.whenReady(() => {
    initializeShip();
});

// Initialisation de l'outil de mesure
measureTool.init(map);

// Écouteurs globaux de la souris
document.addEventListener('contextmenu', function (e) {
  e.preventDefault();
});

document.addEventListener('mousedown', (e) => {
    AppState.dragStartPos = { x: e.clientX, y: e.clientY };
    AppState.isDragging = false;
});

document.addEventListener('mousemove', (e) => {
    if (!AppState.dragStartPos) return;
    const dx = Math.abs(e.clientX - AppState.dragStartPos.x);
    const dy = Math.abs(e.clientY - AppState.dragStartPos.y);
    AppState.isDragging = (dx > 5 || dy > 5);
});


document.addEventListener('mouseup', () => {
    // Laisse le clic DOM se déclencher avant de reset
    setTimeout(() => {
        AppState.isDragging = false;
        AppState.dragStartPos = null;
    }, 100); // 100 ms suffit pour laisser passer le clic
});

// Gestionnaires d'événements DOM
document.addEventListener('DOMContentLoaded', function() {
    // Initialisation des projections
    document.getElementById('projectionTime').value = (AppState.projectionHours * 60).toFixed(0);
    document.getElementById('projectionInfo').innerHTML =
        (AppState.projectionHours * 60) > 0
            ? `Projection sur ${minutes.toFixed(0)} minutes`
            : 'Cliquez ci-dessus pour faire une projection';

    // Initialisation de l'enregistrement
    initializeSaveInterval();

    document.getElementById('saveInterval').addEventListener('change', function () {
        const newInterval = parseInt(this.value, 10);
        console.log(newInterval);
        AppState.saveInterval = newInterval;
        initializeSaveInterval();
        if (AppState.updateSaveInterval(newInterval)) {
            console.log("NOUVEL INTERVALE : ", newInterval)
            console.log("🔴 saveInterval mis à jour et compteur réinitialisé");
        } else {
            alert("Intervalle invalide (1 à 60)");
        }
});

// projectionTime
document.getElementById('projectionTime').addEventListener('change', function () {
    updateProjectionTime();
});

// Initialisation de la visibilité
updateInfoVisibility(!AppState.isInfoVisible);

// Gestionnaire pour le bouton de bascule
function toggleHistorique() {
    AppState.isInfoVisible = !AppState.isInfoVisible;
    updateInfoVisibility(!AppState.isInfoVisible);

    const bouton = document.getElementById('toggleInfoButton');
    if (bouton) {
        bouton.classList.toggle('active');
        bouton.title = AppState.isInfoVisible
            ? "Afficher l'historique et les projections"
            : "Masquer l'historique et les projections";
    }
};

// Attacher au clic
document.getElementById('toggleInfoButton').addEventListener('click', toggleHistorique);

// Gestionnaire pour le bouton de bascule
function toggleVent() {
    AppState.isVentVisible = !AppState.isVentVisible;

    // Passage en frontend : plus d'appel backend. On bascule sur 'Fenêtre1' côté client.
    if (window.Fenetre1 && typeof window.Fenetre1.toggle === 'function') {
        window.Fenetre1.toggle(AppState.isVentVisible);
    }

    const bouton = document.getElementById('toggleVent');
    if (bouton) {
        bouton.classList.toggle('active');
        bouton.title = AppState.isVentVisible
            ? "Masquer les vents"
            : "Afficher les vents";
    }
};

// Attacher au clic
document.getElementById('toggleVent').addEventListener('click', toggleVent);

// Gestionnaire pour le bouton menu
const toggleMenuButton = document.getElementById('toggleMenu');
    if (toggleMenuButton) {
        toggleMenuButton.addEventListener('click', function() {
            showBoatConfigModal();
        });
    }
});

document.getElementById('toggle-labels').addEventListener('click', function () {
  this.classList.toggle('active');
  AppState.IsNoDisplay = this.classList.contains('active');

  // Message dynamique
  if (AppState.IsNoDisplay) {
    showMessage("Étiquettes masquées.", "info");
  } else {
    showMessage("Étiquettes affichées.", "info");
  }

  // Affichage / masquage des labels
  const labels = document.querySelectorAll('.distance-label');
  labels.forEach(label => {
    label.style.display = AppState.IsNoDisplay ? 'none' : 'block';
  });

  // Mise à jour du title
  this.title = AppState.IsNoDisplay
    ? "Afficher les étiquettes de distance"
    : "Masquer les étiquettes de distance";
});


// ==============================================
// 19. INTERVALLES DE MISE À JOUR ET NETTOYAGE
// ==============================================
// Marqueur principal (legacy - à supprimer après refactoring)
/*
const currentMarker = L.marker(CONFIG.MAP.initialPosition, {
    icon: createCustomIcon(0),
    }).addTo(map)
    .bindPopup("Salut tout le monde ! Je suis HUAHINE");
 */

// Mise à jour initiale des informations
updateInfo(`Zoom: ${map.getZoom()}<br>Position: ${CONFIG.MAP.initialPosition[0].toFixed(5)}, ${CONFIG.MAP.initialPosition[1].toFixed(5)}`);

// Intervalles de mise à jour
clearAllMarkers();
updatePosition();
AppState.updateInterval = setInterval(updatePosition, CONFIG.UPDATES.positionInterval);
AppState.aisUpdateInterval = setInterval(updateAISData, CONFIG.UPDATES.aisInterval);

// Premier appel immédiat pour les données AIS
updateAISData();

// Nettoyage à la fermeture
window.addEventListener('unload', function() {
    clearInterval(AppState.updateInterval);
    clearInterval(AppState.aisUpdateInterval);
});

// ==============================================
// 20. INFORMATIONS DE DÉBOGAGE
// ==============================================
console.log('Position initiale:', CONFIG.MAP.initialPosition);
console.log('Application maritime initialisée avec succès');
document.getElementById("intervalLabel").textContent = " x " + CONFIG.UPDATES.positionInterval/1000 + " sec";

// ==============================================
// 21. FENÊTRE DE LA LISTE DES INSTRUMENTS NMEA 2000
// ==============================================
async function loadConfig() {
  const response = await fetch('/api/configuration');
  const data = await response.json();

  const list = document.getElementById('f_config-list');
  list.innerHTML = '';

  for (const [source, config] of Object.entries(data)) {
    const item = document.createElement('li');
    item.innerHTML = `<span><strong>Adresse:</strong> &nbsp;${source} &nbsp;  ${config}</span>`;
    list.appendChild(item);
  }
};

let configInterval = null;


document.getElementById('f_config').addEventListener('click', async (event) => {
  const btn = event.currentTarget;

  // Toggle visuel
  btn.classList.toggle('active');

  // Mise à jour de l'état global
  AppState.IsIntervenantVisible = !AppState.IsIntervenantVisible;

  // Mise à jour du title
  btn.title = AppState.IsIntervenantVisible
    ? "Masquer la fenêtre 'liste des instruments'"
    : "Afficher la liste des instruments";

  // Si on masque la fenêtre
  if (!AppState.IsIntervenantVisible) {
    document.getElementById('f_modal').style.display = 'none';

    // Stopper le rafraîchissement automatique
    if (configInterval) {
      clearInterval(configInterval);
      configInterval = null;
    }

    return;
  }

  // Sinon : on affiche et on charge
  document.getElementById('f_modal').style.display = 'flex';

  // Chargement initial
  await loadConfig();

  // Rafraîchissement toutes les 20 secondes
  configInterval = setInterval(async () => {
    await loadConfig();
  }, 20000);
});




 // Envoi la commande PGN 59904
document.getElementById('f_raf-button').addEventListener('click', async () => {
    try {
        const response = await fetch('/send', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        });

        const result = await response.json();
        console.log('Réponse du backend :', result);
      } catch (error) {
            console.error('Erreur lors de l’appel à send:', error);
      }
  await new Promise(resolve => setTimeout(resolve, 2000));

  await loadConfig();

});


const btn = document.getElementById("f_raf-button");
const status = document.getElementById("f_raf-status");

btn.addEventListener("click", () => {
    if (!AppState.IsConnected){
        showNotification("Vous n'êtes pas connecté au NMEA 2000", 'error');
        return;
    }
    btn.style.display = "none";
    status.style.display = "inline";

    setTimeout(() => {
        status.style.display = "none";
        btn.style.display = "inline";
    }, 6000);
});
