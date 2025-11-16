from django.urls import path
from . import views

app_name = 'riego'

urlpatterns = [
    # Vistas principales
    path('', views.dashboard_riego, name='dashboard'),
    path('crear/', views.crear_riego, name='riego_crear'),
    path('<int:pk>/', views.detalle_riego, name='riego_detalle'),
    path('editar/<int:pk>/', views.editar_riego, name='riego_editar'),

    path('<int:pk>/cancelar/', views.cancelar_riego, name='riego_cancelar'), 
    
    # 2. URL NUEVA (para el botón del "tick")
    path('<int:pk>/finalizar/', views.finalizar_riego, name='riego_finalizar'),
    
    
]