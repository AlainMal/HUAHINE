"""
Module pour enregistrer les routes d'aide sur l'application Quart principale via un Blueprint.
Les templates sont dans aide/templates/ et les fichiers statiques dans aide/static/.
"""

def register_aide_routes(app):
    """
    Enregistre les routes d'aide sur l'application Quart fournie en utilisant un Blueprint
    dédié avec ses propres dossiers templates et static.

    Args:
        app: Instance de Quart (quart_app) depuis HUAHINE.py
    """
    from quart import Blueprint, render_template
    import sys
    import os

    def resource_path(relative_path):
        """Obtenir le chemin absolu vers les ressources (compatible PyInstaller)
        Préfère le chemin local s'il existe (utile en dev ou si de nouveaux fichiers
        ne sont pas encore inclus dans le bundle PyInstaller), sinon retombe sur _MEIPASS.
        """
        try:
            local_path = os.path.abspath(relative_path)
            if os.path.exists(local_path):
                return local_path
        except Exception:
            pass
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
        return os.path.join(base_path, relative_path)

    # Crée un Blueprint pour la section Aide, avec ses propres dossiers templates et static
    aide_bp = Blueprint(
        'aide', __name__,
        template_folder=resource_path('aide\\templates'),
        static_folder=resource_path('aide\\static'),
        static_url_path='/static'
    )

    # Route de test
    @aide_bp.route('/test')
    async def aide_test():
        return "Route d'aide fonctionne !"

    # Les fichiers statiques de l'aide seront servis automatiquement par le Blueprint sous /aide/static/
    # (grâce à static_folder et static_url_path). Si besoin d'en-têtes no-cache, on peut ajouter une route dédiée.

    #@aide_bp.route('/')
    @aide_bp.route('/index')
    async def aide_index():
        try:
            return await render_template('aide_index.html')
        except Exception as e:
            print(f"[ERREUR AIDE] Erreur lors du rendu de index.html (aide): {e}")
            import traceback
            traceback.print_exc()
            return f"Erreur: {str(e)}", 500

    @aide_bp.route('/enregistre')
    async def aide_enregistre_page():
        return await render_template('enregistre.html')

    @aide_bp.route('/import')
    async def aide_import_page():
        return await render_template('import.html')

    @aide_bp.route('/export')
    async def aide_export_page():
        return await render_template('export.html')

    @aide_bp.route('/cartes')
    async def aide_cartes_page():
        return await render_template('cartes.html')

    @aide_bp.route('/install')
    async def aide_install_page():
        return await render_template('install.html')

    @aide_bp.route('/nmea')
    async def aide_nmea_page():
        return await render_template('nmea.html')

    # Enregistrer le Blueprint sur l'application principale sous le préfixe /aide
    app.register_blueprint(aide_bp, url_prefix='/aide')

    print("[AIDE] Blueprint d'aide enregistré sur le serveur Quart principal")

def start_help_server():
    """
    Fonction de compatibilité - ne fait rien car les routes sont déjà enregistrées.
    Le serveur Quart principal gère tout.
    """
    print("[AIDE] start_help_server() appelé - routes déjà disponibles sur quart_app")
