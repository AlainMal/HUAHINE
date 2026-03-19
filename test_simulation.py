import math
import time
import json
import os
from datetime import datetime

class SimulateurBateau:
    def __init__(self, lat_init=43.243757, lon_init=5.365660):
        self.latitude = lat_init
        self.longitude = lon_init
        self.vitesse = 6.0  # nœuds
        self.cap = 270.0  # ouest
        self.history_file = os.path.join('static', 'boat_history.json')  # Modifié pour écrire directement dans static

        # Créer le dossier static s'il n'existe pas
        os.makedirs('static', exist_ok=True)

    def calculer_nouvelle_position(self, delta_temps_heures):
        # Distance parcourue en milles nautiques
        distance_nm = self.vitesse * delta_temps_heures
        # Conversion en degrés (1 NM = 1/60 degré)
        distance_deg = distance_nm / 60.0

        # Calcul des composantes selon le cap
        cap_rad = math.radians(self.cap)

        # Déplacement en latitude (Nord/Sud)
        delta_lat = distance_deg * math.cos(cap_rad)
        # Déplacement en longitude (Est/Ouest). Correction pour la convergence des méridiens
        delta_lon = distance_deg * math.sin(cap_rad) / math.cos(math.radians(self.latitude))

        self.latitude += delta_lat
        self.longitude += delta_lon

        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sog": self.vitesse,  # Vitesse (Speed Over Ground)
            "cog": self.cap  # Cap (Course Over Ground)
        }

    def sauvegarder_position(self, position):
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            history = []

        history.append(position)

        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)

    def simuler(self, duree_minutes=60, intervalle_secondes=10):
        print(f"Début de la simulation : position initiale : {self.latitude:.6f}°N, {self.longitude:.6f}°E")

        iterations = int((duree_minutes * 60) / intervalle_secondes)
        for i in range(iterations):
            delta_temps = intervalle_secondes / 3600.0
            position = self.calculer_nouvelle_position(delta_temps)
            self.sauvegarder_position(position)

            print(f"Position {i + 1}/{iterations} : {position['latitude']:.6f}°N, {position['longitude']:.6f}°E")
            time.sleep(intervalle_secondes)

        print("Simulation terminée")


if __name__ == "__main__":
    simulateur = SimulateurBateau(lat_init=43.243757, lon_init=5.365660)
    simulateur.simuler(duree_minutes=60, intervalle_secondes=10)

def main():
    # Création du simulateur avec position initiale
    simulateur = SimulateurBateau(lat_init=43.243757, lon_init=5.365660)

    # Lancement de la simulation pour 10 minutes avec mise à jour toutes les 10 secondes
    simulateur.simuler(duree_minutes=10, intervalle_secondes=10)

