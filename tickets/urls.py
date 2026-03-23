from django.urls import path
from django.contrib.auth import views
from . import views

urlpatterns = [
    path("login/", views.custom_login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.index, name="index"),
    
    # Dashboards
    path("dashboard/", views.dashboard_admin, name="dashboard"),
    path("dashboard/tecnico/", views.dashboard_tecnico, name="dashboard_tecnico"),
    
    # Incidencias - Listados y Gestión
    path("incidencias/admin/", views.incidencias_admin, name="incidencias_admin"),
    path("incidencias/asignadas/", views.incidencias_asignadas, name="incidencias_asignadas"),
    path("incidencias/mis-incidencias/", views.mis_incidencias, name="mis_incidencias"),
    path("incidencias/crear/", views.crear_incidencia, name="crear_incidencia"),
    path("incidencias/<int:pk>/", views.detalle_incidencia, name="detalle_incidencia"),
    path('incidencia/<int:pk>/gestionar/', views.gestionar_incidencia, name='gestionar_incidencia'),
    
    # Acciones de Incidencia
    path("incidencias/<int:pk>/resolver/", views.resolver_incidencia, name="resolver_incidencia"),
    path("incidencias/<int:pk>/cerrar/", views.cerrar_incidencia_view, name="cerrar_incidencia"),
    path("incidencias/<int:pk>/reabrir/", views.reabrir_incidencia_view, name="reabrir_incidencia"),

    # Usuarios
    path("usuarios/", views.usuarios, name="usuarios"),
    path("mi-perfil/", views.mi_perfil, name="mi_perfil"),
    path("usuarios/crear/", views.crear_usuario, name="crear_usuario"),
    path("usuarios/<int:pk>/editar/", views.editar_usuario, name="editar_usuario"),
    path("usuarios/<int:pk>/toggle-status/", views.toggle_usuario_status, name="toggle_usuario_status"),
    path("usuarios/<int:user_id>/reset-password/", views.reset_password_admin, name="reset_password_admin"),
    path('cambio-obligatorio/', views.password_change_forced, name='password_change_forced'),

    # Notificaciones (HTMX)
    path('notifications/unread_count/', views.get_unread_notifications_count, name='unread_count'),
    path('notificaciones/ir/<int:pk>/', views.ir_a_notificacion, name='ir_a_notificacion'),
    path('notificaciones/marcar-todas/', views.marcar_notificaciones_leidas, name='marcar_notificaciones_leidas'),

    # REPORTE 1: El general con estadísticas (Dashboard)
    path('incidencias/informe-general/pdf/', views.exportar_incidencias_pdf, name='reporte_incidencias_pdf'),

    # REPORTE 2: El de un solo ticket (Detalle)
    path('incidencia/<int:pk>/pdf/', views.reporte_detalle_ticket_pdf, name='ticket_detalle_pdf'),

    # REPORTE 3: El de la lista de asignadas (Técnico)
    path('incidencias/reporte-asignadas/pdf/', views.exportar_reporte_general_pdf, name='reporte_tecnico_pdf'),
]
