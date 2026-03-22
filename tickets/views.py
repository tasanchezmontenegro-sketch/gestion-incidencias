import os, io
from datetime import datetime

# Django Core
from django.conf import settings
from django.contrib import messages
from django.contrib.staticfiles import finders
from django.urls import reverse
from django.utils import timezone
from django.http import HttpResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.template.loader import get_template, render_to_string

# Django Auth
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

# Django Database
from django.db.models import Count, Q

# PDF Generation
from weasyprint import HTML

# Apps Locales
from .models import Incidencia, CustomUser, Estado, Area, Comentario, Notificacion
from .forms import CustomUserChangeForm, IncidenciaForm, IncidenciaAdminForm
from .services import resolver_incidencia_service, cerrar_incidencia_service


User = get_user_model()
REGISTROS_POR_PAGINA = 10


# ── Helpers de rol ──────────────────────────────────────────
def is_admin(user):
    return user.is_authenticated and (user.is_staff or user.role == 'administrador')

def is_tecnico(user):
    return user.is_authenticated and user.role == 'tecnico'

def is_trabajador(user):
    return user.is_authenticated and user.role == 'usuario'

# ── Exportar PDF ─────────────────────────────────────────────
@login_required
def exportar_reporte_general_pdf(request):
    incidencias = Incidencia.objects.filter(
        tecnico_asignado=request.user
    ).order_by('-fecha_creacion')

    context = {
        'incidencias': incidencias,
        'fecha_reporte': timezone.now(),
        'usuario_reporte': request.user.get_full_name() or request.user.username,
    }

    html_string = render_to_string('tickets/pdf_reporte_general.html', context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Reporte_General_Soporte.pdf"'

    HTML(
        string=html_string,
        base_url=request.build_absolute_uri()
    ).write_pdf(response)

    return response

# Función auxiliar para resolver rutas de archivos (CSS, Imágenes)
def link_callback(uri, rel):
    """
    Convierte URIs de Django a rutas de archivos absolutas para xhtml2pdf.
    """
    # Resolver rutas de STATIC
    if uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT or settings.STATICFILES_DIRS[0], uri.replace(settings.STATIC_URL, ""))
    # Resolver rutas de MEDIA
    elif uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    else:
        return uri

    # Verificar si el archivo existe
    if not os.path.isfile(path):
        return uri
    return path

@login_required
def exportar_incidencias_pdf(request):
    # 1. Traemos todas las incidencias optimizadas
    incidencias = Incidencia.objects.select_related(
        'creador', 'tecnico_asignado', 'area', 'estado'
    ).all().order_by('-fecha_creacion')

    # 2. Preparamos el contexto con los nombres EXACTOS que pide tu template
    context = {
        'incidencias': incidencias,
        'fecha': timezone.now(),
        'usuario': request.user.get_full_name() or request.user.username,
        'titulo_reporte': "INFORME DE GESTIÓN DE INCIDENCIAS - UGEL MORROPÓN",
        'stats': {
            'total_incidencias': incidencias.count(),
            'total_resueltos': incidencias.filter(estado__name='Resuelto').count(),
            'total_cerrados': incidencias.filter(estado__name='Cerrado').count(),
            'total_criticas': incidencias.filter(prioridad='critica').count(),
        }
    }

    # 3. Renderizado a String
    html_string = render_to_string('tickets/pdf_template.html', context)
    
    # 4. Configuración de Respuesta para Descarga
    response = HttpResponse(content_type='application/pdf')
    filename = f"Reporte_General_{timezone.now().strftime('%d_%m_%Y')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # 5. Generación del PDF con WeasyPrint
    HTML(
        string=html_string, 
        base_url=request.build_absolute_uri('/') 
    ).write_pdf(response, url_fetcher=fetch_resources)

    return response

