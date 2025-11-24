from django import forms
from .models import ControlRiego, FertilizanteRiego
from cuarteles.models import Cuartel
from autenticacion.models import Usuario
from inventario.models import Producto

# ---------------------------------------------------------------
# Formulario Principal (ControlRiego)
# ---------------------------------------------------------------
class ControlRiegoForm(forms.ModelForm):
    """Formulario para ControlRiego con ForeignKey"""
    
    # Inicializamos el campo vacío, se llena en __init__
    encargado_riego = forms.ModelChoiceField(
        queryset=Usuario.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = ControlRiego
        fields = [
            'cuartel',
            'estado', 
            'fecha',
            'horario_inicio',
            'horario_fin', 
            'caudal_m3h',
            'incluye_fertilizante',
            'encargado_riego',
            'observaciones'
        ]
        widgets = {
            'cuartel': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'horario_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horario_fin': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'caudal_m3h': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'incluye_fertilizante': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        # Extraemos el usuario
        self.usuario_actual = kwargs.pop('usuario_actual', None)
        super().__init__(*args, **kwargs)
        
        # 1. Configurar cuarteles
        self.fields['cuartel'].queryset = Cuartel.objects.all().order_by('nombre')
        self.fields['cuartel'].empty_label = "Seleccione un cuartel"
        self.fields['cuartel'].label_from_instance = lambda obj: f"{obj.nombre} (Cuartel {obj.numero})"
        
        # ==========================================================
        # --- 2. LÓGICA DE FILTRADO DE REGADORES (RF014) ---
        # ==========================================================
        if self.usuario_actual:
            # Si es Admin: Ve a TODOS los regadores activos
            if self.usuario_actual.es_administrador:
                self.fields['encargado_riego'].queryset = Usuario.objects.filter(
                    esta_activo=True,
                    rol__nombre='regador'
                ).order_by('nombres')
            
            # Si es Regador: Solo se ve a sí mismo
            else:
                self.fields['encargado_riego'].queryset = Usuario.objects.filter(
                    pk=self.usuario_actual.pk
                )
                # Preseleccionar
                self.fields['encargado_riego'].initial = self.usuario_actual
        else:
             self.fields['encargado_riego'].queryset = Usuario.objects.none()

        self.fields['encargado_riego'].empty_label = "Seleccione un encargado"
        
        # 3. Mostrar nombre completo del usuario
        if hasattr(Usuario, 'get_full_name') and callable(getattr(Usuario, 'get_full_name')):
             self.fields['encargado_riego'].label_from_instance = lambda obj: obj.get_full_name()
        elif hasattr(Usuario, 'nombres'):
             self.fields['encargado_riego'].label_from_instance = lambda obj: f"{obj.nombres} {obj.apellidos}"


# ---------------------------------------------------------------
# Formulario Secundario (FertilizanteRiego)
# ---------------------------------------------------------------
class FertilizanteRiegoForm(forms.ModelForm):
    """Formulario simple para un solo fertilizante"""
    class Meta:
        model = FertilizanteRiego
        fields = ['producto', 'cantidad_kg']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'cantidad_kg': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['producto'].queryset = Producto.objects.filter(
            tipo='fertilizante',
            esta_activo=True
        ).order_by('nombre')
        self.fields['producto'].empty_label = "Seleccione fertilizante"

# ---------------------------------------------------------------
# FormSet
# ---------------------------------------------------------------
FertilizanteRiegoFormSet = forms.inlineformset_factory(
    ControlRiego, 
    FertilizanteRiego,
    form=FertilizanteRiegoForm,
    extra=1, 
    can_delete=True,
    fk_name='control_riego'
)