"""  principal  """
import asyncio
import csv
import subprocess
import webbrowser
import ctypes
import sqlite3
import qasync
import logging
import sys
import json
import warnings
import win32gui
import win32con
import win32api
import win32process
import os
from pathlib import Path
from datetime import datetime
import resouce_rc

# Ignorer le warning SIP
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=".*sipPyTypeDict.*"
)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QTableView, QMessageBox, QFileDialog
from PyQt5.QtWidgets import QMainWindow, QAbstractItemView
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, pyqtSlot, Qt
from PyQt5.QtGui import QIcon
from PyQt5.uic import loadUi
from quart import Quart, render_template, Response, jsonify, request

# Import des packages personnalisés
from serveur_aide import register_aide_routes, start_help_server
from Package.NMEA_2000 import NMEA2000
from Package.CAN_dll import CANDll
from Package.TempsReel import TempsReel

from Package.CANApplication import CANApplication
from Package.Constante import *

# Fenêtre de vent gérée côté frontend (Fenêtre1.js)

# Méthode pour définir les ressource PATH ------------------------------------------------------------------------------
def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

# ********************************** CLASSE MODÈLE DE LA TABLE *********************************************************
# Cette classe sert de modèle à la table incluse dans MainWindow().
class TableModel(QAbstractTableModel):
    def __init__(self, buffer, buffer_index, buffer_capacity):
        """
        Initialise le modèle avec le buffer circulaire.
        """
        super().__init__()
        self._buffer_count = 0
        self._buffer = buffer
        self._buffer_index = buffer_index
        self._buffer_capacity = buffer_capacity
        self._row_count = 0  # Nombre réel de lignes dans le buffer.
        self._model = None  # Par exemple, initialisez avec un modèle qui sera défini plus tard
    # ==================================== DEBUT DES MÉTHODES DE LA TABLE ==============================================
    # Méthode pour actualiser le buffer de la table. -------------------------------------------------------------------
    def update_buffer(self, buffer, buffer_index, row_count):
        self.beginResetModel()
        self._buffer = buffer
        self._buffer_index = buffer_index
        self._row_count = row_count
        self.endResetModel()

    # Méthode pour récupérer l'index du buffer. ------------------------------------------------------------------------
    def get_real_index(self, logical_row):
        return (self._buffer_index - self._buffer_count + logical_row) % self._buffer_capacity

    # Méthode pour récupérer la ligne en cours. ------------------------------------------------------------------------
    def get_row_data(self, row):
        real_index = self.get_real_index(row)
        return self._buffer[real_index]

    # Méthode pour retourner le nombre de lignes. ----------------------------------------------------------------------
    def rowCount(self, parent=None):
       return self._row_count

    # Méthode pour retourner le nombre de colonnes. --------------------------------------------------------------------
    def columnCount(self, parent=None):
        return 3

    # Méthode pour retourner la donnée de la trame. --------------------------------------------------------------------
    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            # Obtenir l'indice réel dans l'ordre FIFO (en respectant l'ordre haut vers bas)
            real_index = self.get_real_index(index.row())
            trame = self._buffer[real_index]

            # Vérifier si la trame est valide (ne pas afficher les valeurs vides par défaut)
            if trame == ("", "", ""):
                return None

            # Retourner la donnée de la colonne correspondante
            return trame[index.column()]

        return None

    # Méthode pour retourner l'en-tête. --------------------------------------------------------------------------------
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                headers = ["ID", "Len", "Datas"]
                return headers[section]
            elif orientation == Qt.Vertical:
                return str(section + 1)
        return None
# ************************************ FIN DE LA CLASSE TableModel *****************************************************