@login_required
def reporte_detalle_ticket_pdf(request, pk):
    incidencia = get_object_or_404(
        Incidencia.objects.select_related('creador', 'tecnico_asignado', 'area', 'estado'),
        pk=pk
    )

    context = {
        'i': incidencia,
        'fecha_reporte': timezone.now(),
        'usuario_reporte': request.user.get_full_name() or request.user.username,
    }

    html_string = render_to_string('tickets/pdf_ticket_detalle.html', context)
    response = HttpResponse(content_type='application/pdf')
    
    # CAMBIO AQUÍ: 'inline' abre el PDF en el navegador, 'attachment' lo descarga.
    filename = f"Ticket_{incidencia.id:04d}_Detalle.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    HTML(
        string=html_string, 
        base_url=request.build_absolute_uri('/') 
    ).write_pdf(response, url_fetcher=fetch_resources)

    return response

# ── Autenticación ────────────────────────────────────────────
def custom_login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('index')
        messages.error(request, 'Usuario o contraseña incorrectos.')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def index(request):
    if is_admin(request.user):
        return redirect('dashboard')
    elif is_tecnico(request.user):
        return redirect('dashboard_tecnico')
    return redirect('mis_incidencias')


# ── Dashboards ───────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def dashboard_admin(request):
    # 1. Definir los filtros de base (Q) y la fecha
    hoy = timezone.localdate()
    
    # 2. CALCULAR LAS VARIABLES PRIMERO
    # Críticas: Alta o Crítica y que NO estén resueltas
    count_criticas = Incidencia.objects.filter(
        Q(prioridad__icontains='alt') | Q(prioridad__icontains='crit')
    ).exclude(estado__name__icontains='resuelto').count()

    # Pendientes: Estado Pendiente o En Proceso
    count_pendientes = Incidencia.objects.filter(
        Q(estado__name__icontains='pendiente') | Q(estado__name__icontains='proceso')
    ).count()

    # Resueltas: Estado exacto 'Resuelto'
    count_resueltas = Incidencia.objects.filter(estado__name__iexact='Resuelto').count()

    # Cerradas (Para el KPI de 'Cerrados' en tu HTML)
    count_cerrados = Incidencia.objects.filter(estado__name__iexact='Cerrado').count()

    # Lista de hoy
    lista_hoy = Incidencia.objects.filter(fecha_creacion__date=hoy).order_by('-fecha_creacion')
    count_hoy = lista_hoy.count()

    # 3. PASAR LAS VARIABLES AL CONTEXTO
    return render(request, 'tickets/dashboard_admin.html', {
        'stats': {
            'total_criticas': count_criticas,
            'total_pendientes': count_pendientes,
            'total_resueltos': count_resueltas,
            'total_cerrados': count_cerrados, # Agregamos esta para que no salga 0
            'total_hoy': count_hoy,
        },
        'incidencias_resueltas': count_resueltas,
        'incidencias_hoy': count_hoy,
        'incidencias_hoy_lista': lista_hoy, # Nombre que espera tu HTML
        'incidencias_por_estado': list(Incidencia.objects.values('estado__name').annotate(count=Count('id'))),
        'incidencias_por_area': list(Incidencia.objects.values('area__name').annotate(count=Count('id'))),
    })

@login_required
@user_passes_test(is_tecnico)
def dashboard_tecnico(request):
    # 1. Base de datos: Filtramos por el técnico logueado
    # Importante: Asegúrate de que el campo en tu modelo sea 'tecnico_asignado' 
    # o 'tecnico'. Según tu código previo es 'tecnico_asignado'.
    tickets_base = Incidencia.objects.filter(tecnico_asignado=request.user)
    
    hoy = timezone.localdate()
    
    # 2. Optimizamos la consulta para la tabla con select_related
    # Traemos las del día de hoy para el contador de la cabecera de la tabla
    ultimas_incidencias = tickets_base.filter(
        fecha_creacion__date=hoy
    ).select_related('area', 'estado').order_by('-fecha_creacion')

    # 3. Definimos los estados que consideramos "Finalizados"
    # Usamos una lista para mantener la consistencia en todos los contadores
    estados_finalizados = ['Resuelto', 'Cerrado', 'CERRADO']

    return render(request, 'tickets/dashboard_tecnico.html', {
        # Total histórico asignado a este técnico
        'assigned_tickets': tickets_base.count(),
        
        # CONTADOR CRÍTICO: Solo las que faltan atender. 
        # Si ya están Cerradas (como en tu imagen), ya no deben asustar al técnico.
        'assigned_criticas': tickets_base.filter(
            prioridad__icontains='Crítica'
        ).exclude(
            estado__name__in=estados_finalizados
        ).count(),
                
        # CONTADOR DE ÉXITO: Aquí es donde aparecerán tus 8 tickets de la imagen.
        'resolved_assigned_tickets': tickets_base.filter(
            estado__name__in=estados_finalizados
        ).count(),
        
        'ultimas_incidencias': ultimas_incidencias,
        'incidencias_hoy': ultimas_incidencias.count(),
    })


