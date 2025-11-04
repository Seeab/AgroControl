from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.core.exceptions import ValidationError
import os
import re 

class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'roles'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.nombre


class Usuario(models.Model):
    nombre_usuario = models.CharField(max_length=150, unique=True)
    correo_electronico = models.EmailField(max_length=254, blank=True, null=True)
    contraseña = models.CharField(max_length=128)
    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150)
    rol = models.ForeignKey(Rol, on_delete=models.SET_NULL, null=True, related_name='usuarios')
    esta_activo = models.BooleanField(default=True)
    es_administrador = models.BooleanField(default=False)
    ultimo_acceso = models.DateTimeField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

    def set_password(self, raw_password):
        """Encripta y guarda la contraseña"""
        self.contraseña = make_password(raw_password)

    def check_password(self, raw_password):
        """Verifica si la contraseña es correcta"""
        return check_password(raw_password, self.contraseña)

    def get_full_name(self):
        """Retorna el nombre completo del usuario"""
        return f"{self.nombres} {self.apellidos}"

    def actualizar_ultimo_acceso(self):
        """Actualiza la fecha del último acceso"""
        self.ultimo_acceso = timezone.now()
        self.save(update_fields=['ultimo_acceso'])


def validar_rut_chileno(value):
    """Valida que el RUT chileno tenga formato correcto"""
    # Patrón para RUT: 7-8 dígitos + guión + dígito verificador (k/K o número)
    rut_pattern = re.compile(r'^(\d{7,8})-([\dkK])$')
    
    if not rut_pattern.match(value):
        raise ValidationError('El RUT debe tener formato: 12345678-9')
    
    # Validar dígito verificador
    rut, dv = value.split('-')
    dv = dv.upper()
    
    # Algoritmo de validación de RUT chileno
    suma = 0
    multiplo = 2
    
    # Recorrer el RUT de derecha a izquierda
    for r in reversed(rut):
        suma += int(r) * multiplo
        multiplo += 1
        if multiplo == 8:
            multiplo = 2
    
    resto = suma % 11
    dv_calculado = 11 - resto
    
    if dv_calculado == 11:
        dv_calculado = '0'
    elif dv_calculado == 10:
        dv_calculado = 'K'
    else:
        dv_calculado = str(dv_calculado)
    
    if dv != dv_calculado:
        raise ValidationError('El RUT no es válido. Dígito verificador incorrecto.')

def validate_file_size(value):
    """Valida que el archivo no exceda 5MB"""
    filesize = value.size
    if filesize > 5 * 1024 * 1024:
        raise ValidationError("El tamaño máximo del archivo es 5MB")

def validate_file_extension(value):
    """Valida las extensiones de archivo permitidas"""
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Tipo de archivo no permitido. Use PDF, JPG, PNG o GIF.')

class Operario(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='operario', null=True, blank=True)
    nombre_completo = models.CharField(max_length=200)
    cargo = models.CharField(max_length=100)
    
    # ✅ CAMBIADO: carnet -> rut
    rut = models.CharField(
        max_length=50, 
        unique=True,
        validators=[validar_rut_chileno],
        help_text="Formato: 12345678-9",
        error_messages={
            'unique': 'Ya existe un operario con este RUT registrado.'  # ✅ MENSAJE PERSONALIZADO
        }
    )
    
    telefono = models.CharField(max_length=20, blank=True, null=True)
    
    # Campos para certificaciones
    certificacion_documento = models.FileField(
        upload_to='certificaciones/operarios/',
        blank=True,
        null=True,
        validators=[validate_file_size, validate_file_extension],
        help_text="Subir documento de certificación (PDF, JPG, PNG, GIF). Tamaño máximo: 5MB"
    )
    fecha_emision_certificacion = models.DateField(blank=True, null=True)
    fecha_vencimiento_certificacion = models.DateField(blank=True, null=True)
    
    esta_activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'operarios'
        verbose_name = 'Operario'
        verbose_name_plural = 'Operarios'

    def __str__(self):
        return self.nombre_completo

    def carnet_por_vencer(self, dias=30):
        """Verifica si el carnet está próximo a vencer (RF008)"""
        if self.fecha_vencimiento_certificacion:
            from datetime import timedelta
            dias_restantes = (self.fecha_vencimiento_certificacion - timezone.now().date()).days
            return 0 <= dias_restantes <= dias
        return False

    def certificacion_vencida(self):
        """Verifica si la certificación está vencida"""
        if self.fecha_vencimiento_certificacion:
            return self.fecha_vencimiento_certificacion < timezone.now().date()
        return False

    # ✅ ACTUALIZADO: Método para RUT formateado
    def get_rut_formateado(self):
        """Retorna el RUT formateado para mostrar"""
        return self.rut.upper()