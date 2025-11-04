from django.urls import path
from . import views

app_name = 'aplicaciones'

urlpatterns = [
    path('', views.lista_aplicaciones, name='lista_aplicaciones'),
    path('crear/', views.crear_aplicacion, name='crear_aplicacion'),
    path('<int:aplicacion_id>/', views.detalle_aplicacion, name='detalle_aplicacion'),
    path('<int:app_id>/editar/', views.editar_aplicacion, name='editar_aplicacion'),
    path('<int:app_id>/finalizar/', views.finalizar_aplicacion, name='finalizar_aplicacion'),
    path('<int:app_id>/cancelar/', views.cancelar_aplicacion, name='cancelar_aplicacion'),
]