# ── Gestión de Incidencias ───────────────────────────────────
@login_required
@user_passes_test(is_admin)
def incidencias_admin(request):
    # 1. Obtener parámetros de orden y filtros
    orden = request.GET.get('order_by', '-fecha_creacion') # Por defecto: más nuevas arriba
    search_query = request.GET.get('search', '').strip()
    estado_filtro = request.GET.get('estado', '')
    prioridad_filtro = request.GET.get('prioridad', '')
    filtro_urgente = request.GET.get('filtro', '')

    # 2. Queryset base con optimización de relaciones (select_related)
    incidencias = Incidencia.objects.select_related(
        'creador', 'tecnico_asignado', 'area', 'estado'
    ).all()

    # 3. Aplicar Búsqueda
    if search_query:
        incidencias = incidencias.filter(
            Q(id__icontains=search_query) | 
            Q(descripcion__icontains=search_query) |
            Q(creador__first_name__icontains=search_query) |
            Q(creador__username__icontains=search_query) |
            Q(area__name__icontains=search_query) |
            Q(tecnico_asignado__first_name__icontains=search_query) |
            Q(tecnico_asignado__username__icontains=search_query)
        ).distinct()

    # 4. Aplicar Filtros de Estado y Prioridad
    if estado_filtro:
        incidencias = incidencias.filter(estado__name__iexact=estado_filtro)
    
    if prioridad_filtro:
        incidencias = incidencias.filter(prioridad__iexact=prioridad_filtro)
    
    if filtro_urgente == 'urgentes':
        incidencias = incidencias.filter(
            Q(prioridad__icontains='alt') | Q(prioridad__icontains='crit')
        ).exclude(estado__name__icontains='resuelto')

    # 5. APLICAR EL ORDEN DINÁMICO (Aquí está el cambio clave)
    # Validamos que el campo de orden sea permitido para evitar errores
    campos_validos = ['id', '-id', 'descripcion', '-descripcion', 'area', '-area', 'prioridad', '-prioridad', 'estado', '-estado', 'fecha_creacion', '-fecha_creacion']
    if orden in campos_validos:
        # Si el orden es por 'area' o 'estado', ordenamos por el nombre del objeto relacionado
        if orden == 'area': incidencias = incidencias.order_by('area__name')
        elif orden == '-area': incidencias = incidencias.order_by('-area__name')
        elif orden == 'estado': incidencias = incidencias.order_by('estado__name')
        elif orden == '-estado': incidencias = incidencias.order_by('-estado__name')
        else:
            incidencias = incidencias.order_by(orden)
    else:
        incidencias = incidencias.order_by('-fecha_creacion')

    # 6. Paginación
    paginator = Paginator(incidencias, REGISTROS_POR_PAGINA)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'tickets/incidencias_admin.html', {
        'incidencias': page_obj, 
        'page_obj': page_obj,
        'order_by': orden, # Lo pasamos al template para resaltar la columna activa
        'stats': {
            'total_criticas': Incidencia.objects.filter(Q(prioridad__iexact='Crítica') | Q(prioridad__iexact='Alta')).count(),
            'total_pendientes': Incidencia.objects.exclude(estado__name__iexact='Resuelto').count(),
            'total_resueltos': Incidencia.objects.filter(estado__name__iexact='Resuelto').count(),
        },
        'search_query': search_query, 
        'estado_filtro': estado_filtro, 
        'prioridad_filtro': prioridad_filtro,
    })

