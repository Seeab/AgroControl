# aplicaciones/apps.py
from django.apps import AppConfig

class AplicacionesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'aplicaciones'

    def ready(self):
        # Importar las señales para que se registren
        import aplicaciones.signals