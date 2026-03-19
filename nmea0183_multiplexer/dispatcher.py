from HUAHINE import coordinates #, mmsi_navires  # à adapter
from Package.MMSI import MMSI
from pynmea2 import parse, GGA, VTG, RMC
from pyais import decode  # si tu utilises pyais pour les trames AIS

class Dispatcher:
    def __init__(self):
        self._navires_table = {}
        self._mmsi_instance = MMSI(self._navires_table)

    def dispatch(self,sentence: str):
        print(sentence)
        # Trames AIS (commencent par '!AIVDM')
        if sentence.startswith('!AIVDM'):
            try:
                msg = decode(sentence)
                ais_mmsi = msg.mmsi
                name = getattr(msg, 'ship_name', None)
                latitude = getattr(msg, 'lat', None)
                longitude = getattr(msg, 'lon', None)
                cog = getattr(msg, 'course', None)
                sog = getattr(msg, 'speed', None)
                classe = msg.get("type") if hasattr(msg, 'get') else None

                if latitude and longitude:
                    self._mmsi_instance.mmsi_navires(
                        ais_mmsi=ais_mmsi,
                        name=name,
                        latitude=latitude,
                        longitude=longitude,
                        cog=cog,
                        sog=sog,
                        classe=classe
                    )
            except Exception as e:
                print(f"[AIS] Erreur de parsing: {e}")
            return

        # Trames NMEA classiques
        try:
            msg = parse(sentence)
        except Exception as e:
            print(f"[NMEA] Erreur de parsing: {e}")
            return

        if isinstance(msg, GGA):
            coordinates["latitude"] = msg.latitude
            coordinates["longitude"] = msg.longitude

        elif isinstance(msg, VTG):
            coordinates["cog"] = msg.true_track
            coordinates["sog"] = msg.spd_over_grnd_kts * 1.852

        elif isinstance(msg, RMC):
            coordinates["latitude"] = msg.latitude
            coordinates["longitude"] = msg.longitude
            coordinates["cog"] = msg.true_course
            coordinates["sog"] = msg.spd_over_grnd * 1.852