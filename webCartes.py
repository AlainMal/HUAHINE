import sys
import webbrowser
from PyQt5.QtCore import QUrl, Qt, QEvent
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QDesktopServices


class BrowserView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._temp_views = []  # Empêche la collecte prématurée des vues temporaires

    def createWindow(self, _type):
        """
        Intercepte target="_blank" et ouvre l'URL dans le navigateur par défaut.
        """
        temp_view = QWebEngineView()

        def handle_url(url):
            webbrowser.open(url.toString())  # Ouvre dans Chrome/Edge/Firefox
            temp_view.deleteLater()

        temp_view.urlChanged.connect(handle_url)
        self._temp_views.append(temp_view)
        return temp_view


class HelpWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aide – HAUHINE")
        self.setGeometry(250, 150, 900, 700)

        self.browser = BrowserView()
        self.setCentralWidget(self.browser)

    def show_help(self, url):
        self.browser.setUrl(QUrl(url))
        self.show()
        self.raise_()
        self.activateWindow()


class Navigateur(QMainWindow):
    def __init__(self, parent_window=None):
        super().__init__()
        self.help_window = HelpWindow()
        self.parent_window = parent_window
        self.setWindowTitle("HAUHINE - CARTES MARINES")
        self.setGeometry(200, 100, 1200, 800)

        self.setWindowIcon(QIcon("./VoilierImage.ico"))

        # Vue Web
        self.browser = BrowserView()
        # Gestion des téléchargements
        profile = self.browser.page().profile()
        profile.downloadRequested.connect(self.handle_download)
        self.browser.setUrl(QUrl("http://127.0.0.1:5000/"))
        self.setCentralWidget(self.browser)
        self.showMaximized()

        # Intercepter les touches directement au niveau de la WebView
        self.browser.installEventFilter(self)

    def handle_download(self, download):
        url = download.url().toString()
        print("Téléchargement intercepté :", url)

        # Ouvre le lien dans le navigateur par défaut
        import webbrowser
        webbrowser.open(url)

        # Annule le téléchargement interne de Qt
        download.cancel()

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "Quitter",
            "Voulez-vous quitter la carte ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F1:
            event.accept()
            self.help_window.show_help("http://127.0.0.1:5000/aide/cartes")
            return

        elif event.key() == Qt.Key_F3:
            event.accept()
            QDesktopServices.openUrl(QUrl("http://127.0.0.1:5000/?lancerHistorique=true&idCarte=123"))
            return

        elif event.key() == Qt.Key_F9:
            event.accept()
            profile = self.browser.page().profile()

            profile.clearHttpCache()
            profile.clearAllPersistentData()
            profile.clearAllVisitedLinks()
            profile.cookieStore().deleteAllCookies()
            print("Cache et données effacés — JS/CSS seront rechargés.")
            return True

        elif event.key() == Qt.Key_F2:
            if self.parent_window:
                self.parent_window.show()
                self.parent_window.raise_()
                self.parent_window.activateWindow()
            return

        super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Navigateur()
    window.show()
    sys.exit(app.exec_())