@login_required
@user_passes_test(is_tecnico)
def incidencias_asignadas(request):
    # Base: solo las asignadas al técnico actual
    incidencias = Incidencia.objects.filter(tecnico_asignado=request.user).select_related('creador', 'estado', 'area').order_by('-fecha_creacion')
    
    search_query = request.GET.get('search', '').strip()
    estado_filtro = request.GET.get('estado', '')
    
    if search_query:
        incidencias = incidencias.filter(
            Q(id__icontains=search_query) | 
            Q(descripcion__icontains=search_query) |
            Q(creador__first_name__icontains=search_query) | # Nombre del trabajador
            Q(creador__last_name__icontains=search_query) |  # Apellido del trabajador
            Q(creador__username__icontains=search_query)    # DNI/Username del trabajador
        ).distinct()
        
    if estado_filtro:
        incidencias = incidencias.filter(estado__name__iexact=estado_filtro)

    paginator = Paginator(incidencias, REGISTROS_POR_PAGINA)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'tickets/incidencias_asignadas.html', {
        'incidencias': page_obj, 
        'page_obj': page_obj,
        'search_query': search_query,
        'estado_filtro': estado_filtro
    })

@login_required
@user_passes_test(is_trabajador)
def mis_incidencias(request):
    # Optimización con select_related para cargar estado y técnico de una vez
    incidencias = Incidencia.objects.filter(creador=request.user).select_related('estado', 'area', 'tecnico_asignado').order_by('-fecha_creacion')
    
    search_query = request.GET.get('search', '').strip()
    estado_filtro = request.GET.get('estado', '')

    if search_query:
        # Busca por ID (número) o el texto de la descripción
        incidencias = incidencias.filter(
            Q(id__icontains=search_query) | 
            Q(descripcion__icontains=search_query)
        ).distinct()
        
    if estado_filtro:
        incidencias = incidencias.filter(estado__name__iexact=estado_filtro)

    paginator = Paginator(incidencias, REGISTROS_POR_PAGINA)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'tickets/mis_incidencias.html', {
        'incidencias': page_obj, 
        'page_obj': page_obj,
        'search_query': search_query,
        'estado_filtro': estado_filtro
    })

# ── Cerrar incidencia (Universal para quien creó el ticket) ──
@login_required
def cerrar_incidencia_view(request, pk):
    # CAMBIO IMPORTANTE: Ahora cualquier usuario logueado (Admin, Tecnico o Trabajador)
    # puede cerrar la incidencia SIEMPRE Y CUANDO él sea el CREADOR (solicitante).
    incidencia = get_object_or_404(Incidencia, pk=pk, creador=request.user)
    
    if incidencia.estado.name.lower() == "resuelto":
        cerrar_incidencia_service(incidencia, request.user)
        messages.success(request, "Has confirmado la solución. Ticket cerrado.")
    
    if request.headers.get('HX-Request'):
        return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
    
    # Redirigir según el rol del que cierra
    if is_admin(request.user): return redirect('incidencias_admin')
    if is_tecnico(request.user): return redirect('incidencias_asignadas')
    return redirect('mis_incidencias')

# ── Reabrir incidencia (Universal para el creador) ──
@login_required
def reabrir_incidencia_view(request, pk):
    # Al igual que cerrar, solo el que creó el ticket puede reabrirlo
    incidencia = get_object_or_404(Incidencia, pk=pk, creador=request.user)
    
    if incidencia.estado.name.lower() == "resuelto":
        estado_proceso = Estado.objects.filter(name__icontains='proceso').first()
        if estado_proceso:
            incidencia.estado = estado_proceso
            incidencia.save()
            
            Comentario.objects.create(
                incidencia=incidencia,
                usuario=request.user,
                tipo_comentario='persiste',
                texto="El solicitante indica que el problema persiste. Reabriendo ticket."
            )
            messages.warning(request, "Has reabierto la incidencia para una nueva revisión.")
        
    return redirect('detalle_incidencia', pk=pk)

# ── Perfil y Usuarios ────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def usuarios(request):
    users = CustomUser.objects.all().order_by('-date_joined')
    areas = Area.objects.all()
    q = request.GET.get('q')
    if q:
        users = users.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(email__icontains=q)
        ).distinct()
    paginator = Paginator(users, REGISTROS_POR_PAGINA)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'tickets/usuarios.html', {'users': page_obj, 'page_obj': page_obj, 'areas': areas, 'query': q})


