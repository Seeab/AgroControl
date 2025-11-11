# AgroControl/urls.py (Este es el archivo central)

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- 1. RUTAS DE APPS (con prefijo) ---
    # Pon todas tus apps que tienen prefijo PRIMERO.
    # Asegúrate de que CADA UNA tenga su 'namespace'.
    
    path('aplicaciones/', include('aplicaciones.urls', namespace='aplicaciones')),
    path('riego/', include('riego.urls', namespace='riego')),
    
    # ¡ESTAS LÍNEAS SON LAS QUE PROBABLEMENTE TIENES MAL!
    path('cuarteles/', include('cuarteles.urls', namespace='cuarteles')),
    path('inventario/', include('inventario.urls', namespace='inventario')),
    
    # --- 2. RUTA RAÍZ (al final) ---
    # La app de autenticación (login/dashboard) va ÚLTIMA
    # porque su ruta '' atrapará todo lo demás.
    path('', include('autenticacion.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)