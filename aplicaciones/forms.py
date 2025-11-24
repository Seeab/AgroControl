from django import forms
from django.forms import inlineformset_factory
from .models import AplicacionFitosanitaria, AplicacionProducto
from cuarteles.models import Cuartel
from inventario.models import Producto, EquipoAgricola
from autenticacion.models import Usuario 

class AplicacionForm(forms.ModelForm):
    
    # --- Campos personalizados ---
    # Inicialmente definimos el queryset vacío o general,
    # pero lo filtraremos dinámicamente en el __init__
    aplicador = forms.ModelChoiceField(
        queryset=Usuario.objects.none(), # Se llena en __init__
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

    equipo_utilizado = forms.ModelChoiceField(
        queryset=EquipoAgricola.objects.filter(estado='operativo').order_by('nombre'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Equipo Utilizado (Opcional)'
    )

    class Meta:
        model = AplicacionFitosanitaria
        fields = [
            'aplicador', 'fecha_aplicacion', 'cuarteles', 
            'objetivo', 'metodo_aplicacion', 'estado',
            'equipo_utilizado'
        ]
        widgets = {
            'objetivo': forms.TextInput(attrs={'class': 'form-control'}),
            'metodo_aplicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        # Extraemos el usuario que pasaremos desde la vista
        self.usuario_actual = kwargs.pop('usuario_actual', None)
        super().__init__(*args, **kwargs)
        
        # ==========================================================
        # --- LÓGICA DE FILTRADO DE APLICADORES (RF018) ---
        # ==========================================================
        if self.usuario_actual:
            # 1. Si es Administrador: Ve a TODOS los aplicadores activos
            if self.usuario_actual.es_administrador:
                self.fields['aplicador'].queryset = Usuario.objects.filter(
                    esta_activo=True, 
                    rol__nombre='aplicador' 
                ).order_by('nombres')
            
            # 2. Si es un Aplicador normal: Solo se ve a sí mismo
            else:
                self.fields['aplicador'].queryset = Usuario.objects.filter(
                    pk=self.usuario_actual.pk
                )
                # Y lo preseleccionamos automáticamente
                self.fields['aplicador'].initial = self.usuario_actual
                # Opcional: Hacer el campo de solo lectura o deshabilitado visualmente
                # self.fields['aplicador'].widget.attrs['readonly'] = True 
        else:
            # Fallback por si algo falla (no debería pasar)
            self.fields['aplicador'].queryset = Usuario.objects.none()

    def clean(self):
        """
        Validación central y cálculos de área.
        """
        cleaned_data = super().clean()
        
        cuarteles = cleaned_data.get('cuarteles')

        if cuarteles:
            try:
                area_total = sum(c.area_hectareas for c in cuarteles if c.area_hectareas)
                if area_total <= 0:
                        raise forms.ValidationError(
                            "El área total de los cuarteles seleccionados debe ser mayor a 0."
                        )
                cleaned_data['area_tratada'] = area_total 
            except Exception as e:
                raise forms.ValidationError(f"Error al calcular el área: {e}")
        else:
             cleaned_data['area_tratada'] = 0

        return cleaned_data

# --- El resto del archivo (AplicacionProductoForm y FormSet) sigue igual ---
class AplicacionProductoForm(forms.ModelForm):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(esta_activo=True).order_by('nombre'),
        widget=forms.Select(attrs={'class': 'form-control producto-select'})
    )
    
    cantidad_utilizada = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'})
    )

    class Meta:
        model = AplicacionProducto
        fields = ['producto', 'cantidad_utilizada']

    def clean(self):
        cleaned_data = super().clean()
        producto = cleaned_data.get('producto')
        cantidad_utilizada = cleaned_data.get('cantidad_utilizada')
        
        if not cleaned_data.get('DELETE', False):
            if producto and cantidad_utilizada:
                if cantidad_utilizada > producto.stock_actual:
                    raise forms.ValidationError(
                        f"No hay stock de '{producto.nombre}'. "
                        f"Requerido: {cantidad_utilizada} {producto.unidad_medida}, "
                        f"Disponible: {producto.stock_actual} {producto.unidad_medida}."
                    )
            
            if not producto:
                raise forms.ValidationError("Debe seleccionar un producto.")
            
            if not cantidad_utilizada or cantidad_utilizada <= 0:
                raise forms.ValidationError("La cantidad debe ser mayor a 0.")

        return cleaned_data

AplicacionProductoFormSet = inlineformset_factory(
    AplicacionFitosanitaria,
    AplicacionProducto, 
    form=AplicacionProductoForm,
    extra=1,
    can_delete=True,
    fk_name='aplicacion',
    min_num=1,
    validate_min=True,
)