# ── Notificaciones ───────────────────────────────────────────
@login_required
def get_unread_notifications_count(request):
    notifications = request.user.notificaciones.all().order_by('-fecha_creacion')[:10]
    unread_count = request.user.notificaciones.filter(leido=False).count()
    
    if request.headers.get('HX-Request'):
        return render(request, 'tickets/partials/notification_list.html', {
            'notifications': notifications,
            'unread_notifications_count': unread_count,
        })
    return render(request, 'tickets/partials/notification_bell.html', {
        'notifications': notifications,
        'unread_notifications_count': unread_count,
    })

@login_required
def marcar_notificaciones_leidas(request):
    # 1. Marcamos todo como leído para el usuario actual
    request.user.notificaciones.filter(leido=False).update(leido=True)

    # 2. Obtenemos datos actualizados
    notificaciones = request.user.notificaciones.all()[:10]
    unread_count = 0 # Obviamente es 0 ahora

    # 3. Renderizamos el partial de la lista
    return render(request, 'tickets/partials/notification_list.html', {
        'notifications': notificaciones,
        'unread_notifications_count': unread_count,
    })


# ── Perfil ───────────────────────────────────────────────────
@login_required
def mi_perfil(request):
    user = request.user
    profile_form = CustomUserChangeForm(instance=user)
    password_form = PasswordChangeForm(user)
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = CustomUserChangeForm(request.POST, request.FILES, instance=user)
            if profile_form.is_valid():
                perfil_edit = profile_form.save(commit=False)
                perfil_edit.area = user.area
                perfil_edit.telefono = request.POST.get('telefono')
                if 'foto' in request.FILES:
                    perfil_edit.foto = request.FILES['foto']
                if user.role == 'administrador':
                    perfil_edit.first_name = request.POST.get('first_name')
                    perfil_edit.last_name = request.POST.get('last_name')
                else:
                    perfil_edit.first_name = user.first_name
                    perfil_edit.last_name = user.last_name
                perfil_edit.save()
                messages.success(request, 'Perfil actualizado exitosamente.')
                return redirect('mi_perfil')
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user_updated = password_form.save()
                user_updated.must_change_password = False
                user_updated.last_password_change = timezone.now()
                user_updated.save()
                update_session_auth_hash(request, user_updated)
                messages.success(request, 'Contraseña cambiada exitosamente.')
                return redirect('mi_perfil')
    return render(request, 'tickets/mi_perfil.html', {'profile_form': profile_form, 'password_form': password_form})


# ── Detalle de incidencia ────────────────────────────────────
@login_required
def detalle_incidencia(request, pk):
    incidencia = get_object_or_404(Incidencia, pk=pk)
    comentarios = incidencia.comentarios.all().order_by('fecha_creacion')

    if request.method == 'POST':
        texto = request.POST.get('texto_comentario')
        if texto:
            Comentario.objects.create(
                incidencia=incidencia,
                usuario=request.user,
                texto=texto
            )
            comentarios = incidencia.comentarios.all().order_by('fecha_creacion')
        return render(request, 'tickets/partials/_comentarios_list.html', {'comentarios': comentarios})

    if request.headers.get('HX-Request'):
        return render(request, 'tickets/partials/_comentarios_list.html', {'comentarios': comentarios})

    return render(request, 'tickets/detalle_incidencia.html', {
        'incidencia': incidencia,
        'comentarios': comentarios,
        'is_tecnico': request.user.role == 'tecnico',
    })


