from django import forms
from .models import AplicacionFitosanitaria
from cuarteles.models import Cuartel
from inventario.models import Producto, EquipoAgricola # <-- 1. IMPORTACIÓN AÑADIDA
from django.contrib.auth.models import User

class AplicacionForm(forms.ModelForm):
    
    # --- Campos personalizados ---
    aplicador = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=True).order_by('username'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(esta_activo=True).order_by('nombre'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    cuarteles = forms.ModelMultipleChoiceField(
        queryset=Cuartel.objects.all().order_by('nombre'), 
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': '5'})
    )
    fecha_aplicacion = forms.DateTimeField(
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={'class': 'form-control', 'type': 'datetime-local'}
        ),
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S']
    )

    # --- ✨ NUEVO CAMPO AÑADIDO (CON FILTRO) ---
    equipo_utilizado = forms.ModelChoiceField(
        queryset=EquipoAgricola.objects.filter(estado='operativo').order_by('nombre'),
        required=False, # <-- Muy importante: hacerlo opcional
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Equipo Utilizado (Opcional)'
    )
    # --- FIN DEL NUEVO CAMPO ---

    class Meta:
        model = AplicacionFitosanitaria
        # AHORA PEDIMOS 'cantidad_utilizada' Y SACAMOS 'dosis_por_hectarea'
        fields = [
            'aplicador', 'fecha_aplicacion', 'producto', 'cantidad_utilizada',
            'cuarteles', 'objetivo', 'metodo_aplicacion', 'estado',
            'equipo_utilizado' # <-- 3. AÑADIDO A LA LISTA
        ]
        widgets = {
            # Este es el NUEVO campo de entrada
            'cantidad_utilizada': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}
            ),
            'objetivo': forms.TextInput(attrs={'class': 'form-control'}),
            'metodo_aplicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            # No es necesario añadir 'equipo_utilizado' aquí, ya lo definimos arriba.
        }

    def clean(self):
        """
        Validación central (RF020) y cálculos (LÓGICA INVERTIDA)
        """
        cleaned_data = super().clean()
        
        producto = cleaned_data.get('producto')
        cantidad_utilizada = cleaned_data.get('cantidad_utilizada') # <-- Dato de entrada
        cuarteles = cleaned_data.get('cuarteles')

        if producto and cantidad_utilizada and cuarteles:
            
            # 1. Validar stock (RF020) - AHORA ES MÁS FÁCIL
            if cantidad_utilizada > producto.stock_actual:
                raise forms.ValidationError({
                    'cantidad_utilizada': ( # Error en el campo nuevo
                        f"No hay suficiente stock. Requerido: {cantidad_utilizada} {producto.unidad_medida}, "
                        f"Disponible: {producto.stock_actual} {producto.unidad_medida}."
                    )
                })

            # 2. Calcular área total
            try:
                area_total = sum(c.area_hectareas for c in cuarteles if c.area_hectareas)
                if area_total <= 0:
                        raise forms.ValidationError(
                            "El área total de los cuarteles seleccionados debe ser mayor a 0."
                        )
                cleaned_data['area_tratada'] = area_total
            except Exception as e:
                raise forms.ValidationError(f"Error al calcular el área: {e}")

            # 3. Calcular Dosis/Ha (el campo calculado)
            if area_total > 0:
                dosis_calculada = cantidad_utilizada / area_total
                cleaned_data['dosis_por_hectarea'] = dosis_calculada
            else:
                cleaned_data['dosis_por_hectarea'] = 0

        return cleaned_data