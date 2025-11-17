# mantenimiento/urls.py (CORREGIDO)
from django.urls import path
from . import views

app_name = 'mantenimiento'

urlpatterns = [
    # 1. Dashboard (Lista Principal)
    path('', views.dashboard_mantencion, name='dashboard'),

    # <-- CORRECCIÓN: Nombres simplificados
    # 2. Crear
    path('crear/', views.crear_mantenimiento, name='crear_mantenimiento'),

    # 4. Editar
    path('<int:pk>/editar/', views.editar_mantenimiento, name='editar_mantenimiento'),

    # <-- CORRECCIÓN: 'mantenimiento_detalle' -> 'detalle_mantenimiento'
    # Esta línea habría causado el siguiente error
    # 3. Detalle
    path('<int:pk>/', views.detalle_mantenimiento, name='detalle_mantenimiento'),

    # 5. Acciones (Botones de la tabla)
    path('<int:pk>/finalizar/', views.finalizar_mantenimiento, name='finalizar_mantenimiento'),
    path('<int:pk>/cancelar/', views.cancelar_mantenimiento, name='cancelar_mantenimiento'),
]