# ── Crear incidencia ─────────────────────────────────────────
@login_required
def crear_incidencia(request):
    es_admin = is_admin(request.user)
    es_tecnico_user = is_tecnico(request.user)
    
    FormularioClase = IncidenciaAdminForm if es_admin else IncidenciaForm
    
    if request.method == 'POST':
        form = FormularioClase(request.POST, request.FILES) if es_admin else FormularioClase(request.POST, request.FILES, user=request.user)
            
        if form.is_valid():
            nueva = form.save(commit=False)
            nueva.creador = request.user
            
            if es_admin:
                # Validación manual extra para el Admin:
                if not nueva.categoria or not nueva.prioridad or not nueva.area:
                    messages.error(request, 'Admin: Categoría, Prioridad y Área son obligatorios.')
                    return render(request, 'tickets/crear_incidencia.html', {'form': form, 'es_admin': es_admin})

                if nueva.tecnico_asignado:
                    estado_nombre = 'En Proceso'
                else:
                    estado_nombre = 'Pendiente'
            else:
                nueva.area = request.user.area
                estado_nombre = 'Pendiente'

            # Asignación segura del estado
            nueva.estado = Estado.objects.filter(name__iexact=estado_nombre).first()
            nueva.save()
            
            # --- NOTIFICACIONES ---
            if nueva.tecnico_asignado and nueva.tecnico_asignado != request.user:
                from .models import Notificacion
                Notificacion.objects.create(
                    usuario_destino=nueva.tecnico_asignado,
                    incidencia=nueva,
                    mensaje=f"Nueva incidencia #{nueva.id:04d} asignada.",
                    tipo="asignacion"
                )

            messages.success(request, 'Incidencia registrada exitosamente.')
            
            if es_admin: return redirect('incidencias_admin')
            return redirect('mis_incidencias')
            
    else:
        form = FormularioClase() if es_admin else FormularioClase(user=request.user)
            
    return render(request, 'tickets/crear_incidencia.html', {'form': form, 'es_admin': es_admin})


# ── Gestionar incidencia (admin) ─────────────────────────────
@login_required
@user_passes_test(is_admin)
def gestionar_incidencia(request, pk):
    incidencia = get_object_or_404(Incidencia, pk=pk)
    
    if request.method == 'POST':
        form = IncidenciaAdminForm(request.POST, request.FILES, instance=incidencia)
        if form.is_valid():
            ins = form.save(commit=False)
            
            # --- LÓGICA AUTOMÁTICA DE ESTADO ---
            # Si el Admin asigna un técnico, el estado pasa a 'En Proceso' automáticamente.
            # Solo lo hacemos si el estado actual es 'Pendiente' o 'Asignado'.
            if ins.tecnico_asignado and ins.estado.name.lower() in ['pendiente', 'asignado']:
                estado_proceso = Estado.objects.filter(name__icontains='proceso').first()
                if estado_proceso:
                    ins.estado = estado_proceso
            
            ins.save()
            
            # Notificación para el técnico
            Notificacion.objects.create(
                usuario_destino=ins.tecnico_asignado,
                incidencia=ins,
                mensaje=f"Se te ha asignado la incidencia #{ins.id:04d}",
                tipo="asignacion"
            )
            
            messages.success(request, f"Incidencia #{ins.id:04d} actualizada y en proceso.")
            return redirect('detalle_incidencia', pk=ins.id)
    else:
        form = IncidenciaAdminForm(instance=incidencia)
    
    return render(request, 'tickets/gestionar_incidencia.html', {
        'form': form, 
        'incidencia': incidencia
    })


@login_required
def resolver_incidencia(request, pk):
    incidencia = get_object_or_404(Incidencia, pk=pk)
    
    # 1. Validación de Permisos
    es_admin = request.user.role == 'administrador'
    es_tecnico_asignado = incidencia.tecnico_asignado == request.user
    
    if not (es_admin or es_tecnico_asignado):
        messages.error(request, "No tienes permiso para resolver esta incidencia.")
        return redirect('detalle_incidencia', pk=pk)

    if request.method == 'POST':
        solucion = request.POST.get('solucion_aplicada', '').strip()
        evidencia = request.FILES.get('evidencia_solucion')

        # 2. Validación de contenido
        if not solucion or len(solucion) < 10:
            messages.warning(request, "Por favor, detalle mejor la solución (mínimo 10 caracteres).")
            return redirect('detalle_incidencia', pk=pk)

        # 3. Validación de Imagen
        if evidencia:
            if evidencia.name.lower().endswith('.pdf') or not evidencia.content_type.startswith('image/'):
                messages.error(request, "⚠️ Error: No se pueden subir archivos PDF. Use una imagen (JPG o PNG).")
                return redirect('detalle_incidencia', pk=pk)
            incidencia.evidencia_solucion = evidencia

        # 4. Actualización de datos e Historial
        incidencia.solucion_aplicada = solucion
        estado_resuelto = Estado.objects.filter(name__iexact='Resuelto').first()
        if estado_resuelto:
            incidencia.estado = estado_resuelto
        
        incidencia.save()

        # 5. Crear Comentario de tipo "confirmacion" para el historial
        Comentario.objects.create(
            incidencia=incidencia,
            usuario=request.user,
            tipo_comentario="confirmacion",
            texto=f"Resolución marcada: {solucion}",
            evidencia_adjunta=evidencia if evidencia else None
        )

        # 6. NOTIFICAR A LOS ADMINISTRADORES
        admins = CustomUser.objects.filter(role='administrador')
        link_detalle = reverse('detalle_incidencia', kwargs={'pk': incidencia.id})
        
        for admin in admins:
            Notificacion.objects.create(
                usuario_destino=admin,
                incidencia=incidencia,
                mensaje=f"Ticket #{incidencia.id:04d} resuelto por {request.user.username}",
                tipo="incidencia_resuelta",
                link=link_detalle
            )

        messages.success(request, '¡Incidencia resuelta! Se ha notificado al administrador.')
        return redirect('detalle_incidencia', pk=pk)
            
    return redirect('detalle_incidencia', pk=pk)


