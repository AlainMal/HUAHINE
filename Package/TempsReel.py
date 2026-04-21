from Package.CAN_dll import CanMsg

# ======================================================================================================================
# Cette classe sert uniquement à traiter les résultats en temps réel.
# ======================================================================================================================
class TempsReel:
    def __init__(self):
        pass

    # Méthode du temps réel sur bus CAN. --------------------------------------------------------------------------------
    @staticmethod
    def temps_reel(msg:CanMsg, file_path, coche_file,coche_nmea, main_window):
        if msg:
            # On met le résultat dans un fichier si la case à cocher est validée.
            if coche_file:
                with open(file_path, "a") as file:
                    # Limite de sécurité : max 8 octets
                    data_bytes = msg.data[:msg.len]

                    # Formatage hexadécimal
                    datas = " ".join(f"{byte:02X}" for byte in data_bytes)

                    # Écriture : timestamp, ID sur 8 hex, longueur sur 1 hex, données
                    file.write(f"{msg.TimeStamp} {msg.ID:08X} {msg.len:X} {datas}\n")

            # *************** EMPLACEMENT PRÉVU POUR METTRE LE TEMPS REEL *********************
            #                             NMEA 2000
            #                       Affichage des jauges
            #                       Affichage des MMSI
            #                       Affichage des positions sur la carte
            #                       Affichage des instruments sur NMEA 2000
            # *********************************************************************************

            # On appelle la routine "octets" si la case à cocher est activée pour "NMEA 2000 en temps réel".
            if coche_nmea:
                # Récupère le pgn.
                pgn =  main_window.nmea_2000.pgn( msg.ID)
                # Récupère la source.
                source = main_window.nmea_2000.source(msg.ID)
                # Appelle la fonction "octets" dans "NMEA_2000.py" en temps réel
                main_window.nmea_2000.octets(pgn, source, msg.data) # Ce qui est fait dans "octets".
            # =================================================================================
