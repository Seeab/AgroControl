from django import forms
from .models import Mantenimiento
from inventario.models import EquipoAgricola
from autenticacion.models import Usuario

class MantenimientoForm(forms.ModelForm):
    """
    Formulario principal para crear y editar Mantenimientos.
    """

    # Inicializamos vacío, se llena en __init__
    operario_responsable = forms.ModelChoiceField(
        queryset=Usuario.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Mantenimiento
        fields = [
            'maquinaria',
            'cantidad', 
            'tipo_mantenimiento',
            'fecha_mantenimiento',
            'operario_responsable',
            'descripcion_trabajo',
        ]
        widgets = {
            'maquinaria': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'tipo_mantenimiento': forms.Select(attrs={'class': 'form-select'}),
            'fecha_mantenimiento': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'descripcion_trabajo': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'maquinaria': 'Maquinaria o Equipo',
            'cantidad': 'Cantidad a Mantener',
            'tipo_mantenimiento': 'Tipo de Tarea',
            'fecha_mantenimiento': 'Fecha y Hora Programada',
            'operario_responsable': 'Responsable Asignado',
            'descripcion_trabajo': 'Descripción del Trabajo',
        }

    def __init__(self, *args, **kwargs):
        # Extraemos el usuario actual
        self.usuario_actual = kwargs.pop('usuario_actual', None)
        super().__init__(*args, **kwargs)

        # --- 1. Lógica de Maquinaria (Optgroups) ---
        equipos_operativos = EquipoAgricola.objects.filter(estado='operativo')
        if self.instance and self.instance.pk:
            equipos_actuales = EquipoAgricola.objects.filter(pk=self.instance.maquinaria.pk)
            equipos_para_mostrar = (equipos_operativos | equipos_actuales).distinct().order_by('nombre')
        else:
            equipos_para_mostrar = equipos_operativos.order_by('nombre')
        
        grouped_choices = []
        for tipo_key, tipo_display in EquipoAgricola.TIPO_EQUIPO_CHOICES:
            equipos_en_grupo = equipos_para_mostrar.filter(tipo=tipo_key)
            if equipos_en_grupo.exists():
                lista_opciones = [
                    (equipo.id, f"{equipo.nombre} (Stock: {equipo.stock_actual})") for equipo in equipos_en_grupo
                ]
                grouped_choices.append((tipo_display, lista_opciones))

        self.fields['maquinaria'].choices = [('', 'Seleccione un equipo')] + grouped_choices

        # ==========================================================
        # --- 2. LÓGICA DE FILTRADO DE RESPONSABLES ---
        # ==========================================================
        if self.usuario_actual:
            # Si es Admin: Ve a TODOS los encargados de mantención activos
            if self.usuario_actual.es_administrador:
                try:
                    self.fields['operario_responsable'].queryset = Usuario.objects.filter(
                        esta_activo=True,
                        rol__nombre='encargado de mantencion' # Nombre exacto del rol
                    ).order_by('nombres')
                except Exception:
                    # Fallback si el rol no existe
                    self.fields['operario_responsable'].queryset = Usuario.objects.filter(esta_activo=True)
            
            # Si NO es Admin (es Encargado): Solo se ve a sí mismo
            else:
                self.fields['operario_responsable'].queryset = Usuario.objects.filter(
                    pk=self.usuario_actual.pk
                )
                # Preseleccionar automáticamente
                self.fields['operario_responsable'].initial = self.usuario_actual
        else:
             self.fields['operario_responsable'].queryset = Usuario.objects.none()

        self.fields['operario_responsable'].empty_label = "Seleccione un responsable"

        # Mostrar nombres completos
        if hasattr(Usuario, 'get_full_name') and callable(getattr(Usuario, 'get_full_name')):
             self.fields['operario_responsable'].label_from_instance = lambda obj: obj.get_full_name()
        elif hasattr(Usuario, 'nombres'):
             self.fields['operario_responsable'].label_from_instance = lambda obj: f"{obj.nombres} {obj.apellidos}"