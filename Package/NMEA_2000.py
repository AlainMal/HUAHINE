import asyncio
import math
from Package.Constante import *
from Package.MMSI import *

# **********************************************************************************************************************
#       Programme d'analyse des trames du bus CAN et les transforment en NMEA 2000
# **********************************************************************************************************************

# Cette classe permet de déduire le PGN, sa source, son destinataire, sa priorité et la définition des octets.
class NMEA2000:
    ADRESSES_NOEUD = list(range(253))
    nbr = 0
    coord = 0
    cog_sog = 0
    windTrue = 0
    windApp = 0
    def __init__(self,main_window, coordinates:dict, configuration:dict):
        # Ensemble des adresses de nœuds détectées sur le bus
        self.adresses_detectees = set()
        self._coordinates = coordinates
        self._main_window = main_window
        # Pour récupérer les configurations des sources
        self._configuration = configuration

        self._mmsi = None
        self._name = None
        self._latitude = None
        self._longitude = None
        self._sog = None
        self._cog = None
        self._latitudeMoi = None
        self._longitudeMoi = None
        self._windSpeedMoiTrue = None
        self._windAngleMoiTrue = None
        self._windSpeedMoiApp = None
        self._windAngleMoiApp = None
        self._sogMoi = None
        self._cogMoi = None
        self._headingMoi = None
        self._stwMoi = None
        # Ajouts pour gestion avancée du cap
        self._headingMagMoi = None
        self._headingTrueMoi = None
        self._headingUsedMoi = None
        self._headingSource = None  # '127250-TRUE', '127250-MAG', 'COG', etc.
        self._magVarMoi = None
        self._classe = None
        self._mmsi_courant = None  # Stocke le MMSI en cours de traitement

        self._definition = None
        print("NMEA2000 initialisé.")
        self._table = []
        self.mmsi = MMSI(self._table)

        self._analyse0 = None
        self._analyse1 = None
        self._analyse2 = None
        self._analyse3 = None
        self._analyse4 = None
        self._analyse5 = None
        self._analyse6 = None
        self._analyse7 = None

        self._pgn1 = None
        self._pgn2 = None
        self._pgn3 = None
        self._definition = None
        self._valeurChoisieTab = None
        self._valeurChoisie2 = None
        self._valeurChoisie1 = None
        self._valeurChoisie3 = None
        self._priorite = None
        self._destination = None
        self._source = None
        self._pgn = None

        # Initialisation à faire une seule fois (dans __init__ )
        self._buffer_cog = []
        self._buffer_sog = []

        self._buffer_lat = []
        self._buffer_lon = []

        self._buffer_w_speed_true = []
        self._buffer_w_angle_true = []

        self._buffer_w_speed_app = []
        self._buffer_w_angle_app = []

        self._buffer_hdg = []
        self._buffer_stw = []
        self._buffer_magvar = []
        self._hdg_ref = None

        # Dictionnaire pour stocker les données temporaires par MMSI (AIS)
        self._temp_data = {}
        # Dictionnaire séparé pour assembler les configurations produit (PGN 126996)
        self._temp_config = {}

        # self._coor = None

        # Défini la taille de la mémoire, elle est calculé au plus juste, mais c'est la plus rapide.
        nombre_octets = 8
        nombre_pgn = 25     # On a plus de PGN mais
        nombre_trames = 36  # On limite la valeur à 36 le nombre maximum de trames sur le même PGN.
        valeur_defaut = 0

        # Crée une table 3D fixe remplie avec la valeur par défaut
        self.memoire = [[[valeur_defaut for _ in range(nombre_trames)]
                         for _ in range(nombre_pgn)]
                        for _ in range(nombre_octets)]

    # ========================== Méthodes de récupération des valeurs dans l'ID ========================================
    # On récupère le PGN, puis la source ensuite la destination ensuite la priorité.
    def pgn(self, id_msg):
        try:
            pf = (id_msg & 0x00FF0000) >> 16  # Extraire les bits PF (byte 2)
            ps = (id_msg & 0x0000FF00) >> 8  # Extraire les bits PS (byte 1)
            dp = (id_msg & 0x03000000) >> 24  # Extraire les bits DP (bits 24-25)

            if pf < 240:  # Si PF < 240, c'est un message point à point
                self._pgn = (dp << 16) | (pf << 8)  # Construire le PGN

            else:  # Sinon, c'est un message global (broadcast)
                self._pgn = (dp << 16) | (pf << 8) | ps

            return self._pgn

        except Exception as e:
            print(f"Erreur dans la méthode 'pgn' : {e}")
            raise

    def source(self,id_msg):
        self._source = id_msg & 0xFF
        return self._source

    def destination(self,id_msg):
        if ((id_msg & 0xFF0000) >> 16) < 240:
            self._destination = (id_msg &  0x00FF00) >> 8
        else:
            self._destination = (id_msg & 0xFF0000) >> 16

        return self._destination

    def priorite(self,id_msg):
        self._priorite = (id_msg & 0x1C000000) >> 26
        return self._priorite

    # Renvoi un tuple contenant toutes les variables contenus dans l'id
    def id(self,id_msg):
        return self.pgn(id_msg), self.source(id_msg) ,self.destination(id_msg),self.priorite(id_msg)
    # ================================== FIN DES MÉTHODES POUR L'ID ====================================================

    # ================================= Méthodes de gestion de la mémoire ==============================================
    def set_memoire(self, numero_d_octet, numero_pgn, numero_de_trame, valeur):
        self.memoire[numero_d_octet][numero_pgn][numero_de_trame] = valeur

    def get_memoire(self, numero_d_octet, numero_pgn, numero_de_trame):
        return self.memoire[numero_d_octet][numero_pgn][numero_de_trame]
    # ======================================== Fin des mémoires ========================================================

    def get_all_ais_ships(self):
        """
        Récupère la liste complète des bateaux AIS
        """
        return self.mmsi.get_all_ships()

    async def get_participants(self):
        """
        Retourne la liste des adresses de nœuds détectées (participants) sur le bus CAN.
        """
        try:
            # Retourner une liste triée pour stabilité d'affichage/itération
            return sorted(self.adresses_detectees)
        except Exception:
            return []

    # ============================= Méthodes de récupération des valeurs des octets ====================================
    def octets(self,pgn,source,datas):
        self._pgn = pgn
        self._source = source  # Avoir la source, utile pour remplir le dictionnaire
        self._pgn1 = None
        self._pgn2 = None
        self._pgn3 = None
        self._valeurChoisieTab = None
        self._valeurChoisie2 = None
        self._valeurChoisie1 = None
        self._valeurChoisie3 = None
        self._definition = None
        # z = Numéro de trame pour le même PGN.

        if source not in self.ADRESSES_NOEUD:
            raise ValueError(f"Adresse de nœud invalide : {source}")
        self.adresses_detectees.add(source)

        # log_ligne(f"SOURCE = {self._source} du PGN {self._pgn}")

        try:
            match int(self._pgn):
                case 129038:
                    # Sécuriser l'accès aux octets : certaines trames peuvent être partielles (< 8 octets)
                    if not datas or len(datas) < 1:
                        # Trame trop courte, on ignore
                        return (None,) * 8

                    z = (datas[0] & 0x1F)
                    # Ce PGN utilise 4 trames : z = 0..3. On ignore les autres valeurs anormales.
                    if z > 3:
                        return (None,) * 8

                    self._valeurChoisie1 = "N° " + str(z)
                    self._pgn1 = "AIS Position Class A"

                    if z == 0:
                        # Besoin des octets 3..7
                        if len(datas) < 8:
                            return (None,) * 8
                        self._valeurChoisie2 = datas[6] << 24 | datas[5] << 16 | datas[4] << 8 | datas[3]
                        self._pgn2 = "MMSI"
                        mmsi_courant = str(self._valeurChoisie2)
                        self._mmsi_courant = mmsi_courant  # Stocker le MMSI courant

                        # Initialiser ou réinitialiser les données temporaires pour ce MMSI
                        self._temp_data[mmsi_courant] = {
                            'mmsi': mmsi_courant,
                            'latitude': None,
                            'longitude': None,
                            'cog': None,
                            'sog': None,
                            'name': None,
                            'classe': 'A',
                            'long': None,
                            'large': None
                        }
                        self._mmsi = mmsi_courant
                        self._classe = "A"
                        # Stocker l'octet 7 pour reconstituer la longitude (trame suivante)
                        self.set_memoire(MEMOIRE_PGN_a7, PGN_129038, z + 1, datas[7])

                    elif z == 1:
                        # Besoin des octets 1..7
                        if len(datas) < 8:
                            return (None,) * 8
                        self._valeurChoisie2 = "{:.6f}".format((datas[3] << 24 | datas[2] << 16 | datas[1] << 8
                                                                | self.get_memoire(MEMOIRE_PGN_a7, PGN_129038, z))
                                                               * (10 ** -7))
                        self._pgn2 = "AIS_A Longitude"

                        self._valeurChoisie3 = "{:.6f}".format((datas[7] << 24 | datas[6] << 16
                                                                | datas[5] << 8 | datas[4]) * (10 ** -7))
                        self._pgn3 = "AIS_A Latitude"

                        # Mettre à jour les données temporaires pour tous les MMSI en attente
                        for mmsi_data in self._temp_data.values():
                            if mmsi_data['latitude'] is None:
                                mmsi_data['latitude'] = self._valeurChoisie3
                                mmsi_data['longitude'] = self._valeurChoisie2

                        self._latitude = self._valeurChoisie3
                        self._longitude = self._valeurChoisie2

                    elif z == 2:
                        # Besoin des octets 2..5
                        if len(datas) < 6:
                            return (None,) * 8
                        self._valeurChoisie2 = "{:.2f}".format((datas[3] << 8 | datas[2]) * 0.0001 * 180 / math.pi)
                        self._pgn2 = "AIS_A COG"

                        self._valeurChoisie3 = "{:.2f}".format((datas[5] << 8 | datas[4]) * 0.01 * 1.94384449)
                        self._pgn3 = "AIS_A SOG"

                        # Mettre à jour les données temporaires pour tous les MMSI en attente
                        for mmsi_data in self._temp_data.values():
                            if mmsi_data['cog'] is None:
                                mmsi_data['cog'] = self._valeurChoisie2
                                mmsi_data['sog'] = self._valeurChoisie3

                        self._cog = self._valeurChoisie2
                        self._sog = self._valeurChoisie3

                    elif z == 3:
                        # Besoin des octets 2..3
                        if len(datas) < 4:
                            return (None,) * 8

                        self._valeurChoisie2 = "{:.2f}".format((datas[3] << 8 | datas[2]) * 0.0001 * 180 / math.pi)
                        self._pgn2 = "AIS_A Heading"

                        # Une fois toutes les données reçues, mettre à jour la base de données
                        for mmsi, data in list(self._temp_data.items()):
                            if all(v is not None for v in [data['latitude'], data['longitude'],
                                                           data['cog'], data['sog']]):
                                self.mmsi.mmsi_navires(
                                    ais_mmsi=data['mmsi'],
                                    latitude=data['latitude'],
                                    longitude=data['longitude'],
                                    cog=data['cog'],
                                    sog=data['sog'],
                                    classe=data['classe'],
                                    long=data['long'],
                                    large=data['large']
                                )
                                # Supprimer les données temporaires une fois traitées
                                del self._temp_data[mmsi]

                case 129025:
                    self._valeurChoisie1 = "{:.6f}".format((datas[3] << 24 | datas[2] << 16
                                                            | datas[1] << 8 | datas[0]) * (10 ** -7))
                    self._pgn1 = "Latitude"

                    self._valeurChoisie2 = "{:.6f}".format((datas[7] << 24 | datas[6] << 16
                                                            | datas[5] << 8 | datas[3]) * (10 ** -7))
                    self._pgn2 = "Longitude"

                    # Pour Analyse.
                    self._analyse3 = "Coord " + self._pgn1
                    self._analyse2 = "Coord " + self._pgn1
                    self._analyse1 = "Coord " + self._pgn1
                    self._analyse0 = "Coord " + self._pgn1
                    self._analyse7 = "Coord " + self._pgn2
                    self._analyse6 = "Coord " + self._pgn2
                    self._analyse5 = "Coord " + self._pgn2
                    self._analyse4 = "Coord " + self._pgn2

                    self._latitudeMoi = self._valeurChoisie1
                    self._longitudeMoi = self._valeurChoisie2
                    # Mise à jour des coordonnées sur la carte environ toutes les secondes (1/10 scrutations).

                    # Toutes les 10 mesures (~1s)
                    if NMEA2000.coord % 10 == 0:
                        try:
                            if None not in (self._latitudeMoi, self._longitudeMoi, self._cogMoi, self._sogMoi):
                                asyncio.create_task(
                                    self.safe_update_coordinates(
                                        latitude=self._latitudeMoi,
                                        longitude=self._longitudeMoi,
                                        cog=self._cogMoi,
                                        sog=self._sogMoi
                                    )
                                )
                        except Exception as e:
                            print(f"Erreur lors de la création de la tâche asynchrone : {e}")

                    # Incrémenter le compteur
                    NMEA2000.coord += 1

                case 130306:
                    # Conversion des données
                    self._valeurChoisie1 = (datas[2] << 8 | datas[1]) * 0.01 * 1.94384449  # vitesse vent en nœuds
                    self._pgn1 = "Vitesse du vent"
                    self._valeurChoisie2 = (datas[4] << 8 | datas[3]) * 0.0001 * 180 / math.pi  # angle vent en degrés
                    self._pgn2 = "Angle du vent"

                    self._valeurChoisieTab = datas[5] & 0x07
                    self._definition = VENT[self._valeurChoisieTab]

                    # On ne prend pas en compte, le vrai vent est calculé par la vitesse sur fond
                    """
                    # Stockage dans le bon buffer selon le type de vent
                    if self._valeurChoisieTab == 4:  # Vent vrai
                        self._buffer_w_speed_true.append(self._valeurChoisie1)
                        self._buffer_w_angle_true.append(self._valeurChoisie2)

                        if NMEA2000.windTrue % 10 == 0: # environ toutes les secondes
                            if self._buffer_w_speed_true and self._buffer_w_angle_true:
                                self._windSpeedMoiTrue = sum(self._buffer_w_speed_true) / len(self._buffer_w_speed_true)
                                self._windAngleMoiTrue = circular_mean_deg(self._buffer_w_angle_true)

                                self._buffer_w_speed_true.clear()
                                self._buffer_w_angle_true.clear()

                                try:
                                    asyncio.create_task(
                                        self.safe_update_coordinates(
                                            w_speed_true=self._windSpeedMoiTrue,
                                            w_angle_true=self._windAngleMoiTrue
                                        )
                                    )
                                except Exception as e:
                                    print(f"Erreur lors de la tâche vent vrai : {e}")

                        NMEA2000.windTrue += 1
                        """

                    # On prend en compte le vrai vent calculé par le SOG
                    if self._valeurChoisieTab == 2:  # Vent apparent
                        self._buffer_w_speed_app.append(self._valeurChoisie1)
                        self._buffer_w_angle_app.append(self._valeurChoisie2)

                        if NMEA2000.windApp % 2 == 0:
                            if self._buffer_w_speed_app and self._buffer_w_angle_app:
                                self._windSpeedMoiApp = sum(self._buffer_w_speed_app) / len(self._buffer_w_speed_app)
                                self._windAngleMoiApp = circular_mean_deg(self._buffer_w_angle_app)

                                self._buffer_w_speed_app.clear()
                                self._buffer_w_angle_app.clear()
                            # Choisir les meilleures sources pour le calcul du vent réel
                            use_hdg_stw = (self._headingMoi is not None and self._stwMoi is not None)
                            speed_bateau = self._stwMoi if use_hdg_stw else self._sogMoi
                            cap_fond = self._cogMoi if self._cogMoi is not None else (self._headingMoi or 0.0)
                            if None not in (self._windSpeedMoiApp, self._windAngleMoiApp, speed_bateau, cap_fond):
                                try:
                                    vt_speed, vt_angle_earth, vt_angle_rel = true_wind(
                                        VA=self._windSpeedMoiApp,
                                        AWA=self._windAngleMoiApp,
                                        SOG=speed_bateau,
                                        COG=cap_fond,
                                        HDG=self._headingMoi,
                                        boat_vector_use_hdg=use_hdg_stw
                                    )
                                    # Publier la vitesse et l'angle relatif pour l'affichage Tribord/Bâbord
                                    asyncio.create_task(
                                        self.safe_update_coordinates(
                                            w_speed_app=self._windSpeedMoiApp,
                                            w_angle_app=self._windAngleMoiApp,
                                            w_speed_true=vt_speed,
                                            w_angle_true=vt_angle_rel
                                        )
                                    )

                                except Exception as e:
                                    print(f"Erreur lors de la tâche vent apparent : {e}")

                        NMEA2000.windApp += 1

                    # Pour Analyse.
                    self._analyse2 = "Nds " + self._pgn1
                    self._analyse1 = "Nds " + self._pgn1
                    self._analyse4 = "Deg " + self._pgn2
                    self._analyse3 = "Deg " + self._pgn2
                    self._analyse5 = "Table: sur 3 bits"

                case 129026:
                    self._valeurChoisie1 = "{:.2f}".format((datas[3] << 8 | datas[2]) * 0.0001 * 180 / math.pi)
                    self._pgn1 = "COG"

                    self._valeurChoisie2 = "{:.2f}".format((datas[5] << 8 | datas[4]) * 0.01 * 1.94384449)
                    self._pgn2 = "SOG"

                    # Pour Analyse.
                    self._analyse3 = "Deg " + self._pgn1
                    self._analyse2 = "Deg " + self._pgn1
                    self._analyse5 = "Nds " + self._pgn2
                    self._analyse4 = "Nds " + self._pgn2

                    # Ajouter les valeurs à chaque passage
                    # Stocker en float pour pouvoir calculer les moyennes
                    self._buffer_cog.append(float(self._valeurChoisie1))
                    self._buffer_sog.append(float(self._valeurChoisie2))

                    # Toutes les 4 mesures (~1s)
                    if NMEA2000.cog_sog % 4 == 0:
                        if self._buffer_cog and self._buffer_sog:
                            # Calcul des moyennes
                            self._cogMoi = sum(self._buffer_cog) / len(self._buffer_cog)
                            self._sogMoi = sum(self._buffer_sog) / len(self._buffer_sog)

                            # Vider les buffers
                            self._buffer_cog.clear()
                            self._buffer_sog.clear()

                            # Sélection du cap utilisé
                            try:
                                # Par défaut, on privilégie le heading calculé depuis 127250 si disponible
                                heading_used = None
                                heading_source = None
                                if self._headingUsedMoi is not None:
                                    heading_used = self._headingUsedMoi
                                    heading_source = self._headingSource or "127250"
                                else:
                                    # Fallback: utiliser COG comme proxy de heading si on avance assez vite
                                    try:
                                        sog_val = float(self._sogMoi) if self._sogMoi is not None else 0.0
                                    except Exception:
                                        sog_val = 0.0
                                    if sog_val >= 1.5 and self._cogMoi is not None:
                                        self._headingTrueMoi = float(self._cogMoi)
                                        if self._magVarMoi is not None:
                                            self._headingMagMoi = (self._headingTrueMoi - self._magVarMoi) % 360.0
                                            if self._headingMagMoi < 0:
                                                self._headingMagMoi += 360.0
                                        heading_used = self._headingTrueMoi
                                        heading_source = "COG"
                                if None not in (self._latitudeMoi, self._longitudeMoi, self._cogMoi, self._sogMoi):
                                    asyncio.create_task(
                                        self.safe_update_coordinates(
                                            latitude=self._latitudeMoi,
                                            longitude=self._longitudeMoi,
                                            cog=self._cogMoi,
                                            sog=self._sogMoi,
                                            heading_used=heading_used if heading_used is not None else self._headingUsedMoi,
                                            heading_true=self._headingTrueMoi,
                                            heading_mag=self._headingMagMoi,
                                            heading_source=heading_source or self._headingSource
                                        )
                                    )
                            except Exception as e:
                                print(f"Erreur lors de la création de la tâche asynchrone : {e}")

                    # Incrémenter le compteur
                    NMEA2000.cog_sog += 1

                case 127250:
                    self._valeurChoisie1 = "{:.2f}".format((datas[2] << 8 | datas[1]) * 0.0001 * 180 / math.pi)
                    self._pgn1 = "Heading"

                    # Référence (2 bits) dans l'octet 7 selon NMEA2000: 0=True, 1=Magnetic, autres=Unknown
                    try:
                        ref_bits = datas[7] & 0x03
                        if ref_bits == 0:
                            self._hdg_ref = "TRUE"
                        elif ref_bits == 1:
                            self._hdg_ref = "MAG"
                        else:
                            self._hdg_ref = "UNKNOWN"
                    except Exception:
                        self._hdg_ref = None

                    # Bufferiser et moyenner périodiquement (moyenne circulaire)
                    try:
                        self._buffer_hdg.append(float(self._valeurChoisie1))
                        if len(self._buffer_hdg) >= 5:
                            self._headingMoi = circular_mean_deg(self._buffer_hdg)
                            self._buffer_hdg.clear()
                    except Exception as e:
                        print(f"Erreur buffer heading: {e}")

                    # Calculer heading True/Mag en fonction de la référence et de la variation
                    try:
                        if self._headingMoi is not None and self._hdg_ref is not None:
                            if self._hdg_ref == "TRUE":
                                self._headingTrueMoi = self._headingMoi
                                if self._magVarMoi is not None:
                                    val = (self._headingTrueMoi - self._magVarMoi) % 360.0
                                    if val < 0:
                                        val += 360.0
                                    self._headingMagMoi = val
                            elif self._hdg_ref == "MAG":
                                self._headingMagMoi = self._headingMoi
                                if self._magVarMoi is not None:
                                    val = (self._headingMagMoi + self._magVarMoi) % 360.0
                                    if val < 0:
                                        val += 360.0
                                    self._headingTrueMoi = val
                        # Choisir un heading utilisé
                        if self._headingTrueMoi is not None:
                            self._headingUsedMoi = self._headingTrueMoi
                            self._headingSource = "127250-TRUE"
                        elif self._headingMagMoi is not None:
                            self._headingUsedMoi = self._headingMagMoi
                            self._headingSource = "127250-MAG"
                    except Exception as e:
                        print(f"Erreur calcul heading true/mag: {e}")

                    # Pour Analyse.
                    self._analyse2 = "Deg " + self._pgn1
                    self._analyse1 = "Deg " + self._pgn1

                    self._analyse4 = "Deg Déviation"
                    self._analyse3 = "Deg Déviation"
                    self._analyse6 = "Deg Variation"
                    self._analyse5 = "Deg Variation"
                    self._analyse7 = "Référence 2 bits"

                case 128267:
                    self._valeurChoisie1 = "{:.2f}".format((datas[4] << 24 | datas[3] << 16
                                                            |  datas[2] << 8 |  datas[1]   )  * 0.01)
                    self._pgn1 = "Profondeur"

                    # Pour Analyse.
                    self._analyse4 = "m " + self._pgn1
                    self._analyse3 = "m " + self._pgn1
                    self._analyse2 = "m " + self._pgn1
                    self._analyse1 = "m " + self._pgn1
                    self._analyse6 = "Sous la quille"
                    self._analyse5 = "Sous la quille"

                case 130312:
                    self._valeurChoisie1 = "{:.2f}".format((datas[4] << 8 | datas[3])  * 0.01 - 273.15)
                    self._pgn1 = "Température"

                    self._valeurChoisieTab = datas[2]
                    self._definition = TEMPERATURE[self._valeurChoisieTab]

                    # Pour Analyse.
                    self._analyse4 = "°C " + self._pgn1
                    self._analyse3 = "°C " + self._pgn1
                    self._analyse6 = "°C Régler la temp."
                    self._analyse5 = "°C Régler la temp."

                case 130316:
                    self._valeurChoisie1 = "{:.2f}".format((datas[5] << 16 | datas[4] << 8 | datas[3]) * 0.01 - 273.15)
                    self._pgn1 = "Température étendue"

                    self._valeurChoisieTab = datas[2]
                    self._definition = TEMPERATURE[self._valeurChoisieTab]

                    # Pour Analyse.
                    self._analyse5 = "°C " + self._pgn1
                    self._analyse4 = "°C " + self._pgn1
                    self._analyse3 = "°C " + self._pgn1
                    self._analyse2 = "Table Temp."

                case 130310:
                    self._pgn1 = "Température Mer"
                    if datas[2] & 0xEF != 0xEF:
                        self._valeurChoisie1 = "{:.2f}".format((datas[2] << 8 | datas[1]) * 0.01 - 273.15)

                    self._pgn2 = "Température de l'air"
                    if datas[4] & 0xEF != 0xEF:
                        if datas[4] & 0xEf != 0xEF:
                            self._valeurChoisie2 = "{:.2f}".format((datas[4] << 8 | datas[3]) * 0.01 - 273.15)

                    self._pgn3 = "Pression atmosphérique"
                    if datas[6] & 0xEF != 0xEF:
                        self._valeurChoisie3 = "{:.2f}".format((datas[6] << 8 | datas[5]))

                    # Pour Analyse.
                    self._analyse2 = "°C " + self._pgn1
                    self._analyse1 = "°C " + self._pgn1
                    self._analyse4 = "°C " + self._pgn2
                    self._analyse3 = "°C " + self._pgn2
                    self._analyse6 = "mBar " + self._pgn3
                    self._analyse5 = "mBar " + self._pgn3

                case 128259:
                    self._pgn1 = "Vitesse surface"
                    if datas[2] & 0xEf != 0xEF:
                        self._valeurChoisie1 = "{:.2f}".format((datas[2] << 8 | datas[1]) * 0.01 * 1.94384449)
                        # Bufferiser STW et moyenner périodiquement
                        try:
                            self._buffer_stw.append(float(self._valeurChoisie1))
                            if len(self._buffer_stw) >= 5:
                                self._stwMoi = sum(self._buffer_stw) / len(self._buffer_stw)
                                self._buffer_stw.clear()
                        except Exception as e:
                            print(f"Erreur buffer STW: {e}")

                    self._pgn2 = "Vitesse fond"
                    if datas[4] & 0xEf != 0xEF:
                        self._valeurChoisie2 = "{:.2f}".format((datas[4] << 8 | datas[3]) * 0.01 * 1.94384449)

                    self._valeurChoisieTab = (datas[5])
                    self._definition = WATER_SPEED[self._valeurChoisieTab]


                    # Pour Analyse.
                    self._analyse2 = "Nds " + self._pgn1
                    self._analyse1 = "Nds " + self._pgn1
                    self._analyse4 = "Nds " + self._pgn2
                    self._analyse3 = "Table 3 bits"
                    self._analyse5 = "Table 3 bits"

                case 127508:
                    self._pgn1 = "Volts Batterie"
                    if (datas[2] <<8 | datas[1]) != 0x7FFF:
                        self._valeurChoisie1 = "{:.2f}".format((datas[2] << 8 | datas[1]) * 0.01)

                    self._pgn2 = "Ampères Batterie"
                    raw_value = ((datas[4] << 8) | datas[3])
                    if raw_value != 0x7FFF:
                        self._valeurChoisie2 = "{:.2f}".format((raw_value if raw_value < 0x8000 else raw_value - 0x10000) *0.1)


                    self._pgn3 = "Température Batterie"
                    if datas[6] & 0xEf != 0xEF:
                        self._valeurChoisie3 = "{:.2f}".format((datas[6] << 8 | datas[5]) * 0.01 - 273.15)

                    # Pour Analyse.
                    self._analyse2 = "Volts " + self._pgn1
                    self._analyse1 = "Volts " + self._pgn1
                    self._analyse4 = "Amp " + self._pgn2
                    self._analyse3 = "Amp " + self._pgn2
                    self._analyse6 = "°C " + self._pgn3
                    self._analyse5 = "°C " + self._pgn3

                case 129794:
                    z = (datas[0] & 0x1F)
                    self._valeurChoisie1 = "N° " + str(z)
                    self._pgn1 = "AIS Données classe A"

                    if z == 0:
                        self._valeurChoisie2 = datas[6] << 24 | datas[5] << 16 | datas[4] << 8 | datas[3]
                        self._pgn2 = "MMSI"

                        mmsi_courant = str(self._valeurChoisie2)
                        self._mmsi_courant = mmsi_courant  # Stocker le MMSI courant

                        # Initialiser ou réinitialiser les données temporaires pour ce MMSI
                        self._temp_data[mmsi_courant] = {
                            'mmsi': mmsi_courant,
                            'latitude': None,
                            'longitude': None,
                            'cog': None,
                            'sog': None,
                            'name': None,
                            'classe': 'A',
                            'long': None,
                            'large': None
                        }
                        self._mmsi = mmsi_courant
                        self._classe = "A"

                    elif z == 1:
                        self._valeurChoisie2 = "".join([chr(datas[i]) for i in range(4, 8)])
                        self._pgn2 = "Indicatif"

                    elif z == 2:
                        self._valeurChoisie2 = "".join([chr(datas[i]) for i in range(1, 4)])
                        self._pgn2 = "Indicatif"

                        self._valeurChoisie3 = "".join([chr(datas[i]) for i in range(4, 8)])
                        self._pgn3 = "Nom du navire"
                        # Mettre à jour les données temporaires pour tous les MMSI en attente
                        for mmsi_data in self._temp_data.values():
                            if mmsi_data['name'] is None:
                                mmsi_data['name'] = self._valeurChoisie3

                    elif z in [3, 4]:
                        self._valeurChoisie3 = "".join([chr(datas[i]) for i in range(1, 8)])
                        self._pgn3 = "Nom du navire"

                        self._name = self._valeurChoisie3

                        # Mettre à jour le nom pour tous les MMSI en attente
                        for mmsi_data in self._temp_data.values():
                            if mmsi_data['name'] is not None:  # On vérifie que le nom a déjà été initialisé
                                mmsi_data['name'] += self._valeurChoisie3
                                self._name = mmsi_data['name']  # Mise à jour du nom complet

                    elif z == 5:
                        self._valeurChoisie2 = "{:.1f}".format((datas[5] << 8 | datas[4]) * 0.1)
                        self._pgn2 = "Longueur"

                        self._valeurChoisie3 = "{:.1f}".format((datas[7] << 8 | datas[6]) * 0.1)
                        self._pgn3 = "Largeur"

                        # Mettre à jour les dimensions UNIQUEMENT pour le MMSI courant
                        if self._mmsi_courant and self._mmsi_courant in self._temp_data:
                            if self._temp_data[self._mmsi_courant]['long'] is None:
                                self._temp_data[self._mmsi_courant]['long'] = self._valeurChoisie2
                                self._temp_data[self._mmsi_courant]['large'] = self._valeurChoisie3 

                    elif z == 6:
                        self._valeurChoisie2 = "{:.2f}".format((datas[3] << 8 | datas[2]) * 0.0001 / 1.85)
                        self._pgn2 = "Distance"

                        self._valeurChoisie3 = "{:.2f}".format((datas[5] << 8 | datas[4]) * 0.0001 / 1.85)
                        self._pgn3 = "Distance Proue"

                    elif z == 7:
                        self._valeurChoisie2 = "".join([chr(datas[i]) for i in range(6, 8)])
                        self._pgn2 = "Destination"

                    elif z in [8, 9]:
                        self._valeurChoisie2 = "".join([chr(datas[i]) for i in range(1, 8)])
                        self._pgn2 = "Destination"

                        if z == 9:
                            # Une fois toutes les données reçues, mettre à jour la base de données
                            for mmsi, data in list(self._temp_data.items()):
                                if all(v is not None for v in [data['name'], data['long'], data['large']]):
                                    nom = data['name'].rstrip('\x00 ').strip()
                                    self.mmsi.mmsi_navires(
                                        ais_mmsi=data['mmsi'],
                                        name=nom,
                                        long=data['long'],
                                        large=data['large']
                                    )
                                    # Supprimer les données temporaires une fois traitées
                                    del self._temp_data[mmsi]

                case 129809:
                    z = (datas[0] & 0x1F)
                    self._valeurChoisie1 = "N° " + str(z)
                    self._pgn1 = "AIS Données classe B"

                    if z == 0:
                        # Extraire MMSI et initialiser la structure temporaire AVANT d'assembler le nom
                        self._valeurChoisie2 = datas[6] << 24 | datas[5] << 16 | datas[4] << 8 | datas[3]
                        self._pgn2 = "MMSI"

                        mmsi_courant = str(self._valeurChoisie2)
                        self._mmsi_courant = mmsi_courant  # Stocker le MMSI courant

                        # Initialiser ou réinitialiser les données temporaires pour ce MMSI
                        self._temp_data[mmsi_courant] = {
                            'mmsi': mmsi_courant,
                            'latitude': None,
                            'longitude': None,
                            'cog': None,
                            'sog': None,
                            'name': None,
                            'classe': 'B',
                            'long': None,
                            'large': None
                        }
                        self._mmsi = mmsi_courant
                        self._classe = "B"

                        # Premier caractère du nom (partie A)
                        self._valeurChoisie3 = chr(datas[7])
                        self._pgn3 = "Nom du navire"

                        # Initialiser le nom pour le MMSI courant
                        if self._mmsi_courant in self._temp_data and self._temp_data[self._mmsi_courant]['name'] is None:
                            self._temp_data[self._mmsi_courant]['name'] = self._valeurChoisie3

                    elif z == 1:
                        # Suite du nom (partie A)
                        self._valeurChoisie3 = "".join([chr(datas[i]) for i in range(1, 8)])
                        self._pgn3 = "Nom du navire"

                        # Mettre à jour le nom UNIQUEMENT pour le MMSI courant
                        if self._mmsi_courant in self._temp_data:
                            if self._temp_data[self._mmsi_courant]['name'] is None:
                                self._temp_data[self._mmsi_courant]['name'] = self._valeurChoisie3
                            else:
                                self._temp_data[self._mmsi_courant]['name'] += self._valeurChoisie3

                    elif z == 2:
                        # Fin du nom (partie A)
                        self._valeurChoisie3 = "".join([chr(datas[i]) for i in range(1, 6)])
                        self._pgn3 = "Nom du navire"

                        # Mettre à jour le nom UNIQUEMENT pour le MMSI courant
                        if self._mmsi_courant in self._temp_data:
                            if self._temp_data[self._mmsi_courant]['name'] is None:
                                self._temp_data[self._mmsi_courant]['name'] = self._valeurChoisie3
                            else:
                                self._temp_data[self._mmsi_courant]['name'] += self._valeurChoisie3

                    elif z == 3:
                        # Une fois toutes les données reçues, mettre à jour la base de données
                        for mmsi, data in list(self._temp_data.items()):
                            if data['name'] is not None:
                                # Nettoyer les caractères de fin éventuels (espaces/NULL)
                                nom = data['name'].rstrip('\x00 ').strip()
                                self.mmsi.mmsi_navires(
                                    ais_mmsi=data['mmsi'],
                                    name=nom
                                )
                                # Supprimer les données temporaires une fois traitées
                                del self._temp_data[mmsi]

                case 129039:
                    z = (datas[0] & 0x1F)
                    self._valeurChoisie1 = "N° " + str(z)
                    self._pgn1 = "AIS Position classe B"

                    if z == 0:
                        self._valeurChoisie2 = datas[6] << 24 | datas[5] << 16 | datas[4] << 8 | datas[3]
                        self._pgn2 = "MMSI"

                        mmsi_courant = str(self._valeurChoisie2)
                        self._mmsi_courant = mmsi_courant  # Stocker le MMSI courant

                        # Initialiser ou réinitialiser les données temporaires pour ce MMSI
                        self._temp_data[mmsi_courant] = {
                            'mmsi': mmsi_courant,
                            'latitude': None,
                            'longitude': None,
                            'cog': None,
                            'sog': None,
                            'name': None,
                            'classe': 'B',
                            'long': None,
                            'large': None
                        }
                        self._mmsi = mmsi_courant
                        self._classe = "B"

                        self.set_memoire(MEMOIRE_PGN_a7, PGN_129039, z + 1, datas[7])

                    elif z == 1:
                        self._valeurChoisie2 = "{:.6f}".format((datas[3] << 24 | datas[2] << 16 | datas[1] << 8
                                                | self.get_memoire(MEMOIRE_PGN_a7,PGN_129039,z)) * (10**-7))
                        self._pgn2 = "AIS_B Longitude"

                        self._valeurChoisie3 = "{:.6f}".format((datas[7] << 24 | datas[6] << 16
                                                                | datas[5] << 8 | datas[4] ) * (10**-7))
                        self._pgn3 = "AIS_B Latitude"

                        self._latitude = self._valeurChoisie3
                        self._longitude = self._valeurChoisie2

                        # Mettre à jour les données temporaires pour tous les MMSI en attente
                        for mmsi_data in self._temp_data.values():
                            if mmsi_data['latitude'] is None:
                                mmsi_data['latitude'] = self._valeurChoisie3
                                mmsi_data['longitude'] = self._valeurChoisie2

                    elif z == 2:
                        self._valeurChoisie2 = "{:.2f}".format((datas[3] << 8 | datas[2]) * 0.0001 * 180 / math.pi)
                        self._pgn2 = "AIS_B COG"

                        self._valeurChoisie3 = "{:.2f}".format((datas[5] << 8 | datas[4]) * 0.01 * 1.94384449)
                        self._pgn3 = "AIS_B SOG"

                        self._cog = self._valeurChoisie2
                        self._sog = self._valeurChoisie3

                        # Mettre à jour les données temporaires pour tous les MMSI en attente
                        for mmsi_data in self._temp_data.values():
                            if mmsi_data['cog'] is None:
                                mmsi_data['cog'] = self._valeurChoisie2
                                mmsi_data['sog'] = self._valeurChoisie3

                    elif z == 3:
                        self._valeurChoisie2 = "{:.2f}".format((datas[3] << 8 | datas[2]) * 0.0001 * 180 / math.pi)
                        self._pgn2 = "AIS_B Heading"

                        # Une fois toutes les données reçues, mettre à jour la base de données
                        for mmsi, data in list(self._temp_data.items()):
                            if all(v is not None for v in [data['latitude'], data['longitude'],
                                                           data['cog'], data['sog']]):
                                self.mmsi.mmsi_navires(
                                    ais_mmsi=data['mmsi'],
                                    latitude=data['latitude'],
                                    longitude=data['longitude'],
                                    cog=data['cog'],
                                    sog=data['sog'],
                                    classe=data['classe']
                                )
                                # Supprimer les données temporaires une fois traitées
                                del self._temp_data[mmsi]

                case 129810:
                    z = (datas[0] & 0x1F)
                    self._valeurChoisie1 = "N° " + str(z)
                    self._pgn1 = "AIS Données classe B Part B"

                    # Mode fixe : dimensions sur sous-trame 2, conversion en mètres, application à tous
                    # units = "m"
                    units_factor = 0.1
                    # apply_all = True

                    if z == 0:
                        # Sous-trame 0: MMSI sur 4 octets (datas[3..6]) en little-endian
                        self._valeurChoisie2 = datas[6] << 24 | datas[5] << 16 | datas[4] << 8 | datas[3]
                        self._pgn2 = "MMSI"
                        mmsi_courant = str(self._valeurChoisie2)
                        self._mmsi_courant = mmsi_courant  # Stocker le MMSI courant

                        # Prépare une structure temporaire pour agréger les champs statiques du navire
                        self._temp_data[mmsi_courant] = {
                            'mmsi': mmsi_courant,
                            'latitude': None,
                            'longitude': None,
                            'cog': None,
                            'sog': None,
                            'name': None,  # pourra être alimenté via d'autres PGN ou l'indicatif
                            'classe': 'B',
                            'long': None,
                            'large': None
                        }

                    elif z == 1:
                        # Sous-trame 1: indicatif d'appel en ASCII sur 7 octets
                        self._valeurChoisie2 = "".join([chr(datas[i]) for i in range(1, 8)])
                        self._pgn2 = "Identifiant"

                    elif z == 2:
                        # Sous-trame 2: indicatif d'appel en ASCII sur 7 octets
                        self._valeurChoisie2 = "".join([chr(datas[i]) for i in range(1, 8)])
                        self._pgn2 = "Indicatif"

                    elif z == 3:
                        # Sous-trame 3 : Dimensions (Longueur / Largeur). Index fixé à 2 (suppression de la config dynamique).
                        if datas[2] != 255:
                            brut_long = (datas[2] << 8) | datas[1]
                        else:
                            brut_long=0
                        if datas[4] != 255:
                            brut_large = (datas[4] << 8) | datas[3]
                        else:
                            brut_large=0
                        self._valeurChoisie2 = "{:.1f}".format(brut_long * units_factor)
                        self._pgn2 = "Longueur"

                        self._valeurChoisie3 = "{:.1f}".format(brut_large * units_factor)
                        self._pgn3 = "Largeur"

                        # Mettre à jour les dimensions UNIQUEMENT pour le MMSI courant
                        if self._mmsi_courant and self._mmsi_courant in self._temp_data:
                            if self._temp_data[self._mmsi_courant]['long'] is None:
                                self._temp_data[self._mmsi_courant]['long'] = self._valeurChoisie2
                                self._temp_data[self._mmsi_courant]['large'] = self._valeurChoisie3

                        # Une fois les dimensions disponibles, pousser en base MMSI
                        for mmsi, data in list(self._temp_data.items()):
                            if all(v is not None for v in [data['long'], data['large']]):
                                self.mmsi.mmsi_navires(
                                    ais_mmsi=data['mmsi'],
                                    long=data['long'],
                                    large=data['large']
                                )
                                # Supprimer les données temporaires une fois traitées
                                del self._temp_data[mmsi]

                case 129029:
                    z = (datas[0] & 0x1F)
                    self._valeurChoisie1 = "N° " + str(z)
                    self._pgn1 = "Info. de position GNSS"

                    if z == 5:
                        self._valeurChoisie2 = datas[7]
                        self._pgn2 = "Nombre de satellites"

                case 129539:
                    self._pgn1 = "Horizontal Précision GNSS"
                    self._valeurChoisie1 = (datas[3] << 8 | datas[2]) * 0.01
                    self._pgn2 = "Vertical précision"
                    self._valeurChoisie2 = (datas[5] << 8 | datas[4]) * 0.01
                    self._pgn3 = "Time précision"
                    self._valeurChoisie3 = (datas[7] << 8 | datas[6]) *0.01

                case 130577:
                    z = (datas[0] & 0x0F)
                    self._valeurChoisie1 = "N° "+ str(z)
                    self._pgn1 = "Données de direction"

                    if z == 1:
                        self._pgn2 = "COG"
                        if datas[2] & 0xEF != 0xEF:
                            self._valeurChoisie2 = "{:.2f}".format((datas[2] << 8 | datas[1]) * 0.0001 * 180 / math.pi)

                        self._pgn3 = "SOG"
                        if datas[4] & 0xEF != 0xEF:
                            self._valeurChoisie3 = "{:.2f}".format((datas[4] << 8 | datas[3]) * 0.01 * 1.94384449)

                        # HEADING
                        if datas[6] & 0xEF != 0xEF:
                            self._valeurChoisieTab = "Heading : " + "{:.2f}".format((datas[6] << 8 | datas[5]) * 0.0001 * 180 / math.pi)
                            self._definition = "HEADING"

                case 127506:
                    z = (datas[0] & 0x1F)
                    self._valeurChoisie1 = "N° "+ str(z)
                    self._pgn1 = "Batteries détaillées"

                    if z == 0:
                        self._valeurChoisieTab = (datas[4])
                        self._definition = ENERGIE_DC[self._valeurChoisieTab]

                        self._valeurChoisie2 = datas[5]
                        self._pgn2 = "État de charge"

                        self._valeurChoisie3 = datas[6]
                        self._pgn3 = "État de santé"

                        self.set_memoire(MEMOIRE_PGN_a7,PGN_127506,z + 1,datas[7])

                    elif z == 1:
                        if not self.get_memoire(MEMOIRE_PGN_a7,PGN_127506,z) == 0xFF:
                            self._pgn2 = "Temps restant en minutes"
                            if datas[1] & 0xEF != 0xEF:
                                self._valeurChoisie2 = (datas[1] << 8
                                                    | self.get_memoire(MEMOIRE_PGN_a7,PGN_127506,z))

                        self._pgn3 = "Ah"
                        if datas[5] & 0xEF != 0xEF:
                            self._valeurChoisie3 = datas[4] << 8 | datas[3]

                case 126720:
                    z = (datas[0] & 0x1F)
                    self._valeurChoisie1 = "N° " + str(z)
                    self._pgn1 = "Info propriétaire"

                    if z == 0:
                        self._valeurChoisie2 = (datas[3] << 8 | datas[2]) & 0x7FF
                        self._pgn2 = "Code propriétaire"
                        self._definition = MANUFACTURE[self._valeurChoisie2]

                case 127245:
                    if datas[0] != 0xFF:
                        self._valeurChoisie1 =  "{:.2f}".format((datas[5] << 8 | datas[4]) * 0.0001 * 180 / math.pi)
                    self._pgn1 = "Ordre de barre"

                case 127251:
                    self._valeurChoisie1 =  "{:.2f}".format((datas[3] << 8 | datas[2])  * 0.00000003125 * 180 / math.pi)
                    self._pgn1 = "Vitesse de rotation"

                case 126464:
                    z = (datas[0] & 0x1F)
                    self._valeurChoisie1 = "N° " + str(datas[0] & 0x1F)
                    self._pgn1 = "Liste des PGN"

                    if (z + 3) % 3 == 0:
                        temp = (datas[5] << 16 | datas[4] << 8 | datas[3])
                        self._pgn2 = "Num PGN"
                        if not (temp < 59392 or temp > 130944 or datas[5] & 0xEF == 0xEF):
                            self._valeurChoisie2 = temp
                            self.set_memoire(MEMOIRE_PGN_a6, PGN_126464, z + 1, datas[6])
                            self.set_memoire(MEMOIRE_PGN_a7, PGN_126464, z + 1, datas[7])

                    elif (z + 2) % 3 == 0:
                        temp =  (datas[1] << 16 | self.get_memoire(MEMOIRE_PGN_a7,PGN_126464,z) << 8
                                                | self.get_memoire(MEMOIRE_PGN_a6,PGN_126464,z))
                        self._pgn2 = "Num PGN"
                        if not (temp < 59392 or temp > 130944 or datas[1] & 0xEF == 0xEF):
                            self._valeurChoisie2 = temp

                        temp = (datas[4] << 16 | datas[3] << 8 | datas[2])
                        self._pgn3 = "Num PGN"
                        if not (temp < 59392 or temp > 130944 or datas[4] & 0xEF == 0xEF):
                            self._valeurChoisie3 = temp

                        temp = (datas[7] << 16 | datas[6] << 8 | datas[5])
                        if not (temp < 59392 or temp > 130944 or datas[7] & 0xEF == 0xEF):
                            self._valeurChoisieTab = "Num PGN:"
                            self._definition = str(temp)

                    elif (z + 1) % 3 == 0:
                        temp = (datas[3] << 16 | datas[2] << 8 | datas[1])
                        self._pgn2 = "Num PGN"
                        if not (temp < 59392 or temp > 130944 or datas[3] & 0xEF == 0xEF):
                            self._valeurChoisie2 = temp

                        temp = (datas[6] << 16 | datas[5] << 8 | datas[4])
                        self._pgn3 = "Num PGN"
                        if not (temp < 59392 or temp > 130944 or datas[6] & 0xEF == 0xEF):
                            self._valeurChoisie3 = temp

                case 126993:
                    self._pgn1 = "Heart beat"
                    self._pgn2 = "Heart beat"
                    if datas[2] & 0xEF != 0xEF:
                        self._valeurChoisie1 = "{:.2f}".format((datas[2] << 8 | datas[1]) * 0.001)

                case 127505:
                    self._pgn1 = "Niveau Réservoir"
                    if datas[2] & 0xEF != 0xEF:
                        self._valeurChoisie1 = "{:.2f}".format((datas[2] << 8 | datas[1]) * 0.004)

                    self._pgn2 = "Capacité du reservoir"
                    if datas[6] & 0xEF != 0xEF:
                        self._valeurChoisie2 = "{:.2f}".format((datas[6] << 24 | datas[5] << 16
                                                                | datas[4] << 8 | datas[3]) * 0.1)

                    self._valeurChoisieTab = datas[0] & 0x0F
                    self._definition = RESERVOIR[self._valeurChoisieTab]

                case 128275:
                    # Détecte la valeur du premier octet qui définie le numéro de la trame
                    z = (datas[0] & 0x1F)
                    self._valeurChoisie1 = "N° " + str(z)
                    self._pgn1 = "Journal"

                    # deuxième octet = 1
                    if z == 1:
                        self._pgn2 = "Distance totale parcourue"
                        if datas[6] & 0xEF != 0xEF:
                            self._valeurChoisie2 = (datas[4] << 24 | datas[3] << 16 | datas[2] << 8 | datas[1])/1852

                case 129540:
                    z = (datas[0] & 0x1F)
                    self._valeurChoisie1 = "N° " + str(z)
                    self._pgn1 = "Satellites en vues"

                    if z == 0:
                        self._valeurChoisie2 = datas[4] & 0x7F
                        self._pgn2 = "Nombre de satellites"

                case 129284:
                    z = (datas[0] & 0x1F)
                    self._valeurChoisie1 = "N° " + str(z)
                    self._pgn1 = "Données Navigation"

                    if z == 4:
                        self._pgn2 ="Latitude Waypoint"
                        self._pgn3 = "Longitude Waypoint"

                case 126996:
                    z = (datas[0] & 0x1F)
                    self._valeurChoisie1 = "N° " + str(z)
                    self._pgn1 = "Information produit"
                    if z == 0:
                        if source not in self._temp_config:
                            self._temp_config[source] = {'source': self._source, 'config': None}

                        if datas[6] & 0xEF != 0xEF:
                            self._pgn2 = "Modèle"
                            self._valeurChoisie2 = "".join([chr(datas[i]) for i in range(6, 8)])
                            self._temp_config[source]['config'] = self._valeurChoisie2.replace(chr(0xFF), "")


                    elif z in [1, 2, 3, 4]:
                        self._pgn2 = "Modèle"
                        # Concatène tous les caractères utiles (ignore 0xFF et 0x00) sans conditionner à un octet précis
                        chunk_chars = []
                        for i in range(1, 8):
                            b = datas[i]
                            if b in (0xFF, 0x00):
                                continue
                            chunk_chars.append(chr(b))
                        self._valeurChoisie2 = "".join(chunk_chars)

                        if self._source in self._temp_config and self._temp_config[source]['config'] is not None:
                            self._temp_config[source]['config'] += self._valeurChoisie2
                        else:
                            # Cas rare : trame reçue sans trame 0 préalable
                            self._temp_config[source] = {'source': self._source, 'config': self._valeurChoisie2}

                    elif z in [5, 6, 7, 8]:
                        self._pgn2 = "Version"

                        # Concatène tous les caractères utiles (ignore 0xFF et 0x00) sans conditionner à un octet précis
                        chunk_chars = []
                        for i in range(1, 8):
                            b = datas[i]
                            if b in (0xFF, 0x00):
                                continue
                            chunk_chars.append(chr(b))
                        self._valeurChoisie2 = "".join(chunk_chars)

                        if self._valeurChoisie2:
                            if self._source in self._temp_config and self._temp_config[source]['config'] is not None:
                                if z == 5:
                                    self._temp_config[source]['config'] += " - <strong>&nbsp;Version:&nbsp;</strong> " + self._valeurChoisie2
                                else:
                                    self._temp_config[source]['config'] += self._valeurChoisie2
                            else:
                                # Cas rare : trame reçue sans trame 0 préalable
                                self._temp_config[source] = {'source': self._source, 'config': self._valeurChoisie2}

                    elif z in [9,10,11,12]:
                        self._pgn2 = "Code Version"

                        # Concatène tous les caractères utiles (ignore 0xFF et 0x00)
                        chunk_chars = []
                        for i in range(1, 8):
                            b = datas[i]
                            if b in (0xFF, 0x00):
                                continue
                            chunk_chars.append(chr(b))
                        self._valeurChoisie2 = "".join(chunk_chars)

                        if self._valeurChoisie2:
                            if self._source in self._temp_config and self._temp_config[source]['config'] is not None:
                                if z == 9:
                                    self._temp_config[source]['config'] += " - <strong>&nbsp;Code:&nbsp;</strong> "+ self._valeurChoisie2
                                else:
                                    self._temp_config[source]['config'] += self._valeurChoisie2
                            else:
                                # Cas rare : trame reçue sans trame 0 préalable
                                self._temp_config[source] = {'source': self._source, 'config': self._valeurChoisie2}

                        if z == 12:
                            config_finale = self._temp_config.get(source, {}).get('config')
                            if config_finale:
                                self._configuration[source] = " ".join(config_finale.split())


                case 126998:
                    # Configuration Information (PGN 126998). Fast Packet
                    # z = numéro de trame (datas[0] & 0x1F)
                    # Première trame : datas[2] = nombre d'octets, datas[3] = mode (0 ou 1)
                    # Trames suivantes : datas[0] = z, données commencent à datas[1]
                    z = (datas[0] & 0x1F)
                    self._valeurChoisie1 = "N° " + str(z)
                    self._pgn1 = "Info Configuration"

                    try:
                        # Initialisation à la première trame du fast-packet
                        if z == 0:
                            # Tampon pour reconstituer toutes les données du PGN
                            self._cfg_payload = bytearray()
                            # Octet [2] = nombre d'octets de la première chaîne
                            self._cfg_total = datas[2]
                            self._cfg_mode = datas[3]
                            self._cfg_payload.extend(datas[4:8])
                            if self._cfg_total == 2:
                                self._cfg_total = datas[4]
                                self._cfg_mode = datas[5]
                                self._cfg_payload.extend(datas[6:8])
                                if self._cfg_total == 2:
                                    self._cfg_total = datas[6]
                                    self._cfg_mode = datas[7]
                                    self._cfg_payload = bytearray()

                            # Octet [3] = mode de la première chaîne (0 ou 1)
                            # self._cfg_mode = datas[7]
                            # Ajouter la charge utile initiale (dès l'octet 4)
                            # self._cfg_payload.extend(datas[4:8])
                            # Publier les informations de la première trame
                            self._pgn2 =  "Configuration"
                            self._pgn3 = "Taille"
                            self._valeurChoisie3 = str(self._cfg_total)
                            self._valeurChoisieTab = str(self._cfg_mode)
                            self._definition = "UNICODE" if  self._cfg_mode == 0 else "ASCII"
                        else:
                            # Trames suivantes : on ajoute 7 octets de données (à partir de datas[1])
                            if not hasattr(self, "_cfg_payload"):
                                self._cfg_payload = bytearray()
                            # Extraire la portion de chaîne reçue dans cette trame
                            portion = datas[1:8]
                            self._cfg_payload.extend(portion)

                            # Convertir la portion en chaîne
                            # Ne s'arrêter sur 0xFF/0x00 que si on dépasse la longueur attendue
                            portion_chars = []
                            bytes_needed = self._cfg_total if hasattr(self, "_cfg_total") else 0
                            current_pos = len(self._cfg_payload) - len(portion)

                            for b in portion:
                                if current_pos < bytes_needed:
                                    # On est dans les données de la chaîne courante
                                    if b not in (0xFF, 0x00):
                                        portion_chars.append(chr(b))
                                    current_pos += 1
                                else:
                                    # On a dépassé la longueur attendue, s'arrêter sur 0xFF/0x00.
                                    if b in (0xFF, 0x00):
                                        break
                                    portion_chars.append(chr(b))
                                    current_pos += 1

                            # Publier la portion reçue dans cette trame
                            self._pgn2 = "Configuration"
                            self._valeurChoisie2 = "".join(portion_chars)

                            # Si on a reçu suffisamment de données, assembler la chaîne complète
                            if hasattr(self, "_cfg_total") and len(self._cfg_payload) >= self._cfg_total:
                                # Assembler la chaîne complète (exactement _cfg_total octets)
                                # Filtrer les 0xFF et 0x00 pour la dernière chaîne
                                full_chars = []
                                for b in self._cfg_payload[:self._cfg_total]:
                                    if b not in (0xFF, 0x00):
                                        full_chars.append(chr(b))
                                self._definition = "".join(full_chars)

                                # Vérifier s'il y a une chaîne suivante
                                if len(self._cfg_payload) > self._cfg_total:
                                    # L'octet suivant est la longueur de la chaîne suivante
                                    next_idx = self._cfg_total
                                    if next_idx < len(self._cfg_payload):
                                        new_total = self._cfg_payload[next_idx]
                                        # L'octet suivant est le mode
                                        if next_idx + 1 < len(self._cfg_payload):
                                            new_mode = self._cfg_payload[next_idx + 1]
                                            # Garder les données restantes après longueur+mode
                                            remaining = self._cfg_payload[next_idx + 2:]
                                            self._cfg_payload = remaining
                                            self._cfg_total = new_total
                                            self._cfg_mode = new_mode
                                        else:
                                            # Pas encore le mode, on attend la prochaine trame
                                            remaining = self._cfg_payload[next_idx + 1:]
                                            self._cfg_payload = remaining
                                            self._cfg_total = new_total
                                else:
                                    # Nettoyage de l'état pour la prochaine séquence
                                    self._cfg_payload = bytearray()
                                    self._cfg_total = 0
                                    self._cfg_mode = None
                    except Exception as e:
                        # Ne jamais casser le flux si un périphérique envoie un format exotique
                        print(f"Erreur décodage PGN 126998: {e}")


                case 127258:
                    self._valeurChoisie1 = "{:.2f}".format((datas[5] << 8 | datas[4]) * 0.0001 * 180 / math.pi)
                    self._pgn1 = "Variation magnétique"
                    # Bufferiser la variation magnétique et moyenner
                    try:
                        self._buffer_magvar.append(float(self._valeurChoisie1))
                        if len(self._buffer_magvar) >= 3:
                            self._magVarMoi = sum(self._buffer_magvar) / len(self._buffer_magvar)
                            self._buffer_magvar.clear()
                    except Exception as e:
                        print(f"Erreur buffer variation magnétique: {e}")

                case 130314:
                    self._valeurChoisie1 = "{:.2f}".format((datas[6] << 24 | datas[5] << 16 | datas[4] << 8 | datas[3]) * 0.001)
                    self._pgn1 = "Pression atmosphérique"

                    self._valeurChoisieTab = datas[2]
                    self._definition = PRESSION[self._valeurChoisieTab]

                case 129283:
                    self._pgn1 = "XTE"
                    if datas[5] & 0xEF != 0xEF:
                        self._valeurChoisie1 = "{:.2f}".format((datas[5] << 24 | datas[4] << 16 | datas[3] << 8 | datas[2]) * 0.00001)

                    self._valeurChoisieTab = datas[1] & 0x0F
                    self._definition = MODE_XTE[self._valeurChoisieTab]

                case 59392:
                    self._valeurChoisie1 = datas[7] << 16 | datas[6] << 8 | datas[5]
                    self._pgn1 = "Acquittement ISO"

                case 59904:
                    self._pgn1 = "Réclame le PGN ISO"
                    self._valeurChoisie1 = datas[2] << 16 | datas[1] << 8 | datas[0]

                case 60160:
                    self._valeurChoisie1 = datas[0]
                    self._pgn1 = "Protocole de transfert ISO"

                case 61184:
                    self._valeurChoisie1 = datas[0]
                    self._pgn1 = "Propriétaire Numéro"

                case 60416:
                    self._valeurChoisie1 = datas[0] & 0x0F
                    self._pgn1 = "Protocole de transfert ISO"

                case 60928:
                    self._pgn1 = "Réponse Adresse revendiquée"
                    self._pgn2 = "Code fabriquant"
                    self._valeurChoisie2 = ((datas[2] >> 5) & 0x07) | (datas[3] << 3)
                    self._definition = MANUFACTURE[self._valeurChoisie2]

                case _:
                    self._pgn1 = "<PGN inconnu sur cette version>"
                    print(f"PGN inattendu : {self._pgn}, Données : {datas}")
                    return (None,) * 8

        except KeyError:
            print(f"ERREUR sur le PGN: {self._pgn}")

        finally:
            pass

        # Retourne le tuple qui ne comprend pas les analyses pour l'instant.
        return (
            self._pgn1,
            self._pgn2,
            self._pgn3,
            self._valeurChoisie1,  # Utiliser float() au lieu de int()
            self._valeurChoisie2,  # pour gérer les nombres décimaux
            self._valeurChoisie3,
            self._valeurChoisieTab if isinstance(self._valeurChoisieTab, str) else self._valeurChoisieTab,
            self._definition
        )

    # Méthode asynchrone pour mettre à jour mes coordonnées. -----------------------------------------------------------
    async def safe_update_coordinates(self, **kwargs):
        try:
            updated = self.update_coordinates(**kwargs)     # Appelle la fonction qui retourne les coordonnées
            self._coordinates.update(updated)               # Mise à jour du dictionnaire globale "coordinates"
        except Exception as e:
            print(f"Erreur dans update_coordinates : {e}")

    # Méthode qui retourne les coordonnées dans un dictionnaire.
    @staticmethod
    def update_coordinates(**kwargs) -> dict[str, float | dict]:
        def _norm360(val: float) -> float:
            try:
                a = float(val) % 360.0
                if a < 0:
                    a += 360.0
                return a
            except Exception:
                return val

        return_coordinates = {}
        for key, value in kwargs.items():
            if value is not None:
                try:
                    # Normaliser les angles de vent côté backend pour garantir [0,360)
                    if key in ("w_angle_true", "w_angle_app"):
                        return_coordinates[key] = _norm360(value)
                    else:
                        return_coordinates[key] = float(value)
                except (TypeError, ValueError):
                    return_coordinates[key] = value
        return return_coordinates

