from django import forms
from .models import Usuario, Operario, Rol
import re

class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}),
        label='Contraseña',
        required=False
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar contraseña'}),
        label='Confirmar contraseña',
        required=False
    )

    class Meta:
        model = Usuario
        fields = ['nombre_usuario', 'correo_electronico', 'nombres', 'apellidos', 
                  'rol', 'esta_activo', 'es_administrador']
        widgets = {
            'nombre_usuario': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
            'correo_electronico': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),
            'esta_activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_administrador': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.is_new = kwargs.pop('is_new', True)
        super().__init__(*args, **kwargs)
        
        if self.is_new:
            self.fields['password'].required = True
            self.fields['password_confirm'].required = True
        else:
            self.fields['password'].help_text = 'Dejar en blanco si no desea cambiar la contraseña'

    def clean_nombre_usuario(self):
        nombre_usuario = self.cleaned_data.get('nombre_usuario')
        if self.instance.pk:
            if Usuario.objects.exclude(pk=self.instance.pk).filter(nombre_usuario=nombre_usuario).exists():
                raise forms.ValidationError('Este nombre de usuario ya está en uso.')
        else:
            if Usuario.objects.filter(nombre_usuario=nombre_usuario).exists():
                raise forms.ValidationError('Este nombre de usuario ya está en uso.')
        return nombre_usuario

    # --- NUEVA VALIDACIÓN DE CORREO ---
    def clean_correo_electronico(self):
        correo = self.cleaned_data.get('correo_electronico')
        if correo:
            # Validamos sin importar mayúsculas/minúsculas con __iexact
            qs = Usuario.objects.filter(correo_electronico__iexact=correo)
            
            if self.instance.pk:
                # Si estamos editando, nos excluimos a nosotros mismos
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise forms.ValidationError('Este correo electrónico ya está registrado por otro usuario.')
        return correo
    # -----------------------------------

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password: 
            if password != password_confirm:
                raise forms.ValidationError('Las contraseñas no coinciden.')
            
            if len(password) < 8:
                raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')
            
            if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
                raise forms.ValidationError('La contraseña debe ser alfanumérica (contener letras y números).')

        return cleaned_data

    def save(self, commit=True):
        usuario = super().save(commit=False)
        password = self.cleaned_data.get('password')
        
        if password:
            usuario.set_password(password)
        
        if commit:
            usuario.save()
        return usuario


class OperarioForm(forms.ModelForm):
    clear_certificacion = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Eliminar documento actual'
    )

    class Meta:
        model = Operario
        fields = [
            'nombre_completo', 'cargo', 'rut', 'telefono',
            'fecha_emision_certificacion', 'fecha_vencimiento_certificacion',
            'certificacion_documento', 'esta_activo'
        ]
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre completo'}),
            'cargo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cargo'}),
            'rut': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '12345678-9',
                'pattern': '[0-9]{7,8}-[0-9kK]',
                'title': 'Formato: 12345678-9'
            }),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+56 9 1234 5678'}),
            'fecha_emision_certificacion': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'},
                format='%Y-%m-%d'
            ),
            'fecha_vencimiento_certificacion': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'},
                format='%Y-%m-%d'
            ),
            'certificacion_documento': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png,.gif'
            }),
            'esta_activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['certificacion_documento'].required = False

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        
        if rut:
            rut_limpio = re.sub(r'[^\dkK-]', '', rut.upper())
            
            if not re.match(r'^\d{7,8}-[\dkK]$', rut_limpio):
                raise forms.ValidationError('El RUT debe tener formato: 12345678-9')
            
            return rut_limpio
        
        return rut

    def clean(self):
        cleaned_data = super().clean()
        fecha_emision = cleaned_data.get('fecha_emision_certificacion')
        fecha_vencimiento = cleaned_data.get('fecha_vencimiento_certificacion')

        if fecha_emision and fecha_vencimiento:
            if fecha_vencimiento <= fecha_emision:
                raise forms.ValidationError('La fecha de vencimiento de la certificación debe ser posterior a la fecha de emisión.')

        return cleaned_data

    def save(self, commit=True):
        operario = super().save(commit=False)
        
        if self.cleaned_data.get('clear_certificacion'):
            if operario.certificacion_documento:
                operario.certificacion_documento.delete(save=False)
            operario.certificacion_documento = None
        
        if commit:
            operario.save()
        
        return operario

