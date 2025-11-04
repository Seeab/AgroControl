<<<<<<< HEAD
# aplicaciones/apps.py
from django.apps import AppConfig

class AplicacionesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'aplicaciones'

    def ready(self):
        # Importar las señales para que se registren
        import aplicaciones.signals
=======
from django.apps import AppConfig


class AplicacionesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'aplicaciones'
>>>>>>> 45ec01aa04e8b7c823306d24fc4db20639502916
