from django.urls import path
from . import views

app_name = 'cuarteles'

urlpatterns = [
    path('', views.lista_cuarteles, name='lista_cuarteles'),
    path('dashboard/', views.dashboard_cuarteles, name='dashboard_cuarteles'),
    path('crear/', views.crear_cuartel, name='crear_cuartel'),
    path('<int:cuartel_id>/', views.detalle_cuartel, name='detalle_cuartel'),
    path('<int:cuartel_id>/editar/', views.editar_cuartel, name='editar_cuartel'),
    path('<int:cuartel_id>/eliminar/', views.eliminar_cuartel, name='eliminar_cuartel'),
    path('api/estadisticas/', views.api_estadisticas_cuarteles, name='api_estadisticas'),
]