# ── Usuarios ─────────────────────────────────────────────────
@login_required
def crear_usuario(request):
    if request.method == 'POST':
        dni = request.POST.get('username')
        if not dni or len(dni) < 4:
            messages.error(request, "El DNI debe tener al menos 4 dígitos.")
            return redirect('usuarios')
        user = CustomUser(
            username=dni,
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            email=request.POST.get('email'),
            role=request.POST.get('role'),
            area_id=request.POST.get('area'),
            must_change_password=True
        )
        ultimos_4 = dni[-4:]
        user.set_password(f"Ugel@{ultimos_4}")
        user.save()
        messages.success(request, f"Usuario {dni} creado. Clave inicial: Ugel@{ultimos_4}")
    return redirect('usuarios')

@login_required
@user_passes_test(is_admin)
def editar_usuario(request, pk):
    usuario = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, request.FILES, instance=usuario)
        if form.is_valid():
            user_edit = form.save(commit=False)
            user_edit.area_id = request.POST.get('area')
            user_edit.role = request.POST.get('role')
            user_edit.save()
            messages.success(request, f"Usuario {usuario.username} actualizado.")
    return redirect('usuarios')

@login_required
@user_passes_test(is_admin)
def toggle_usuario_status(request, pk):
    usuario = get_object_or_404(CustomUser, pk=pk)
    usuario.is_active = not usuario.is_active
    usuario.save()
    messages.info(request, f"Usuario {usuario.username} {'activado' if usuario.is_active else 'desactivado'}.")
    return redirect('usuarios')

@login_required
def reset_password_admin(request, user_id):
    if request.user.role != 'administrador':
        messages.error(request, "No tienes permiso.")
        return redirect('usuarios')
    usuario = get_object_or_404(CustomUser, id=user_id)
    ultimos_4 = usuario.username[-4:]
    usuario.set_password(f"Ugel@{ultimos_4}")
    usuario.must_change_password = True
    usuario.save()
    messages.success(request, f"Clave de {usuario.get_full_name()} restablecida a: Ugel@{ultimos_4}")
    return redirect('usuarios')

# ── Vistas de Error ──────────────────────────────────────────
def error_404_view(request, exception):
    return render(request, 'tickets/404.html', {}, status=404)

def error_500_view(request):
    return render(request, 'tickets/500.html', {}, status=500)

@login_required
def password_change_forced(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            user.must_change_password = False
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Contraseña actualizada. ¡Bienvenido!')
            return redirect('index')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'tickets/forced_change.html', {'form': form})

@login_required
def ir_a_notificacion(request, pk):
    notif = get_object_or_404(Notificacion, pk=pk, usuario_destino=request.user)
    notif.leido = True
    notif.save()
    # Redirigir al link de la incidencia (ej: detalle del ticket)
    return redirect(notif.link or 'dashboard')

# Única función para resolver imágenes en los PDFs
def fetch_resources(uri, rel):
    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
        print(f"Buscando imagen en: {path}") # Mira tu terminal de VS Code para ver si la ruta es real
        if os.path.isfile(path):
            return path
    return uri