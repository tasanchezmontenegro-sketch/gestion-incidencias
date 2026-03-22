from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Area, Estado, Incidencia, Comentario, Notificacion

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # 'area' y 'foto' ahora funcionarán porque los agregamos al modelo arriba
    list_display = ('username', 'email', 'first_name', 'last_name', 'telefono', 'role', 'area', 'is_staff')
    
    fieldsets = UserAdmin.fieldsets + (
        ('UGEL Info', {
            'fields': ('role', 'telefono', 'area', 'foto', 'last_password_change')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('UGEL Info', {
            'fields': ('role', 'telefono', 'area')
        }),
    )

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Estado)
class EstadoAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    # 'creador' es el campo correcto según tu views.py
    list_display = ('id', 'creador', 'area', 'prioridad', 'estado', 'fecha_creacion')
    list_filter = ('prioridad', 'estado', 'categoria')
    search_fields = ('descripcion', 'creador__username') # Permite buscar por nombre de usuario

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('incidencia', 'usuario', 'tipo_comentario', 'fecha_creacion')

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('usuario_destino', 'tipo', 'mensaje', 'leido', 'fecha_creacion')
    list_filter = ('leido', 'tipo')
    actions = ['marcar_como_leidas']

    def marcar_como_leidas(self, request, queryset):
        queryset.update(leido=True)
    marcar_como_leidas.short_description = "Marcar seleccionadas como leídas"