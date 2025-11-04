# Guardar en: autenticacion/management/commands/crear_usuario_admin.py

from django.core.management.base import BaseCommand
from autenticacion.models import Usuario, Rol

class Command(BaseCommand):
    help = 'Crea un usuario administrador por defecto'

    def handle(self, *args, **kwargs):
        # Verificar si ya existe un admin
        if Usuario.objects.filter(nombre_usuario='admin').exists():
            self.stdout.write(self.style.WARNING('El usuario admin ya existe'))
            return

        # Crear o obtener el rol de administrador
        rol_admin, created = Rol.objects.get_or_create(
            nombre='administrador',
            defaults={'descripcion': 'Acceso completo al sistema'}
        )

        # Crear usuario administrador
        admin = Usuario.objects.create(
            nombre_usuario='admin',
            correo_electronico='admin@agrocontrol.com',
            nombres='Administrador',
            apellidos='Del Sistema',
            rol=rol_admin,
            esta_activo=True,
            es_administrador=True
        )
        admin.set_password('admin123')  # Contraseña por defecto
        admin.save()

        self.stdout.write(
            self.style.SUCCESS(
                'Usuario administrador creado exitosamente!\n'
                'Usuario: admin\n'
                'Contraseña: admin123\n'
                '⚠️ Recuerda cambiar la contraseña después del primer inicio de sesión'
            )
        )