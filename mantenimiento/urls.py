from django.urls import path
from . import views

# Este app_name es crucial para que {% url 'mantencion:...' %} funcione
app_name = 'mantenimiento'

urlpatterns = [
    # 1. Dashboard (Lista Principal)
    # URL: /mantencion/
    path('', views.dashboard_mantencion, name='dashboard'),

    # 2. Crear
    # URL: /mantencion/crear/
    path('crear/', views.crear_mantenimiento, name='mantenimiento_crear'),

    # 3. Detalle
    # URL: /mantencion/5/
    path('<int:pk>/', views.detalle_mantenimiento, name='mantenimiento_detalle'),

    # 4. Editar
    # URL: /mantencion/5/editar/
    path('<int:pk>/editar/', views.editar_mantenimiento, name='mantenimiento_editar'),

    # 5. Acciones (Botones de la tabla)
    # URL: /mantencion/5/finalizar/
    path('<int:pk>/finalizar/', views.finalizar_mantenimiento, name='mantenimiento_finalizar'),
    
    # URL: /mantencion/5/cancelar/
    path('<int:pk>/cancelar/', views.cancelar_mantenimiento, name='mantenimiento_cancelar'),

    
]