# ***************************************** FENÊTRE PRINCIPAL ********************************************************
# noinspection PyUnresolvedReferences
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow,self).__init__() # Lance la fenêtre
        self._quart_running = None
        self.quart_task = None
        self.event_loop = None
        self._file_path_csv = None
        self._reply = None
        self._selected_file_path = None
        self.loop = None
        self.setWindowIcon(QIcon(resource_path("VoilierImage.ico")))
        loadUi(resource_path('Alain.ui'), self)
        self.quart_running = False  # Pour suivre l'état du serveur

        self.browser_open = False
        self.nav_window = None  # Fenêtre de navigation intégrée

        self._fenetre_status = None
        self._file_path = None
        self._can_interface = None
        self._handle = None
        self._status = None
        self._stop_flag = False
        self._fenetre_status = None
        self._update_counter = 0
        self._pending_updates = 0  # Compteur pour les mises à jour en attente
        self._batch_update_threshold = 10  # Seuil pour les mises à jour en lot

        # Initialisation des attributs d'instance dans le constructeur
        self.loop = None  # La boucle asyncio sera définie plus loin.

        # Définition des capacités par défaut des : Fichier bus CAN dans Fichier NMEA et taille du buffer tournant.
        self.line_nmea.setText("10000") # Taille pour enregistrer le NMEA 2000
        self.line_table.setText("5000") # Taille pour le buffer tournant

        # Crée l'instance des Classes
        self.setWindowIcon(QIcon(resource_path("VoilierImage.ico")))
        self._temps_reel = TempsReel()
        self._nmea_2000 = NMEA2000(self,coordinates,configuration)
        self._can_interface = CANDll(self._stop_flag, self._nmea_2000)

        # Instanciez CANApplication en lui passant les paramètres nécessaires
        self.can_interface_app = CANApplication(
            self,
            temps_reel=self._temps_reel,            # Fenêtre Temps Réel
            file_path=self._file_path,              # Chemin du fichier texte
            lab_connection=self.lab_connection,     # Où se trouve le label pour afficher le nombre de trames reçues
            check_file=self.check_file,
            check_nmea=self.check_nmea,
            handle=None,
            actions={
                "actionOpen": self.actionOpen,
                "actionClose": self.actionClose,
                "actionRead": self.actionRead,
                "actionStop": self.actionStop,
                "actionStatus": self.actionStatus
            }
        )

        quart_app.can_app = self.can_interface_app
        # quart_app.can_app._encours = True # Pour essai


        # table_can
        self.table_can: QTableView = self.findChild(QTableView, "table_can")

        # Variables pour le buffer tournant
        self._buffer_capacity = int(self.line_table.text())
        self._buffer_index = 0  # Position actuelle du buffer circulaire
        self._buffer_count = 0  # Nombre d'éléments actuellement remplis

        # Buffer initialisé avec des données vides.
        self._buffer = [("", "", "")] * self._buffer_capacity

        # Instanciation de notre TableModel
        self._model = TableModel(self._buffer, self._buffer_index, self._buffer_capacity)
        self.table_can.setModel(self._model)  # Lien entre le modèle et la table


        # Initialize la table.
        self.table_can.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_can.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.table_can.setModel(self._model)

        # Configurer les largeurs des colonnes
        self.configurer_colonnes()

        # Défini la méthode sur changement de ligne sur la table.
        # noinspection PyUnresolvedReferences
        self.table_can.selectionModel().selectionChanged.connect(self.on_selection_changed)

        # Appel des méthodes des objets widgets.
        self.check_file.stateChanged.connect(self.on_check_file_changed)
        self.table_can.clicked.connect(self.on_click_table)                 # Gestion du clic dans la table
        self.line_table.editingFinished.connect(self.on_change_buffer_size) # Modification de la taille du buffer

        # Appel des méthodes des menus.
        self.actionOuvrir.triggered.connect(self.on_click_file)
        self.actionImporter.triggered.connect(self.on_click_import)
        self.actionVoir.triggered.connect(self.on_click_voir)
        self.actionAbout.triggered.connect(self.show_about_box)
        self.actionExport.triggered.connect(self.on_click_export)
        self.actionMap.triggered.connect(self.on_click_map)
        self.actionQuitter.triggered.connect(self.close_both)
        self.actionAide.triggered.connect(self.show_help)

        # Initialise les menus inaccessibles.
        self.actionClose.setEnabled(False)
        self.actionRead.setEnabled(False)
        self.actionStop.setEnabled(False)
        self.actionImporter.setEnabled(False)
        self.actionVoir.setEnabled(False)
        self.actionExport.setEnabled(False)

        self.setWindowIcon(QIcon(resource_path("VoilierImage.ico")))

        # Démarrer le serveur d'aide
        start_help_server()

    @property
    def nmea_2000(self):
        return self._nmea_2000

    # ==================================== DEBUT DES MÉTHODES LIÉES A LA TABLE =========================================
    # Méthode pour configurer la taille des colonnes de la table. ------------------------------------------------------
    def configurer_colonnes(self):
        self.table_can.setColumnWidth(0, 80)  # Largeur de "ID"
        self.table_can.setColumnWidth(1, 30)  # Largeur de "Len"
        self.table_can.setColumnWidth(2, 180)  # Largeur de "Data"
        # Ouvre la table.
        self.show()

    # Méthode sur changement de ligne sur la table. --------------------------------------------------------------------
    def on_selection_changed(self):
        indexes = self.table_can.selectionModel().selectedRows()
        if indexes:  # Vérifier s'il y a une sélection active
            index = indexes[0]
            self.on_click_table(index)  # On va sur "on_click_table".sus. -----------------------------------------
    def on_click_table(self, index: QModelIndex):
        model = self.table_can.model()  # Récupérer le modèle de la table
        ligne = index.row()  # Récupérer l'indice de la ligne cliqué

        if isinstance(model, TableModel):
            # Récupère directement les données de la ligne grâce aux méthodes publiques
            row_data = model.get_row_data(ligne)

            col1 = row_data[0]  # ID
            col2 = row_data[1]  # Longueur (Len)
            col3 = row_data[2]  # Données hexadécimales

            print(f"Ligne sélectionnée : {ligne}\n"
                  f"ID : {col1}\n"
                  f"Nb Octets : {col2}\n"
                  f"Datas : {col3}")
        else:
            # Logique par défaut si un modèle autre qu'un buffer circulaire est utilisé
            col1 = model.data(model.index(ligne, 0), Qt.DisplayRole)
            col2 = model.data(model.index(ligne, 1), Qt.DisplayRole)
            col3 = model.data(model.index(ligne, 2), Qt.DisplayRole)

            print(f"Ligne sélectionnée : {ligne}\n"
                  f"ID : {col1}\n"
                  f"Nb Octets : {col2}\n"
                  f"Datas : {col3}")

        col1= col1.strip()
        if not col1.startswith("0x"):
            col1 = f"0x{col1}"

        id_msg = int(col1, 16)
        tout_id = self._nmea_2000.id(id_msg)

        # Affiche le résultat des octets avec leurs définitions.
        if col3:
            data = col3.split(" ")
            try:
                # Récupère les informations des octets.
                octetsTuple = self._nmea_2000.octets(int(tout_id[0]),int(tout_id[1]),[int(octet,16) for octet in data])
                # Affiche toutes les informations sur le formulaire.
                self.lab_octet.setText("                             Ligne " + str(ligne+1)       # Numéro de ligne
                               + "\n PGN : "+ " " + str(tout_id[0])                               # PGN
                               + "   Prio : " + str(tout_id[3])                                   # Priorité
                               + "  Source : " +  str(tout_id[1])                                 # Source
                               + "  Dest. : " + str(tout_id[2]) + "\n\n"                          # Destination
                               + " " + str(octetsTuple[0]) + ": " + str(octetsTuple[3]) + "\n"    # PGN1 : Valeur 1
                               + " " + str(octetsTuple[1]) + ": " + str(octetsTuple[4]) + "\n"    # PGN2 : Valeur 2
                               + " " + str(octetsTuple[2]) + ": " + str(octetsTuple[5]) + "\n"    # PGN3 : Valeur 3
                               + " Table : " + str(octetsTuple[6]) + ": \n"                       # Table :
                               + " Définition : " + str(octetsTuple[7])) + "\n"                   # Définition
            except Exception as e:
                print(f"Erreur dans l'appel à octets : {e}")

    # Méthode pour remplir la table venant d'un fichier. ---------------------------------------------------------------
    def affiche_trame_fichier(self, trame):
        self.add_to_buffer(trame)

    # Méthode pour ajouter une trame au buffer -------------------------------------------------------------------------
    def add_to_buffer(self, trame):
        # Ajouter la trame dans l'ordre dans la position en cours
        self._buffer[self._buffer_index] = trame

        # Incrémenter l'index
        self._buffer_index = (self._buffer_index + 1) % self._buffer_capacity

        # S'assurer que le nombre total de trames ajoutées ne dépasse pas la capacité du buffer
        if self._buffer_count < self._buffer_capacity:
            self._buffer_count += 1

        # Incrémentation pour compter le nombre de trames depuis la dernière mise à jour
        self._update_counter += 1

        # Met à jour la table toutes les 10 trames
        if self._update_counter >= self._batch_update_threshold:
            self._update_counter = 0  # Réinitialise le compteur
            self._model.update_buffer(self._buffer, self._buffer_index, self._buffer_count)

        # Ajouter au compteur d'attente pour update
        self._pending_updates += 1

        # Vérifier si un seuil est atteint pour mettre à jour la table
        if self._pending_updates >= self._batch_update_threshold:
            self._pending_updates = 0  # Réinitialisation du compteur
            # Mise à jour en regroupant les trames
            self._model.update_buffer(self._buffer, self._buffer_index, self._buffer_count)

    # Méthode pour changement de la valeur de la capacité du buffer. ---------------------------------------------------
    def on_change_buffer_size(self):
        try:
            # Validation de la nouvelle taille
            new_size = int(self.line_table.text())
            if new_size <= 0:
                raise ValueError("La taille doit être supérieure à zéro.")

            # Réinitialise le buffer avec la nouvelle capacité
            self._buffer_capacity = new_size
            self._buffer = [("", "", "")] * self._buffer_capacity
            self._buffer_index = 0
            self._buffer_count = 0

            # Réinitialisation de la table
            self._model.update_buffer(self._buffer, self._buffer_index, self._buffer_count)

        except ValueError:
            # Gère les erreurs en affichant un message
            QMessageBox.warning(self, "Erreur", "Veuillez entrer une taille valide (entier positif).")
            # Réinitialise la valeur précédente
            self.line_table.setText(str(self._buffer_capacity))
    # ================================ FIN DES MÉTHODES LIÉES A LA TABLE ===============================================

    # ============================== DEBUT DES MÉTHODES LIÉES A L'APPLICATION ==========================================
    # Méthode pour arrêter toutes les tâches ---------------------------------------------------------------------------
    async def async_close(self):
        """Gestion asynchrone de la fermeture"""
        try:
            # Arrêter Quart
            if hasattr(self, 'arreter_quart'):
                await self.arreter_quart()

            # Nettoyage des tâches
            if hasattr(self, 'cleanup'):
                await cleanup(window)

            # Arrêter l'application CAN si elle existe
            if hasattr(self, 'can_interface_app'):
                await self.can_app.arreter_quart()

           # Permettre la mise en veille en Windows
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)

        except Exception as error:
            print(f"Erreur pendant async_close: {error}")

    # Méthode pour arrêter la fenêtre principale sur "X" ---------------------------------------------------------------
    def closeEvent(self, event):
        """Gestionnaire d'événement de fermeture"""
        reply = QMessageBox.question(
            self,
            "Quitter",
            "Voulez-vous vraiment quitter l'application ?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()  # on laisse fermer.
            # self.close_both()
            # Demander l'arrêt propre directement via handle_shutdown (exposé sur la fenêtre principale)
            try:
                if hasattr(self, 'handle_shutdown') and callable(self.handle_shutdown):
                    print("Demande d'arrêt propre via handle_shutdown...")
                    self.handle_shutdown()
                else:
                    print("[WARN] handle_shutdown indisponible; tentative de nettoyage asynchrone minimal")
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(self.async_close())
                    else:
                        loop.run_until_complete(self.async_close())
            except Exception as error:
                print(f"Erreur lors de la demande d'arrêt propre: {error}")
            # Ne pas appeler self.close() ici; la fermeture est gérée par loop.stop() puis Qt.
        else:
            event.ignore()  # on bloque la fermeture


    # Méthode pour fermer la fenêtre principale avec le menu -----------------------------------------------------------
    def close_both(self):
        """Point d'entrée pour la fermeture depuis le menu"""
        self._reply = QMessageBox.question(self, "Fermer l'application", "Voulez-vous vraiment quitter l'application ?",QMessageBox.Yes | QMessageBox.No)
        if self._reply == QMessageBox.No:
            return
        print("Fermeture des fenêtres...")
        # Fermer Fenêtre Status
        if hasattr(self, 'can_interface_app'):
            self.can_interface_app.fermer_fenetre_status()
            print("La fenêtre Status est fermée")

            # Fermer la fenêtre principale
            self.can_interface_app.on_click_close()
            print("Fermeture de la fenêtre principale")

        # Demander l'arrêt propre directement via handle_shutdown (exposé sur la fenêtre principale)
        try:
            if hasattr(self, 'handle_shutdown') and callable(self.handle_shutdown):
                print("Demande d'arrêt propre via handle_shutdown...")
                self.handle_shutdown()
            else:
                print("[WARN] handle_shutdown indisponible; tentative de nettoyage asynchrone minimal")
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self.async_close())
                else:
                    loop.run_until_complete(self.async_close())
        except Exception as error:
            print(f"Erreur lors de la demande d'arrêt propre: {error}")
        # Ne pas appeler self.close() ici; la fermeture est gérée par loop.stop() puis Qt.

    # Méthode sur la case à cocher. ------------------------------------------------------------------------------------
    def on_check_file_changed(self, state):
        if state == Qt.Checked:
            if not self._file_path:
                QMessageBox.information(self, "ENREGISTREMENT",
                                        "Veuillez ouvrir un fichier avant de pouvoir l'enregistrer.")
                # Remet la case à False.
                self.check_file.setChecked(False)
        return self.check_file

    # Méthode d'ouverture de la lecture du bloc note. ------------------------------------------------------------------
    def on_click_voir(self):
        if self._file_path:
            if os.path.exists(self._file_path):
                subprocess.Popen(["notepad.exe", self._file_path])
        else:
            QMessageBox.information(self, "VOIR", "Veuillez ouvrir un fichier avant de le voir sur le bloc notes.")

    # Méthode pour ouvrir le fichier texte, prêt à l'enregistrement. ----------------------------------------------------
    def on_click_file(self):
        # self.setCursor(Qt.WaitCursor)
        self.setCursor(Qt.CursorShape.WaitCursor)

        __previous_file_path = self._file_path

        # Boîte de dialogue pour sélectionner un fichier ou en définir un nouveau
        selected_file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Créer un Fichier texte pour récupérer les trame du bus CAN",  # Titre de la boîte de dialogue
            self._file_path if self._file_path else ""
            ,  # Dossier initial
            "Fichier texte (*.txt);;Tous les fichiers (*.*)")

        if selected_file_path:
            self._file_path = selected_file_path
            # Si le fichier n'existe pas, le créer
            if not os.path.exists(self._file_path):
                with open(self._file_path, "w") as file:
                    file.write("")  # Crée un fichier vide
                print(f"Fichier créé : {self._file_path}")
                self.lab_file.setText(str(self._file_path))
            else:
                print(f"Fichier ouvert : {self._file_path}")
                self.lab_file.setText("Bus CAN     : " + str(self._file_path))

            self.actionImporter.setEnabled(True)
            self.actionVoir.setEnabled(True)
            self.actionExport.setEnabled(True)

        else:
            self._file_path = __previous_file_path
            print("Aucun fichier sélectionné.")

        self.unsetCursor()
        self.can_interface_app._file_path = self._file_path

    # Méthode pour importer les données du fichier texte sur la table. -------------------------------------------------
    def on_click_import(self):
        if not self._file_path:
            QMessageBox.information(self, "IMPORTER LE FICHIER",
                                    "Veuillez ouvrir un fichier avant de l'importer sur la table.")
            return None

        # On défini la quantité de trames
        quantite = int(self.line_table.text())
        start_index = 0

        resultat = self.Qmessagebox_4_boutons( "Importer dans la table",
                                                  "Vous allez importer dans la table",
                                                  start_index,
                                                  "Précédent",
                                                  "Suivant",
                                                  "Valider",
                                                  quantite)

        if resultat is None:
            print("La boîte de dialogue a été fermée sans action (bouton 'X').")
            return None
        else:
            print(f"L'importation commence à l'index : {resultat}")
            start_index = resultat

        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            liste_tuples = []
            with open(self._file_path, 'r', encoding='utf-8', errors='replace') as fichier:
                for i, ligne in enumerate(fichier):
                    # Saute les lignes avant le `start_index`
                    if i < start_index:
                        continue

                    # Lire jusqu'à la quantité de lignes à partir de `start_index`
                    if i >= start_index + quantite:
                        break

                    # Supprimer les espaces inutiles.
                    ligne = ligne.strip()

                    # Défini l'espace comme séparateur.
                    valeurs = ligne.split(' ')

                    # Convertit la liste des valeurs en tuple.
                    ligne_tuple = tuple(valeurs)

                    # Ajoute le tuple à la liste.
                    liste_tuples.append(ligne_tuple)

            # Transformer la liste pour afficher seulement les colonnes souhaitées.
            # Les valeurs dans la table sont déjà en hexadécimales.
            liste_modifiee = [
                (
                    t[1] if len(t) > 1 else '',  # 2e élément ID
                    t[2] if len(t) > 2 else '',  # 3e élément Len
                    ' '.join(t[3:]) if len(t) > 3 else ''  # 4e élément Data avec join.
                )
                for t in liste_tuples
            ]

            # Appeler la fonction pour afficher les trames une par une.
            for trame in liste_modifiee:
                self.affiche_trame_fichier(trame)

        except Exception as error:
            QMessageBox.critical(self, "Erreur", f"Une erreur s'est produite lors de l'importation : {str(error)}")

        finally:
            QApplication.restoreOverrideCursor()

        return None

    # Méthode pour exporter le fichier texte vers le fichier NMEA 2000 en CSV. -----------------------------------------
    def on_click_export(self):
        if not self._file_path_csv:
            # Récupérer le chemin du fichier où sauvegarder le CSV.
            self._file_path_csv, _ = QFileDialog.getSaveFileName(self,
                                                  "Créer un fichier CSV pour y inclure le NMEA 2000",
                                                  "",
                                                  "Fichier csv (*.csv);;Tous les fichiers (*.*)")
        else:
            self._reply = QMessageBox.question(self, "EXPORTER LE FICHIER EN NMEA 2000",
                                               f"Voulez-vous créer un autre fichier CSV ?\n\n"
                                               f"Ou travailler avec celui-ci :\n{self._file_path_csv}")
            if self._reply == QMessageBox.Yes:
                # Récupérer le chemin du fichier où sauvegarder le CSV.
                self._file_path_csv, _ = QFileDialog.getSaveFileName(self,
                                                  "Créer un nouveau fichier CSV pour y inclure le NMEA 2000",
                                                  "",
                                                  "Fichier csv (*.csv);;Tous les fichiers (*.*)")

        if not self._file_path_csv:
            return
        else:
            self.lab_csv.setText("NMEA 2000 : " + str(self._file_path_csv))

        nombre_lignes = int(self.line_nmea.text())  # C'est ici qu'on définit la taille du fichier NMEA 2000.

        # Récupérer le start_index à partir de la méthode de gestion des quatre boutons
        start_index = self.Qmessagebox_4_boutons("Exporter NMEA 2000",
                                                 f"Vous allez exporter dans le fichier "
                                                 f"{os.path.basename(self._file_path_csv)} en NMEA 2000",
                                                 0,
                                                 "Précédent",
                                                 "Suivant",
                                                 "Valider",
                                                 nombre_lignes)

        if start_index is None:
            print("La boîte de dialogue a été fermée sans action (bouton 'X').")
            return

        try:
            # Ouvrir le fichier source texte.
            with open(self._file_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                # Lire toutes les lignes du fichier
                lignes = f.readlines()

            # Ignorer les lignes avant le `start_index` et limiter à nombre les lignes
            lignes_restees = lignes[start_index:start_index + nombre_lignes]

            # Transformer les lignes en données structurées
            resultat = (ligne.strip().split(" ") for ligne in lignes_restees if ligne.strip())

            # Ouvrir le fichier CSV pour écrire les résultats
            #with open(self._file_path_csv, 'w', newline='', encoding='utf-8-sig') as f:
             #   writer = csv.writer(f, delimiter=';')
            with open(self._file_path_csv, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_ALL)

                # Écrire l'en-tête du fichier CSV
                writer.writerow(("PGN", "Source","Destination", "Priorité","PGN1", "Valeur", "PGN2",
                                 "Valeur", "PGN3", "Valeur", "Table", "Définition"))

                for index, ligne in enumerate(resultat):
                    try:
                        # Vérifier que la ligne contient suffisamment de données
                        if len(ligne) < 1:
                            print(f"Données insuffisantes à l'index {index} : {ligne}")
                            continue

                        nombre_octets_declare = int(ligne[2])
                        # Extraire les octets selon le nombre déclaré
                        data = ligne[3:3 + nombre_octets_declare]

                        # Convertir les octets en valeurs numériques
                        octets = []
                        for octet in data:
                            if len(octet) == 2 and all(c in '0123456789ABCDEFabcdef' for c in octet.lower()):
                                octets.append(int(octet, 16))
                            else:
                                print(f"Octet invalide ignoré : {octet}")

                        # Convertir et traiter les champs de la ligne avec la méthode _nmea_2000.pgn
                        pgn = self._nmea_2000.pgn(int(ligne[1], 16))  # Conversion hexadécimale → entier

                        # Récupérer la source
                        source = self._nmea_2000.source(int(ligne[1], 16))

                        # Récupérer la destination
                        destination = self._nmea_2000.destination(int(ligne[1], 16))

                        # Récupérer la priorité
                        priorite = self._nmea_2000.priorite(int(ligne[1], 16))

                        # Récupère la zone data qui est mise dans les colonnes 3 à 10
                        # data = (ligne[i].strip() for i in range(3, 11) if i < len(ligne))
                        # data = ligne[3:] if len(ligne) > 3 else []
                        # print(f"Données brutes trouvées : {data}")

                        # Convertir les octets avec la méthode `_nmea_2000. octets`
                        result = ["N/A"] * 8
                        try:
                            result = self._nmea_2000.octets(pgn,source,octets)
                        except ValueError as ve:
                            print(f"Erreur dans le traitement NMEA 2000 à l'index {index}")
                            print(f"PGN: {pgn}")
                            print(f"Octets: {octets}")
                            print(f"Erreur détaillée: {ve}")

                        def protect_excel(value):
                            if value is None:
                                return ""
                            v = str(value)
                            # Si la valeur ressemble à une formule potentielle
                            if v.startswith("-") and "-" in v[1:]:
                                return f'="{v}"'
                            return v

                        # Écrire les résultats dans CSV sous forme d'un tuple.

                        writer.writerow((
                            str(pgn),
                            str(source),
                            str(destination),
                            str(priorite),
                            protect_excel(result[0]),
                            protect_excel(result[3]),
                            protect_excel(result[1]),
                            protect_excel(result[4]),
                            protect_excel(result[2]),
                            protect_excel(result[5]),
                            protect_excel(result[6]),
                            protect_excel(result[7])
                        ))


                    except ValueError as ve:
                        print(f"Erreur de conversion à l'index {index} : {ligne}")
                        print(f"TimeStamp: {ligne[0] if len(ligne) > 0 else 'N/A'}")
                        print(f"ID: {ligne[1] if len(ligne) > 1 else 'N/A'}")
                        print(f"Nombre d'octets déclaré: {ligne[2] if len(ligne) > 2 else 'N/A'}")
                        print(f"Octets trouvés: {ligne[3:] if len(ligne) > 3 else 'N/A'}")
                        print(f"Erreur : {ve}")
                    except Exception as ex:
                        print(f"Erreur inattendue à l'index {index} : {ex}")

            reponse = QMessageBox.question(self, "EXPORT CSV EN NMEA 2000", f"Exportation NMEA 2000 dans le fichier\n"
                                                        f"{os.path.basename(self._file_path_csv)} \n"
                                                        f"est terminée avec succès !\n\n"
                                                        f"Voulez vous voir le fichier "
                                                        f"oû vous avez le résultat ?",
                                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            try:
                if reponse == QMessageBox.Yes:
                    print("L'utilisateur à cliqué sur Oui")
                    excel_path = r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"
                    if os.path.exists(excel_path):
                        subprocess.Popen([excel_path, self._file_path_csv])
                    else:
                        os.startfile(self._file_path_csv)
            except Exception as error :
                QMessageBox.warning(self, "Erreur", f"Impossible d'ouvrir le fichier : {str(error)}")

        except FileNotFoundError:
            QMessageBox.critical(self, "EXPORT CSV EN NMEA 2000", "Fichier source introuvable ou non spécifié.")
        except Exception as error :
            print(f"Erreur inattendue : {error}")
            QMessageBox.critical(self, "EXPORT CSV", "Le fichier est dèjà ouvert!")

    # Méthode pour montrer l'aide. -------------------------------------------------------------------------------------
    @pyqtSlot()
    def show_help(self):
        # Démarrer Quart si nécessaire
        if not self._quart_running:
            self.start_quart_server()
        webbrowser.open("http://127.0.0.1:5000/aide/index")

    # Méthode pour avoir quatre boutons personalisés, qui sont le précédent, le suivant, valider et annuler ------------
    @staticmethod
    def Qmessagebox_4_boutons(titre="Importer",info="information",
                              start_index=None,
                              premier="Précedent",
                              deuxieme="Suivant",
                              troisieme = "Valider",
                              quantite = 5000):

        # Ce bouton n'a pas besoin d'être instancié.
        quatrieme = "Annuler"

        # Création du QMessageBox avec quatre boutons définis par l'utilisateur.
        try:
            msg_box = QMessageBox()
            msg_box.setWindowTitle(titre)
            msg_box.setWindowIcon(QIcon(resource_path("VoilierImage.ico")))

            # Ajout des quatre boutons personalisés.
            bouton_oui = msg_box.addButton(premier, QMessageBox.ActionRole)
            bouton_non = msg_box.addButton(deuxieme, QMessageBox.ActionRole)
            bouton_valider = msg_box.addButton(troisieme, QMessageBox.ActionRole)
            bouton_annuler = msg_box.addButton(quatrieme, QMessageBox.ActionRole)

            # Mettre le focus par défaut sur le 'Valider'
            msg_box.setDefaultButton(bouton_valider)

            continuer = True
            while continuer:
                msg_box.setText(f"{info}, les numéros des lignes de: {start_index + 1} à {start_index + quantite}")
                # Affichage de la boîte de dialogue.
                msg_box.exec()

                # Détection du bouton 'Annuler'
                if msg_box.clickedButton() == bouton_annuler:
                    print("L'utilisateur a annulé la boîte de dialogue.")
                    return None

                # Détection du bouton cliqué
                if msg_box.clickedButton() == bouton_non:
                    start_index += quantite
                elif msg_box.clickedButton() == bouton_oui:
                    start_index = max(0, start_index - quantite)
                elif msg_box.clickedButton() == bouton_valider:
                    print(f"Vous avez validé l'importation des lignes {start_index + 1} à {start_index + quantite}.")
                    continuer = False

            return start_index

        except Exception as error:
            print("Erreur", f"Une erreur s'est produite lors de l'importation : {str(error)}")
            return None

    # Méthode ABOUT. ---------------------------------------------------------------------------------------------------
    @staticmethod
    def show_about_box()-> None:
        # Crée une boîte de dialogue "À propos"
            about_box = QMessageBox()
            about_box.setWindowTitle("À propos de l'application")
            about_box.setWindowIcon(QIcon(resource_path("VoilierImage.ico")))
            about_box.setText(
                "<h3>Application Huahine</h3>"
                "<p>Version 1.0</p>"
                "<p>© 2025 Alain Malvoisin</p>"
                "<p>Ceci est une application qui se connecte sur le bus CAN,</p>" 
                "et décode les trames en NMEA 2000."
            )
            about_box.setIcon(QMessageBox.Information)

            # Affiche la boîte de dialogue
            about_box.exec_()
# =============================================== FIN DES MÉTHODES =====================================================

# ================================================= DEBUT DU QUART =====================================================
# Dans class MainWindow(QMainWindow)
    # Méthode qui lance la "quart_app" ---------------------------------------------------------------------------------
    async def lancer_quart(self):
        if self.quart_running:
            return
        try:
            self.quart_running = True
            print(f"[DEBUG] Demarrage Quart sur http://127.0.0.1:5000")
            print(f"[DEBUG] static_folder: {quart_app.static_folder}")
            print(f"[DEBUG] template_folder: {quart_app.template_folder}")
            await quart_app.run_task(
                host='127.0.0.1',
                port=5000
            )
        except Exception as error:
            self.quart_running = False
            print(f"[ERREUR] Erreur lors du lancement du serveur: {error}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Erreur", f"Erreur du serveur: {str(error)}")

    # Méthode pour arrêter le Quart. -----------------------------------------------------------------------------------
    async def arreter_quart(self):
        """Arrête proprement le serveur Quart"""
        try:
            # Annuler d'abord la tâche serveur si elle existe
            if hasattr(self, 'quart_task') and self.quart_task and not self.quart_task.done():
                try:
                    self.quart_task.cancel()
                    await asyncio.wait_for(self.quart_task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                except Exception as e:
                    print(f"[Quart] Erreur lors de l'annulation de la tâche: {e}")
                finally:
                    self.quart_task = None

            # Tenter une fermeture gracieuse du serveur sans bloquer
            try:
                await asyncio.wait_for(quart_app.shutdown(), timeout=1.0)
            except asyncio.TimeoutError:
                print("[Quart] Timeout sur shutdown(), on continue l'arrêt")
            except Exception as e:
                print(f"[Quart] Erreur pendant shutdown(): {e}")

            # Fermer d'éventuels clients websockets si gérés
            try:
                if hasattr(quart_app, 'clients'):
                    for client in list(quart_app.clients):
                        try:
                            client.close()
                        except Exception:
                            pass
            except Exception:
                pass

            print("Serveur Quart arrêté (best-effort)")
        except Exception as error:
            print(f"Erreur lors de l'arrêt du serveur Quart: {error}")
        finally:
            # Ne pas annuler les autres tâches ici ; le nettoyage global s'en charge.
            self.quart_running = False

    # Méthode qui lance le serveur Quart. ------------------------------------------------------------------------------
    def start_quart_server(self):
        # Démarrer le serveur Quart à la demande s'il n'est pas déjà en cours
        if not getattr(self, 'quart_running', False):
            print("[MAP] Démarrage du serveur Quart à la demande...")
            loop = asyncio.get_event_loop()
            try:
                if loop.is_running():
                    self.quart_task = loop.create_task(self.lancer_quart(), name="QuartServerTask")
                else:
                    loop.run_until_complete(self.lancer_quart())
                self._quart_running = True
            except Exception as e:
                print(f"[MAP] Erreur au démarrage de Quart: {e}")

    # Méthode qui affiche la carte. ------------------------------------------------------------------------------------
    def on_click_map(self):
        """Gestionnaire du clic sur le bouton Map"""
        try:
            print("Bouton 'Map' cliqué !")

            if not self._quart_running:
                self.start_quart_server()

            # Importer et créer la fenêtre de navigation directement
            from webCartes import Navigateur

            # Créer la fenêtre de navigation si elle n'existe pas déjà
            if not hasattr(self, 'nav_window') or self.nav_window is None:
                self.nav_window = Navigateur(parent_window=self)
                self.nav_window.show()
            else:
                # Si la fenêtre existe déjà, la mettre au premier plan
                self.nav_window.show()
                self.nav_window.raise_()
                self.nav_window.activateWindow()

            self.browser_open = True

        except Exception as error:
            print(f"Erreur dans on_click_map: {error}")
            QMessageBox.critical(self, "Erreur", f"Une erreur est survenue: {str(error)}")


# ========================================== CONFIGURATION ET CONSTANTES ===============================================
# Au niveau global de votre fichier, définissez coordinates avec les données par défaut.
coordinates: dict[str, float | dict] = {
    "latitude": 43.243757,
    "longitude": 5.365660,
    "cog": 270.00,
    "sog": 4.0,
    "w_speed_true": 20.0,
    "w_angle_true": 290.0,
    "w_speed_app": 22.0,
    "w_angle_app": 300.0,
    "boat_info": {}
}

# Configuration globale du bateau par défaut.
boat_config = {
    "name": "HUAHINE",
    "type": "Voilier",
    "length": "9.5",
    "width": "3.24",
    "draft": "1.9",
    "mmsi": "227 246 320",
    "speed": "6.0"
}

# Configuration par défaut de la carte
DEFAULT_CONFIG = {
    "center": {
        "latitude": 43.2438,
        "longitude": 5.3656,
        "zoom": 13
    },
    "bounds": {
        "minZoom": 3,
        "maxZoom": 18
    }
}
# ========================================== INITIALISATION DE L'APPLICATION QUART ==================================
# Lance l'application Quart
quart_app = Quart(__name__,
                  static_folder=resource_path('static'),
                  template_folder=resource_path('templates'))

# Enregistrer les routes d'aide sur quart_app
register_aide_routes(quart_app)
# ========================================== CLASSE DE GESTION DE CONFIGURATION ====================================
class BoatConfigManager:
    """Gestionnaire de la configuration du bateau"""

    @staticmethod
    def load_config():
        """Charge la configuration du bateau depuis le fichier JSON"""
        global boat_config
        config_file = 'boat_config.json'
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    boat_config.update(saved_config)
                    # Mettre à jour les coordonnées globales
                    coordinates["boat_info"] = boat_config.copy()
            except Exception as error:
                print(f"Erreur lors du chargement de la configuration: {error}")

    @staticmethod
    def save_config(new_config):
        """Sauvegarde la configuration du bateau"""
        global boat_config

        # Mettre à jour la configuration avec validation
        boat_config.update({
            "name": str(new_config.get("name", "HUAHINE")).strip() or "HUAHINE",
            "type": str(new_config.get("type", "Voilier")).strip() or "Voilier",
            "length": str(new_config.get("length", "12.0")).strip() or "12.0",
            "width": str(new_config.get("width", "3.8")).strip() or "3.8",
            "draft": str(new_config.get("draft", "1.8")).strip() or "1.8",
            "mmsi": str(new_config.get("mmsi", "000000000")).strip() or "999999999",
            "speed": str(new_config.get("speed", "6.0")).strip() or "6.0",
        })

        # Sauvegarder dans le fichier JSON
        config_file = 'boat_config.json'
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(boat_config, f, indent=2, ensure_ascii=False)

        # Mettre à jour les coordonnées globales
        coordinates["boat_info"] = boat_config.copy()
# ========================================== GESTIONNAIRE DES CARTES MBTiles =======================================
class MapTileService:
    """Service de gestion des tuiles de carte"""

    # Mapping des noms de cartes vers les fichiers MBTiles (relatifs au dossier de l'exécutable / projet)
    MBTILES_FILES = {
        'cartes1.mbtiles': os.path.join('static', 'cartes1.mbtiles'),
        'cartes2.mbtiles': os.path.join('static', 'cartes2.mbtiles'),
        'cartes3.mbtiles': os.path.join('static', 'cartes3.mbtiles')
    }

    @staticmethod
    def _base_dir():
        """Retourne le dossier de base pour résoudre les chemins (exécutable si congelé, sinon dossier du script)."""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        # Mode dev : dossier du fichier HUAHINE.py, pas le répertoire courant
        return os.path.dirname(os.path.abspath(__file__))

    @staticmethod
    def resolve_mbtiles_path(relative_path):
        """Construit un chemin absolu vers un fichier '.mbtiles' en évitant toute dépendance au répertoire courant."""
        base = MapTileService._base_dir()
        return os.path.join(base, relative_path)

    @staticmethod
    def get_tile_data(map_name, z, x, y):
        """Récupère les données d'une tuile spécifique"""
        print(f"Demande de tuile : carte={map_name}, z={z}, x={x}, y={y}")

        # Vérifier si la carte demandée existe
        if map_name not in MapTileService.MBTILES_FILES:
            print("CARTE NON TROUVÉE")
            return None, 404

        try:
            # Calculer la coordonnée Y pour le format TMS
            y_tms = y

            # Connexion à la base MBTiles appropriée
            relative_path = MapTileService.MBTILES_FILES[map_name]
            db_path = MapTileService.resolve_mbtiles_path(relative_path)

            print(f"[DEBUG] db_path: {db_path}")
            print(f"[DEBUG] Fichier existe: {os.path.exists(db_path)}")
            conn = sqlite3.connect(db_path)

            cursor = conn.cursor()

            cursor.execute('''
                SELECT tile_data FROM tiles 
                WHERE zoom_level=? AND tile_column=? AND tile_row=?
            ''', (z, x, y_tms))

            tile_data = cursor.fetchone()
            conn.close()

            if tile_data:
                print(f"Tuile trouvée pour {map_name} z={z}, x={x}, y={y}")
                return tile_data[0], 200
            else:
                print(f"Tuile non trouvée pour {map_name} z={z}, x={x}, y={y}")
                return None, 404

        except Exception as error:
            print(f"Erreur pour la tuile {map_name} z={z}, x={x}, y={y}: {error}")
            return None, 500

    @staticmethod
    def get_map_bounds(mbtiles_path):
        """Récupère les limites de la carte depuis les métadonnées"""
        try:
            # Résoudre le chemin de manière robuste (exe_dir en prod, dossier du script en dev)
            if mbtiles_path and os.path.isabs(mbtiles_path):
                db_path = mbtiles_path
            elif mbtiles_path:
                db_path = MapTileService.resolve_mbtiles_path(mbtiles_path)
            else:
                # Par défaut, utiliser cartes1.mbtiles à l'endroit prévu
                db_path = MapTileService.resolve_mbtiles_path(MapTileService.MBTILES_FILES['cartes1.mbtiles'])

            print(f"[DEBUG] get_map_bounds db_path: {db_path}")
            print(f"[DEBUG] Fichier existe: {os.path.exists(db_path)}")
            conn = sqlite3.connect(db_path)

            cursor = conn.cursor()

            cursor.execute("SELECT value FROM metadata WHERE name='bounds'")
            bounds = cursor.fetchone()

            if bounds:
                west, south, east, north = map(float, bounds[0].split(','))
                center_lat = (north + south) / 2
                center_lon = (east + west) / 2
                conn.close()
                return center_lat, center_lon
            else:
                conn.close()
                return None, None

        except Exception as error:
            print(f"Erreur lors de la récupération des limites : {error}")
            return None, None
# ========================================== GESTIONNAIRE DE FICHIERS D'HISTORIQUE ===============================
class HistoryFileManager:
    """Gestionnaire des fichiers d'historique de navigation"""

    STATIC_FOLDER = 'history'

    @staticmethod
    def ensure_static_folder():
        """S'assure que le dossier static existe"""
        os.makedirs(HistoryFileManager.STATIC_FOLDER, exist_ok=True)

    @staticmethod
    def save_history(filename, history_data):
        """Sauvegarde l'historique dans un fichier"""
        try:
            HistoryFileManager.ensure_static_folder()

            # Normaliser le nom de fichier pour la sécurité
            filename = os.path.basename(filename)
            file_path = os.path.join(HistoryFileManager.STATIC_FOLDER, filename)

            # Sanitize: garantir angles de vent en [0,360)
            def _norm360(v):
                try:
                    a = float(v) % 360.0
                    if a < 0:
                        a += 360.0
                    return a
                except Exception:
                    return v

            sanitized = []
            if isinstance(history_data, list):
                for item in history_data:
                    if isinstance(item, dict):
                        it = dict(item)
                        if 'w_angle_true' in it and it['w_angle_true'] is not None:
                            it['w_angle_true'] = _norm360(it['w_angle_true'])
                        if 'w_angle_app' in it and it['w_angle_app'] is not None:
                            it['w_angle_app'] = _norm360(it['w_angle_app'])
                        sanitized.append(it)
                    else:
                        sanitized.append(item)
            else:
                sanitized = history_data

            with open(file_path, 'w') as f:
                json.dump(sanitized, f)

            return {"status": "success", "message": f"Historique sauvegardé dans {filename}"}

        except Exception as error:
            return {"status": "error", "message": str(error)}

    @staticmethod
    def load_history(filename):
        """Charge l'historique depuis un fichier"""
        try:
            # Normaliser le nom de fichier pour la sécurité
            filename = os.path.basename(filename)
            file_path = os.path.join(HistoryFileManager.STATIC_FOLDER, filename)

            with open(file_path, 'r') as f:
                history_data = json.load(f)

            return history_data

        except Exception as error:
            return {"status": "error", "message": str(error)}

    @staticmethod
    def list_json_files():
        """Liste tous les fichiers JSON dans le dossier history"""
        try:
            folder = Path(HistoryFileManager.STATIC_FOLDER)
            files = []

            for file in folder.glob("*.json"):
                stat = file.stat()

                files.append({
                    "name": file.name,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            return files
        except Exception as error:
            return {"status": "error", "message": str(error)}

    @staticmethod
    def delete_history(filename):
        """Supprime un fichier d'historique"""
        try:
            if not filename:
                return {"status": "error", "message": "Nom de fichier manquant"}

            # Normaliser le nom de fichier
            if not filename.endswith('.json'):
                filename = f"{filename}.json"

            # Sécurité pour éviter les chemins malveillants
            filename = os.path.basename(filename)
            file_path = os.path.join(HistoryFileManager.STATIC_FOLDER, filename)

            # Vérifier si le fichier existe
            if not os.path.exists(file_path):
                return {
                    "status": "error",
                    "message": f"Le fichier {filename} n'existe pas dans le dossier static"
                }

            # Supprimer le fichier
            os.remove(file_path)

            return {
                "status": "success",
                "message": f"Fichier {filename} supprimé avec succès"
            }

        except Exception as error:
            print(f"Erreur lors de la suppression: {error}")
            return {
                "status": "error",
                "message": f"Erreur lors de la suppression: {str(error)}"
            }

# ========================================== GESTIONNAIRE DE FICHIERS DE ROUTES =====================================
class RouteFileManager:
    """Gestionnaire des fichiers de routes"""

    STATIC_FOLDER = 'routes'

    @staticmethod
    def ensure_routes_folder():
        """S'assure que le dossier routes existe"""
        os.makedirs(RouteFileManager.STATIC_FOLDER, exist_ok=True)

    @staticmethod
    def save_route(filename, route_data):
        """Sauvegarde la route dans un fichier"""
        try:
            RouteFileManager.ensure_routes_folder()

            # Normaliser le nom de fichier pour la sécurité
            filename = os.path.basename(filename)
            file_path = os.path.join(RouteFileManager.STATIC_FOLDER, filename)

            with open(file_path, 'w') as f:
                json.dump(route_data, f)

            return {"status": "success", "message": f"Route sauvegardée dans {filename}"}

        except Exception as error:
            return {"status": "error", "message": str(error)}

    @staticmethod
    def load_route(filename):
        """Charge la route depuis un fichier"""
        try:
            # Normaliser le nom de fichier pour la sécurité
            filename = os.path.basename(filename)
            file_path = os.path.join(RouteFileManager.STATIC_FOLDER, filename)

            with open(file_path, 'r') as f:
                route_data = json.load(f)

            return route_data

        except Exception as error:
            return {"status": "error", "message": str(error)}

    @staticmethod
    def list_json_files():
        """Liste tous les fichiers JSON dans le dossier routes avec leurs dates"""
        try:
            folder = Path(RouteFileManager.STATIC_FOLDER)
            files = []

            for file in folder.glob("*.json"):
                stat = file.stat()

                files.append({
                    "name": file.name,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

            return files

        except Exception as error:
            return {"status": "error", "message": str(error)}

    @staticmethod
    def delete_route(filename):
        """Supprime un fichier de route"""
        try:
            if not filename:
                return {"status": "error", "message": "Nom de fichier manquant"}

            # Normaliser le nom de fichier
            if not filename.endswith('.json'):
                filename = f"{filename}.json"

            # Sécurité pour éviter les chemins malveillants
            filename = os.path.basename(filename)
            file_path = os.path.join(RouteFileManager.STATIC_FOLDER, filename)

            # Vérifier si le fichier existe
            if not os.path.exists(file_path):
                return {
                    "status": "error",
                    "message": f"Le fichier {filename} n'existe pas dans le dossier routes"
                }

            # Supprimer le fichier
            os.remove(file_path)

            return {
                "status": "success",
                "message": f"Fichier {filename} supprimé avec succès"
            }

        except Exception as error:
            print(f"Erreur lors de la suppression: {error}")
            return {
                "status": "error",
                "message": f"Erreur lors de la suppression: {str(error)}"
            }
# ============================================= CARTES PRINCIPALES =====================================================
@quart_app.route('/test')
async def test_route():
    """Route de test pour vérifier que Quart fonctionne"""
    print("[DEBUG] Route /test appelée")
    return "Quart fonctionne !"

@quart_app.route('/')
@quart_app.route('/map')
async def map_page():
    """Route principale pour afficher la carte"""
    try:
        # Vous pouvez utiliser n'importe quelle carte comme carte par défaut
        # Passer un chemin relatif pour éviter d'utiliser le répertoire courant ou _MEIPASS
        default_mbtiles = MapTileService.MBTILES_FILES['cartes1.mbtiles']

        logging.info(
            f"Coordonnées envoyées : {DEFAULT_CONFIG['center']['latitude']}, {DEFAULT_CONFIG['center']['longitude']}")

        # Récupération des limites de la carte par défaut
        center_lat, center_lon = MapTileService.get_map_bounds(default_mbtiles)

        # Utiliser les valeurs par défaut si les limites ne sont pas disponibles
        if center_lat is None or center_lon is None:
            center_lat = DEFAULT_CONFIG['center']['latitude']
            center_lon = DEFAULT_CONFIG['center']['longitude']

        return await render_template(
            'index.html',
            center_lat=center_lat,
            center_lon=center_lon,
            default_zoom=DEFAULT_CONFIG['center']['zoom'],
            min_zoom=DEFAULT_CONFIG['bounds']['minZoom'],
            max_zoom=DEFAULT_CONFIG['bounds']['maxZoom']
        )

    except Exception as error:
        print(f"Erreur: {str(error)}")
        return await render_template(
            'index.html',
            **DEFAULT_CONFIG['center'],
            **DEFAULT_CONFIG['bounds']
        )
# ========================================== ROUTES DES TUILES DE CARTE ================================================
@quart_app.route('/tile/<string:map_name>/<int:z>/<int:x>/<int:y>')
async def serve_tile(map_name, z, x, y):
    """Route pour servir les tuiles de carte MBTiles"""
    tile_data, status_code = MapTileService.get_tile_data(map_name, z, x, y)

    if status_code == 200 and tile_data:
        return Response(tile_data, mimetype='image/png')
    elif status_code == 404:
        return Response('Carte non trouvée', status=404)
    else:
        return Response('', status=500)

@quart_app.route('/tiles/<int:z>/<int:x>/<int:y>.png')
async def get_tile(z, x, y):
    """Route pour servir les tuiles statiques"""
    try:
        tile_path = resource_path(os.path.join('static', 'tiles', f'{z}_{x}_{y}.png'))
        if os.path.exists(tile_path):
            with open(tile_path, 'rb') as f:
                tile_data = f.read()
            return Response(tile_data, mimetype='image/png')
        else:
            return Response('', status=404)
    except Exception as error:
        print(f"Erreur lors de la récupération de la tuile : {error}")
        return Response('', status=500)

# ========================================== ROUTES DES VENTS (supprimées — géré côté frontend) ========================

# =============================================== ROUTES API ===========================================================
@quart_app.route('/api/get_coordinates')
async def get_coordinates():
    """ 'API' pour récupérer les coordonnées actuelles """
    try:
        return jsonify(coordinates)  # Retourne les coordonnées stockées globalement
    except Exception as error:
        print(f"Erreur lors de la récupération des coordonnées : {error}")
        return jsonify({"error": str(error)}), 500

@quart_app.route('/get_ships')
async def get_ships():
    """ API pour récupérer les informations des navires AIS"""
    try:
        # Récupération des navires MMSI
        raw_ships = window.nmea_2000.get_all_ais_ships()
        print(f"Navires bruts récupérés: {len(raw_ships)}")

        if not raw_ships:
            print("❌ Aucun navire AIS disponible")
            return jsonify([])

        # Récupérer la position actuelle de votre bateau
        my_latitude = None
        my_longitude = None

        try:
            if hasattr(window, 'coordinates') and window.coordinates:
                my_latitude = getattr(window.coordinates, 'latitude', None)
                my_longitude = getattr(window.coordinates, 'longitude', None)
        except:
            # Position par défaut si non trouvée
            my_latitude = 43.2438
            my_longitude = 5.3656

        # Conversion au format attendu avec validation
        ships = []
        for i, ship in enumerate(raw_ships):
            try:
                # Validation des données requises
                mmsi = ship.get("ais_mmsi")
                latitude = ship.get("latitude")
                longitude = ship.get("longitude")

                print(f"Navire {i + 1}: MMSI={mmsi}, Lat={latitude}, Lon={longitude}")

                # Vérifier que les coordonnées sont présentes et valides
                if not mmsi or latitude is None or longitude is None:
                    print(f"❌ Navire ignoré - données manquantes: MMSI={mmsi}, Lat={latitude}, Lon={longitude}")
                    continue

                # Conversion sécurisée des coordonnées
                try:
                    lat_float = float(latitude) if latitude != 'N/A' else None
                    lon_float = float(longitude) if longitude != 'N/A' else None

                    if lat_float is None or lon_float is None:
                        print(f"❌ Navire {mmsi} ignoré - coordonnées invalides")
                        continue

                except (ValueError, TypeError) as e:
                    print(f"❌ Erreur conversion coordonnées navire {mmsi}: {e}")
                    continue

                # Conversion sécurisée des autres valeurs
                try:
                    cog_float = float(ship.get("cog", 0)) if ship.get("cog") not in [None, 'N/A', ''] else 0.0
                    sog_float = float(ship.get("sog", 0)) if ship.get("sog") not in [None, 'N/A', ''] else 0.
                    long_float = float(ship.get("long", 0)) if ship.get("long") not in [None, 'N/A', ''] else 0.0
                    large_float = float(ship.get("large", 0)) if ship.get("large") not in [None, 'N/A', ''] else 0.0
                except (ValueError, TypeError):
                    cog_float = 0.0
                    sog_float = 0.0

                # Calculer la distance
                distance = calculate_distance_nm(my_latitude, my_longitude, lat_float, lon_float)

                ship_data = {
                    "mmsi": str(mmsi),
                    "name": ship.get("name", "Inconnu"),
                    "latitude": lat_float,
                    "longitude": lon_float,
                    "cog": cog_float,
                    "sog": sog_float,
                    "class": ship.get("classe", "N/A"),
                    "distance": distance,  # ✅ Ajout de la distance calculée
                    "long": long_float,
                    "large": large_float
                }

                ships.append(ship_data)
                print(f"✅ Navire {mmsi} ajouté: {ship_data}")

            except Exception as e:
                print(f"❌ Erreur traitement navire {i + 1}: {e}")
                continue

        # Debug final
        print(f"📡 Envoi de {len(ships)} navires AIS valides depuis [{my_latitude:.4f}, {my_longitude:.4f}]")
        for ship in ships:
            print(
                f"  - {ship['mmsi']}: [{ship['latitude']}, {ship['longitude']}] - Distance: {ship.get('distance', 'N/A')} - {ship['name']}")

        return jsonify(ships)

    except Exception as e:
        print(f"❌ ERREUR dans get_ships: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 500

# ========================================== ROUTES POUR LES MMSI ======================================================
import math

def calculate_distance_nm(lat1, lon1, lat2, lon2):
    """
    Calcule la distance entre deux points en milles nautiques en haversine
    """
    if any(coord is None or coord == 'N/A' for coord in [lat1, lon1, lat2, lon2]):
        return 'N/A'

    try:
        # Conversion en radians
        lat1_rad = math.radians(float(lat1))
        lon1_rad = math.radians(float(lon1))
        lat2_rad = math.radians(float(lat2))
        lon2_rad = math.radians(float(lon2))

        # Formule haversine
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        # Rayon de la Terre en milles nautiques (3440.065 NM)
        earth_radius_nm = 3440.065

        distance = earth_radius_nm * c
        return f"{distance:.1f} NM"

    except (ValueError, TypeError) as e:
        print(f"Erreur calcul distance: {e}")
        return 'N/A'

@quart_app.route('/api/ais_ships')
async def get_ais_ships():
    """
    API pour récupérer la liste des navires AIS détectés
    """
    try:
        raw_ships = window.nmea_2000.get_all_ais_ships()

        # Récupérer la position actuelle de votre bateau
        my_latitude = None
        my_longitude = None

        # Essayer de récupérer depuis les coordonnées globales
        try:
            #if hasattr(window, 'coordinates') and window.coordinates:
                my_latitude = coordinates["latitude"] #getattr(window.coordinates, 'latitude', None)
                my_longitude = coordinates["longitude"] #getattr(window.coordinates, 'longitude', None)
        except:
            pass

        # Si pas trouvé, essayer depuis la dernière position connue
        if not my_latitude or not my_longitude:
            try:
                response = await window.get_current_coordinates()  # Si cette méthode existe
                if response and 'latitude' in response and 'longitude' in response:
                    my_latitude = response['latitude']
                    my_longitude = response['longitude']
            except:
                # Position par défaut (Marseille) si aucune position trouvée
                my_latitude = 43.2438
                my_longitude = 5.3656
                print("⚠️ Position du bateau non trouvée, utilisation position par défaut")

        # Formatage des données pour l'affichage
        ships_data = []
        for ship in raw_ships:
            # Calculer la distance réelle
            ship_lat = ship.get('latitude', 'N/A')
            ship_lon = ship.get('longitude', 'N/A')

            distance = calculate_distance_nm(my_latitude, my_longitude, ship_lat, ship_lon)

            ship_info = {
                'mmsi': ship.get('ais_mmsi', 'N/A'),
                'name': ship.get('name', 'Inconnu'),
                'latitude': ship_lat,
                'longitude': ship_lon,
                'cog': ship.get('cog', 'N/A'),
                'sog': ship.get('sog', 'N/A'),
                'classe': ship.get('classe', 'N/A'),
                'distance': distance,  # Distance calculée dynamiquement par la formule haversine
                'last_update': 'En cours',
                'long': ship.get('long', 'N/A'),
                'large': ship.get('large', 'N/A')
                # 'last_update': time

            }
            ships_data.append(ship_info)

        print(f"📡 Distances calculées depuis [{my_latitude:.4f}, {my_longitude:.4f}]")

        return jsonify({
            'success': True,
            'ships': ships_data,
            'total': len(ships_data)
        })

    except Exception as e:
        print(f"❌ Erreur dans get_ais_ships: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'ships': [],
            'total': 0
        }), 500
# ========================================== ROUTES DE GESTION D'HISTORIQUE ============================================
@quart_app.route('/save_history', methods=['POST'])
async def save_history():
    """Route pour sauvegarder l'historique de navigation"""
    try:
        data = await request.get_json()
        filename = data.get("filename", "ParcoursA.json")
        history_data = data.get("history")

        result = HistoryFileManager.save_history(filename, history_data)
        return jsonify(result)

    except Exception as error:
        return jsonify({"status": "error", "message": str(error)}), 500

@quart_app.route('/load_history', methods=['POST'])
async def load_history():
    """Route pour charger l'historique de navigation"""
    try:
        data = await request.get_json()
        filename = data.get("filename", "ParcoursA.json")

        result = HistoryFileManager.load_history(filename)
        return jsonify(result)

    except Exception as error:
        return jsonify({"status": "error", "message": str(error)}), 500

@quart_app.route('/list_json_files', methods=['GET'])
async def list_json_files():
    """Route pour lister tous les fichiers JSON d'historique"""
    try:
        folder = Path(HistoryFileManager.STATIC_FOLDER)
        files = []

        for file in folder.glob("*.json"):
            stat = file.stat()

            files.append({
                "name": file.name,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })

        return files
    except Exception as error:
        return jsonify({"status": "error", "message": str(error)}), 500

@quart_app.route('/delete_history', methods=['POST'])
async def delete_history():
    """Route pour supprimer un fichier d'historique"""
    try:
        data = await request.get_json()
        filename = data.get('filename')

        result = HistoryFileManager.delete_history(filename)
        return jsonify(result)

    except Exception as error:
        print(f"Erreur lors de la suppression: {error}")
        return jsonify({
            "status": "error",
            "message": f"Erreur lors de la suppression: {str(error)}"
        })
# =================================================== GESTION DES ROUTES ===============================================
@quart_app.route('/save_route', methods=['POST'])
async def save_route():
    """Route pour sauvegarder une route de navigation"""
    try:
        data = await request.get_json()
        filename = data.get("filename", "Route.json")
        route_data = data.get("route")
        result = RouteFileManager.save_route(filename, route_data)
        return jsonify(result)

    except Exception as error:
        return jsonify({"status": "error", "message": str(error)}), 500

@quart_app.route('/load_route', methods=['POST'])
async def load_route():
    """Route pour charger une route de navigation"""
    try:
        data = await request.get_json()
        filename = data.get("filename", "Route.json")

        result = RouteFileManager.load_route(filename)
        return jsonify(result)

    except Exception as error:
        return jsonify({"status": "error", "message": str(error)}), 500

@quart_app.route('/list_route_files', methods=['GET'])
async def list_route_files():
    """Route pour lister tous les fichiers JSON de routes"""
    try:
        files = RouteFileManager.list_json_files()
        return jsonify(files)
    except Exception as error:
        return jsonify({"status": "error", "message": str(error)}), 500

@quart_app.route('/delete_route', methods=['POST'])
async def delete_route():
    """Route pour supprimer un fichier de route"""
    try:
        data = await request.get_json()
        filename = data.get('filename')

        result = RouteFileManager.delete_route(filename)
        return jsonify(result)

    except Exception as error:
        print(f"Erreur lors de la suppression: {error}")
        return jsonify({
            "status": "error",
            "message": f"Erreur lors de la suppression: {str(error)}"
        })
# ================================================ CONFIGURATION DU BATEAU =============================================
@quart_app.route('/get_boat_config', methods=['GET'])
async def get_boat_config():
    """Route pour récupérer la configuration actuelle du bateau"""
    return jsonify(boat_config)


@quart_app.route('/save_boat_config', methods=['POST'])
async def save_boat_config():
    """Route pour sauvegarder la configuration du bateau"""
    try:
        data = await request.get_json()
        BoatConfigManager.save_config(data)

        return jsonify({"status": "success", "message": "Configuration sauvegardée avec succès"})

    except Exception as error:
        print(f"Erreur lors de la sauvegarde: {error}")
        return jsonify({"status": "error", "message": str(error)}), 500

# =============================================== INITIALISATION =======================================================
# Charger la configuration du bateau au démarrage
BoatConfigManager.load_config()


# ========================================== MIDDLEWARE ET CONFIGURATION ===============================================
@quart_app.after_request
async def after_request(response):
    """Middleware pour ajouter les en-têtes CORS"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

@quart_app.route('/status')
async def get_status():
    try:
        active = getattr(getattr(quart_app, 'can_app', None), '_encours', False)
        print(f"ETAT = {active}")
        return jsonify({'active': active})
    except Exception as e:
        return jsonify({'active': False, 'error': str(e)}), 500

# Fenêtre des listes des participants ----------------------------------------------------------------------------------
configuration = {}

@quart_app.route('/api/configuration')
async def get_configuration():
    return jsonify(configuration)

class MyHandler:
    def __init__(self, can_interface):
        self._can_interface = can_interface

    async def send(self):
        try:
            if self._can_interface is None:
                return {"status": "error", "message": "Interface CAN non initialisée"}
            res = await self._can_interface.send_dll('all')    # Demande l'adresse des instruments.
            print("Méthode send appelée, résultat:", res)
            return {"status": "success", "message": "Trame CAN envoyée", "result": bool(res)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

@quart_app.route('/send', methods=['POST'])
async def trigger_send():
    print("Route /send appelée")
    result = await handler.send()
    return jsonify(result)
# =============================================== FIN DU QUART =========================================================

def bring_to_front(window_title):

    def enum_handler(hwnd, _):
        title = win32gui.GetWindowText(hwnd)

        if window_title.lower() in title.lower():
            print("✅ Fenêtre trouvée :", title)

            try:
                # Récupère les threads
                fg_window = win32gui.GetForegroundWindow()
                fg_thread = win32process.GetWindowThreadProcessId(fg_window)[0]
                this_thread = win32api.GetCurrentThreadId()

                # Attache les threads pour contourner la restriction Windows
                win32process.AttachThreadInput(this_thread, fg_thread, True)

                # Restaure et met au premier plan
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.BringWindowToTop(hwnd)
                win32gui.SetForegroundWindow(hwnd)

                # Détache les threads
                win32process.AttachThreadInput(this_thread, fg_thread, False)

            except Exception as e:
                print("Erreur SetForegroundWindow:", e)

    win32gui.EnumWindows(enum_handler, None)

@quart_app.get("/focus-huahine")
async def focus_huahine():
    bring_to_front("CAN bus et NMEA 2000 en temps réel")  # Titre exact de ta fenêtre PyQt
    return "OK"

# Méthode asynchrone pour arrêter les tâches ---------------------------------------------------------------------------
async def cleanup(window):
    print("Nettoyage en cours...")

    # Arrêter Quart
    if getattr(window, "quart_running", False):
        try:
            asyncio.ensure_future(window.arreter_quart())
        except Exception as e:
            print(f"[CLEANUP] Erreur arreter_quart: {e}")
        window.quart_running = False

    # Annuler les tâches
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for t in tasks:
        t.cancel()

    print("Nettoyage terminé")
    sys.exit(0)

from quart import Response

@quart_app.route("/wind.json")
async def wind_json():
    try:
        wind_path = resource_path("wind.json")

        with open(wind_path, "r", encoding="utf-8") as f:
            data = f.read()
        return Response(data, mimetype="application/json")
    except Exception as e:
        print(f"Erreur chargement wind.json: {e}")
        return Response("{}", mimetype="application/json", status=500)



# ********************************************* LANCE L'APPLICATION ****************************************************
if __name__ == "__main__":
    # Rediriger les print vers un fichier de log SEULEMENT pour l'exe.
    if getattr(sys, 'frozen', False):
        # On est dans l'exe PyInstaller
        log_file = open('huahine_debug.log', 'w', encoding='utf-8')
        sys.stdout = log_file
        sys.stderr = log_file

    print(f"SQLite Version: {sqlite3.sqlite_version}")
    print("=== Serveur de tuiles MBTiles ===")
    print("Accédez à http://127.0.0.1:5000/ pour voir la carte")

    # Test des imports nécessaires
    try:
        import hypercorn
        print("[OK] Hypercorn disponible")
    except ImportError as e:
        print(f"[ERREUR] Hypercorn non disponible: {e}")



    # Définir l'attribut AVANT la création de QApplication
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

    try:
        app = QApplication(sys.argv)

        # Création de la fenêtre principale
        window = MainWindow()
        window.show()

        # Création de l'objet CAN'
        handler = MyHandler(window.can_interface_app._can_interface)

        # Intégration asyncio avec PyQt5
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)

        # Variable pour stocker la référence de la tâche principale
        main_task = None
        # Le serveur Quart sera démarré à la demande lors du clic sur « Map ».

        shutting_down = False

        def handle_shutdown():
            """Gestionnaire d'arrêt propre"""
            global shutting_down
            if shutting_down:
                return
            shutting_down = True
            print("Arrêt de l'application demandé...")
            asyncio.ensure_future(cleanup(window), loop=loop)

        # Exposer le gestionnaire sur la fenêtre pour permettre un appel direct
        window.handle_shutdown = handle_shutdown

        # Gestionnaire d'exception pour la boucle
        def exception_handler(loop, context):
            print(f"Exception dans la boucle asyncio: {context}")
            if 'exception' in context:
                print(f"Détails de l'exception: {context['exception']}")

        loop.set_exception_handler(exception_handler)

        # Démarrage de la boucle principale avec gestion d'erreur
        try:
            print("Démarrage de la boucle principale...")
            with loop:
                loop.run_forever()
        except KeyboardInterrupt:
            print("Interruption clavier détectée")
        except Exception as error:
            print(f"Erreur dans la boucle principale: {error}")
        finally:
            print("Fermeture de la boucle asyncio")
            # S'assurer que toutes les tâches sont nettoyées
            pending_tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
            if pending_tasks:
                print(f"Nettoyage final de {len(pending_tasks)} tâches restantes...")
                for task in pending_tasks:
                    task.cancel()

    except Exception as e:
        print(f"Erreur principale: {e}")
        QMessageBox.critical(None, "Erreur", f"Une erreur s'est produite: {str(e)}")
        sys.exit(1)
    finally:
        print("Application terminée")
        # Forcer la fermeture du processus si quelque chose garde le process vivant
        try:
            from PyQt5.QtWidgets import QApplication
            _app = QApplication.instance()
            if _app is not None:
                _app.quit()
        except Exception:
            pass
        try:
            sys.exit(0)
        except SystemExit:
            pass

#  ****************************************** FIN DE L'APPLICATION *****************************************************'