# def log_ligne(texte):
#    with open("output.txt", "a", encoding="utf-8") as f:
#        f.write(texte + "\n")

def true_wind(VA, AWA, SOG, COG, HDG=None, boat_vector_use_hdg=False):
    """
    Calcule le vent réel (sur le fond) à partir du vent apparent, et l'angle de ce vent réel
    relatif à l'étrave pour déterminer Tribord/Bâbord.

    Paramètres:
    - VA : vitesse du vent apparent (nds).
    - AWA : angle du vent apparent en degrés, relatif à l'étrave (0..360, 90=Tribord, 270=Bâbord).
    - SOG : vitesse du bateau (nds). Si boat_vector_use_hdg=True, interprété comme STW ; sinon SOG.
    - COG : cap fond (degrés 0..360).
    - HDG : cap compas/route du bateau (degrés 0..360). Si fourni, sert de référence pour AWA et l'angle relatif.
    - boat_vector_use_hdg: si True et HDG fourni, le vecteur vitesse du bateau
            est orienté selon HDG (cas STW). Sinon, il est orienté selon COG (cas SOG).

    Retourne un tuple (vitesse_vent_réel, angle_vent_réel_terre_0_360, angle_vent_réel_relatif_0_360)
    - angle_vent_réel_terre_0_360 : direction du vent réel dans le repère Terre (0..360)
    - angle_vent_réel_relatif_0_360 : direction du vent réel relative à l'étrave (0..360),
      utilisable directement pour l'affichage Tribord/Bâbord (0..180 = Tribord, 180..360 = Bâbord)
    """
    # 1) Référence angulaire pour convertir l'AWA vers le repère Terre
    ref_heading = HDG if HDG is not None else COG
    awa_earth = (ref_heading + (AWA % 360.0)) % 360.0

    # 2) Vecteur vent apparent dans le repère Terre
    VA_x = VA * math.cos(math.radians(awa_earth))
    VA_y = VA * math.sin(math.radians(awa_earth))

    # 3) Vecteur vitesse du bateau (négatif car vent réel = vent apparent + (-vitesse_bateau))
    boat_dir = HDG if (boat_vector_use_hdg and HDG is not None) else COG
    SOG_x = -SOG * math.cos(math.radians(boat_dir))
    SOG_y = -SOG * math.sin(math.radians(boat_dir))

    # 4) Somme vectorielle = vent réel (sur le fond)
    VT_x = VA_x + SOG_x
    VT_y = VA_y + SOG_y

    VT_speed = math.hypot(VT_x, VT_y)
    VT_angle_earth = math.degrees(math.atan2(VT_y, VT_x))
    if VT_angle_earth < 0:
        VT_angle_earth += 360.0

    # 5) Angle relatif à l'étrave pour l'affichage Td/Bd
    # On utilise la même référence que pour AWA: le HDG s'il existe, sinon le COG
    VT_angle_rel = (VT_angle_earth - ref_heading) % 360.0

    return VT_speed, VT_angle_earth, VT_angle_rel

# Moyenne circulaire en degrés pour des angles [0,360)
def circular_mean_deg(values):
    try:
        n = len(values)
        if n == 0:
            return None
        s = 0.0
        c = 0.0
        for v in values:
            rad = math.radians(float(v))
            s += math.sin(rad)
            c += math.cos(rad)
        if s == 0.0 and c == 0.0:
            # angles opposés parfaits : retourner simplement le premier normalisé
            return float(values[0]) % 360.0
        ang = math.degrees(math.atan2(s, c))
        if ang < 0.0:
            ang += 360.0
        return ang
    except Exception as e1:
        print(f"Moyenne arithmétique normalisée : {e1}")
        # En cas d'anomalie, repli : moyenne arithmétique normalisée
        try:
            avg = sum(float(v) for v in values) / len(values)
            avg = avg % 360.0
            if avg < 0:
                avg += 360.0
            return avg
        except Exception as e2:
            print(f"[circular_mean_deg] Erreur dans le repli : {e2}")

            return None
