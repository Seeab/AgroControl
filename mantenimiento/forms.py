from django import forms
from .models import Mantenimiento
from inventario.models import EquipoAgricola
from autenticacion.models import Usuario

# ---------------------------------------------------------------
# Formulario Principal (Mantenimiento)
# ---------------------------------------------------------------

class MantenimientoForm(forms.ModelForm):
    """
    Formulario principal para crear y editar Mantenimientos.
    """

    class Meta:
        model = Mantenimiento
        fields = [
            # El campo "tipo_equipo" ya no es necesario
            'maquinaria',
            'tipo_mantenimiento',
            'fecha_mantenimiento',
            'operario_responsable',
            'descripcion_trabajo',
        ]
        widgets = {
            'maquinaria': forms.Select(attrs={'class': 'form-select'}),
            'tipo_mantenimiento': forms.Select(attrs={'class': 'form-select'}),
            'fecha_mantenimiento': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'operario_responsable': forms.Select(attrs={'class': 'form-select'}),
            'descripcion_trabajo': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'maquinaria': 'Maquinaria o Equipo',
            'tipo_mantenimiento': 'Tipo de Tarea',
            'fecha_mantenimiento': 'Fecha y Hora Programada',
            'operario_responsable': 'Responsable Asignado',
            'descripcion_trabajo': 'Descripción del Trabajo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ==========================================================
        # --- INICIO DE LA LÓGICA DE <optgroup> ---
        # ==========================================================
        
        # 1. Obtenemos los equipos que podemos seleccionar
        # (Todos los 'operativos')
        equipos_operativos = EquipoAgricola.objects.filter(estado='operativo')

        # 2. Si estamos editando (self.instance.pk existe), 
        #    debemos añadir el equipo actual a la lista, aunque esté 'en_mantenimiento'.
        #    De lo contrario, no aparecería seleccionado.
        if self.instance and self.instance.pk:
            equipos_actuales = EquipoAgricola.objects.filter(pk=self.instance.maquinaria.pk)
            # Usamos '|' (OR) para combinar ambos querysets
            equipos_para_mostrar = (equipos_operativos | equipos_actuales).distinct().order_by('nombre')
        else:
            # Si estamos creando, solo mostramos los operativos
            equipos_para_mostrar = equipos_operativos.order_by('nombre')
        
        # 3. Creamos la lista de opciones agrupadas
        grouped_choices = []
        
        # Iteramos sobre las categorías DEFINIDAS en el modelo EquipoAgricola
        for tipo_key, tipo_display in EquipoAgricola.TIPO_EQUIPO_CHOICES:
            
            # Filtramos los equipos que pertenecen a esta categoría
            equipos_en_grupo = equipos_para_mostrar.filter(tipo=tipo_key)
            
            if equipos_en_grupo.exists():
                # Creamos la sub-lista de opciones para este grupo
                lista_opciones = [
                    (equipo.id, equipo.nombre) for equipo in equipos_en_grupo
                ]
                # Añadimos el grupo (("Maquinaria Pesada", [(1, "Tractor"), ...]))
                grouped_choices.append((tipo_display, lista_opciones))

        # 4. Asignamos las opciones agrupadas al campo 'maquinaria'
        self.fields['maquinaria'].choices = [('', 'Seleccione un equipo')] + grouped_choices

        # ==========================================================
        # --- FIN DE LA LÓGICA DE <optgroup> ---
        # ==========================================================
        

        # --- Lógica de Operario Responsable (Sin cambios) ---
        try:
            self.fields['operario_responsable'].queryset = Usuario.objects.filter(
                esta_activo=True,
                rol__nombre__in=['encargado de mantencion'] 
            ).order_by('nombres')
        except Exception:
            self.fields['operario_responsable'].queryset = Usuario.objects.filter(
                esta_activo=True
            ).order_by('nombres')

        self.fields['operario_responsable'].empty_label = "Seleccione un responsable"

        if hasattr(Usuario, 'get_full_name') and callable(getattr(Usuario, 'get_full_name')):
             self.fields['operario_responsable'].label_from_instance = lambda obj: obj.get_full_name()
        elif hasattr(Usuario, 'nombres'):
             self.fields['operario_responsable'].label_from_instance = lambda obj: f"{obj.nombres} {obj.apellidos}"