class LoginForm(forms.Form):
    correo_electronico = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com',
            'autofocus': True
        }),
        label='Correo Electrónico',
        error_messages={
            'invalid': 'Por favor ingresa un correo electrónico válido'
        }
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña'
        }),
        label='Contraseña'
    )

    def clean(self):
        cleaned_data = super().clean()
        correo_electronico = cleaned_data.get('correo_electronico')
        password = cleaned_data.get('password')

        if correo_electronico and password:
            try:
                # Nota: Si aún tienes duplicados en la BD, esto lanzará error.
                # Debes limpiar los usuarios duplicados en el admin o por base de datos.
                usuario = Usuario.objects.get(correo_electronico=correo_electronico)
                
                if not usuario.check_password(password):
                    raise forms.ValidationError('Credenciales incorrectas.')
                if not usuario.esta_activo:
                    raise forms.ValidationError('Esta cuenta ha sido desactivada.')
                cleaned_data['usuario'] = usuario
                
            except Usuario.DoesNotExist:
                raise forms.ValidationError('Credenciales incorrectas.')
            except Usuario.MultipleObjectsReturned:
                # Esto captura el error si ya hay duplicados previos y muestra un mensaje más amigable
                raise forms.ValidationError('Error de sistema: Existen múltiples cuentas con este correo. Contacte al administrador.')

        return cleaned_data


class RecuperarPasswordForm(forms.Form):
    correo_electronico = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com',
            'autofocus': True
        }),
        label='Correo Electrónico'
    )

    def clean_correo_electronico(self):
        correo = self.cleaned_data.get('correo_electronico')
        try:
            Usuario.objects.get(correo_electronico=correo, esta_activo=True)
        except Usuario.DoesNotExist:
            raise forms.ValidationError('No existe una cuenta activa con este correo.')
        except Usuario.MultipleObjectsReturned:
             raise forms.ValidationError('Existen múltiples cuentas con este correo. Contacte soporte.')
        return correo


class CambiarPasswordForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Nueva Contraseña',
        min_length=8 
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Confirmar Contraseña'
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Las contraseñas no coinciden.')

        if password:
            if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
                raise forms.ValidationError('La contraseña debe ser alfanumérica (contener letras y números).')

        return cleaned_data
    
class PerfilForm(forms.ModelForm):
    """
    Formulario igual a UsuarioForm pero para auto-edición.
    Incluye cambio de contraseña pero EXCLUYE roles y permisos.
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nueva Contraseña'}),
        label='Nueva Contraseña',
        required=False,
        help_text='Dejar en blanco si no desea cambiar la contraseña'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar nueva contraseña'}),
        label='Confirmar nueva contraseña',
        required=False
    )

    class Meta:
        model = Usuario
        # Excluimos 'rol', 'esta_activo', 'es_administrador'
        fields = ['nombre_usuario', 'correo_electronico', 'nombres', 'apellidos']
        widgets = {
            'nombre_usuario': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}), # Solo lectura
            'correo_electronico': forms.EmailInput(attrs={'class': 'form-control'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
        }

    # --- NUEVA VALIDACIÓN DE CORREO TAMBIÉN EN PERFIL ---
    def clean_correo_electronico(self):
        correo = self.cleaned_data.get('correo_electronico')
        if correo:
            qs = Usuario.objects.filter(correo_electronico__iexact=correo)
            
            # Como PerfilForm siempre es edición, self.instance siempre existe
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise forms.ValidationError('Este correo electrónico ya está asociado a otra cuenta.')
        return correo
    # ---------------------------------------------------

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password: 
            if password != password_confirm:
                raise forms.ValidationError('Las contraseñas no coinciden.')
            
            if len(password) < 8:
                raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')
            
            if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
                raise forms.ValidationError('La contraseña debe ser alfanumérica.')

        return cleaned_data

    def save(self, commit=True):
        usuario = super().save(commit=False)
        password = self.cleaned_data.get('password')
        
        if password:
            usuario.set_password(password)
        
        if commit:
            usuario.save()
        return usuario