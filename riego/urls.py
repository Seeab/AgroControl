# riego/urls.py (CORREGIDO)
from django.urls import path
from . import views

app_name = 'riego'

urlpatterns = [
    # Vistas principales
    path('', views.dashboard_riego, name='dashboard'),
    
    # <-- CORRECCIÓN: Nombres simplificados
    path('crear/', views.crear_riego, name='crear_riego'),
    path('editar/<int:pk>/', views.editar_riego, name='editar_riego'),
    
    # <-- CORRECCIÓN: 'riego_detalle' -> 'detalle_riego'
    # Esta es la línea que causaba tu error
    path('<int:pk>/', views.detalle_riego, name='detalle_riego'),

    # Acciones
    path('<int:pk>/cancelar/', views.cancelar_riego, name='cancelar_riego'), 
    path('<int:pk>/finalizar/', views.finalizar_riego, name='finalizar_riego'),
]