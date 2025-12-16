from django.urls import path
from . import views

urlpatterns = [
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password/recuperar/', views.recuperar_password, name='recuperar_password'),
    path('password/reset/<str:token>/', views.reset_password, name='reset_password'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Gestión de Usuarios
    path('usuarios/', views.usuario_lista, name='usuario_lista'),
    path('usuarios/crear/', views.usuario_crear, name='usuario_crear'),
    path('usuarios/<int:pk>/editar/', views.usuario_editar, name='usuario_editar'),
    path('usuarios/<int:pk>/eliminar/', views.usuario_eliminar, name='usuario_eliminar'),
    
    # Gestión de Operarios
    path('operarios/', views.operario_lista, name='operario_lista'),
    path('operarios/crear/', views.operario_crear, name='operario_crear'),
    path('operarios/<int:pk>/editar/', views.operario_editar, name='operario_editar'),
    path('operarios/<int:pk>/eliminar/', views.operario_eliminar, name='operario_eliminar'),
    path('perfil/', views.perfil_usuario, name='perfil_usuario'),
    path('perfil/editar', views.editar_perfil, name='editar_perfil'),
    path('acceso-denegado/', views.acceso_denegado, name='acceso_denegado'),
    
    
   
]