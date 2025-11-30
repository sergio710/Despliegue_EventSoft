from django.shortcuts import render , redirect, get_object_or_404
from django.contrib import messages
from app_participantes.models import ParticipanteEvento , Participante, Proyecto
from app_eventos.models import EventoCategoria, Evento
from app_evaluadores.models import Criterio, Calificacion
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required, user_passes_test
from app_usuarios.permisos import es_participante
from django.urls import reverse
from django.http import Http404, HttpResponse, FileResponse
from django.conf import settings
import os


@login_required
@user_passes_test(es_participante, login_url='login')
def dashboard_participante_general(request):
    participante = request.user.participante
    inscripciones = ParticipanteEvento.objects.filter(participante=participante)

    if not inscripciones.exists():
        messages.warning(request, "No tienes inscripciones registradas.")
        return redirect('ingreso_participante')

    eventos = []
    estadisticas = {
        'total': 0,
        'pendientes': 0,
        'aprobados': 0,
        'rechazados': 0,
        'cancelados': 0
    }

    for inscripcion in inscripciones:
        evento_data = {
            'eve_id': inscripcion.evento.eve_id,
            'eve_nombre': inscripcion.evento.eve_nombre,
            'eve_fecha_inicio': inscripcion.evento.eve_fecha_inicio,
            'eve_fecha_fin': inscripcion.evento.eve_fecha_fin,
            'par_eve_estado': inscripcion.par_eve_estado,
        }
        eventos.append(evento_data)
        
        # Contar estadísticas
        estadisticas['total'] += 1
        if inscripcion.par_eve_estado == 'Pendiente':
            estadisticas['pendientes'] += 1
        elif inscripcion.par_eve_estado == 'Aprobado':
            estadisticas['aprobados'] += 1
        elif inscripcion.par_eve_estado == 'Rechazado':
            estadisticas['rechazados'] += 1
        elif inscripcion.par_eve_estado == 'Cancelado':
            estadisticas['cancelados'] += 1

    return render(request, 'dashboard_participante_general.html', {
        'eventos': eventos,
        'estadisticas': estadisticas
    })

@login_required
@user_passes_test(es_participante, login_url='login')
def dashboard_participante_evento(request, evento_id):
    participante = request.user.participante
    inscripcion = get_object_or_404(
        ParticipanteEvento, participante=participante, evento__pk=evento_id
    )

    # Proyectos de los que este participante es creador (individual o grupal)
    proyectos_lider = Proyecto.objects.filter(
        evento_id=evento_id,
        creador=participante
    )

    datos = {
        'par_nombre': participante.usuario.first_name,
        'par_correo': participante.usuario.email,
        'par_telefono': participante.usuario.telefono,
        'eve_nombre': inscripcion.evento.eve_nombre,
        'eve_programacion': inscripcion.evento.eve_programacion,
        'eve_informacion_tecnica': inscripcion.evento.eve_informacion_tecnica,
        'eve_memorias': inscripcion.evento.eve_memorias,
        'par_eve_estado': inscripcion.par_eve_estado,
        'par_id': participante.id,
        'eve_id': inscripcion.evento.eve_id
    }
    return render(request, 'dashboard_participante.html', {
        'datos': datos,
        'proyectos_lider': proyectos_lider,
    })


@login_required
@user_passes_test(es_participante, login_url='login')
@require_http_methods(["GET", "POST"])
def modificar_preinscripcion(request, evento_id):
    participante = get_object_or_404(Participante, usuario=request.user)
    evento = get_object_or_404(Evento, pk=evento_id)
    inscripcion = get_object_or_404(
        ParticipanteEvento,
        participante=participante,
        evento=evento
    )
    if inscripcion.par_eve_estado != 'Pendiente':
        messages.warning(request, "No puedes modificar esta inscripción.")
        return redirect('dashboard_participante_evento', evento_id=evento_id)
    if request.method == 'POST':
        participante.par_nombre = request.POST.get('nombre')
        participante.par_correo = request.POST.get('correo')
        participante.par_telefono = request.POST.get('telefono')
        documento = request.FILES.get('documento')
        if documento:
            inscripcion.par_eve_documentos = documento
        participante.save()
        inscripcion.save()
        messages.success(request, "Datos actualizados correctamente")
        return redirect('dashboard_participante_evento', evento_id=evento_id)
    return render(request, 'modificar_preinscripcion_participante.html', {
        'participante': participante,
        'inscripcion': inscripcion,
        'evento': evento,
    })

@login_required
@user_passes_test(es_participante, login_url='login')
@require_POST
def cancelar_inscripcion(request):
    participante = get_object_or_404(Participante, usuario=request.user)
    inscripcion = ParticipanteEvento.objects.filter(participante=participante).order_by('-id').first()
    if inscripcion:
        evento = inscripcion.evento
        inscripcion.delete()
        if not ParticipanteEvento.objects.filter(participante=participante).exists():
            participante.delete()
        messages.info(request, "Has cancelado tu inscripción exitosamente.")
    else:
        messages.warning(request, "No se encontró inscripción activa.")  
    return render(request, 'preinscripcion_cancelada.html')

@login_required
@user_passes_test(es_participante, login_url='login')
def ver_qr_participante(request, evento_id):
    try:
        participante = request.user.participante
        relacion = ParticipanteEvento.objects.select_related('evento').get(
            participante=participante,
            evento_id=evento_id
        )
        evento = relacion.evento
        datos = {
            'qr_url': relacion.par_eve_qr.url if relacion.par_eve_qr else None,
            'eve_nombre': evento.eve_nombre,
            'eve_lugar': evento.eve_lugar,
            'eve_descripcion': evento.eve_descripcion,
        }
        return render(request, 'ver_qr_participante.html', {
            'datos': datos,
            'evento_id': evento_id
        })

    except ParticipanteEvento.DoesNotExist:
        messages.error(request, "QR no encontrado para esta inscripción.")
        return redirect('dashboard_participante')

@login_required
@user_passes_test(es_participante, login_url='login')
def descargar_qr_participante(request, evento_id):
    try:
        participante = request.user.participante
        inscripcion = ParticipanteEvento.objects.get(
            participante=participante,
            evento__eve_id=evento_id
        )
        if inscripcion.par_eve_qr and os.path.exists(inscripcion.par_eve_qr.path):
            with open(inscripcion.par_eve_qr.path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='image/png')
                filename = f'qr_evento_{evento_id}_participante_{participante.id}.png'
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
        raise Http404("QR no disponible o archivo no encontrado")
    except ParticipanteEvento.DoesNotExist:
        raise Http404("QR no encontrado para esta inscripción")
    
@login_required
@user_passes_test(es_participante, login_url='login')
def ver_evento_completo(request, evento_id):
    request.user.participante
    evento = get_object_or_404(Evento, pk=evento_id)
    administrador = evento.eve_administrador_fk.usuario 
    evento_categorias = EventoCategoria.objects.filter(evento=evento).select_related('categoria__cat_area_fk')
    categorias_data = []
    for ec in evento_categorias:
        categoria = ec.categoria
        area = categoria.cat_area_fk
        categorias_data.append({
            'cat_nombre': categoria.cat_nombre,
            'cat_descripcion': categoria.cat_descripcion,
            'are_nombre': area.are_nombre,
            'are_descripcion': area.are_descripcion
        })
    evento_data = {
        'eve_id': evento.eve_id,
        'eve_nombre': evento.eve_nombre,
        'eve_descripcion': evento.eve_descripcion,
        'eve_ciudad': evento.eve_ciudad,
        'eve_lugar': evento.eve_lugar,
        'eve_fecha_inicio': evento.eve_fecha_inicio,
        'eve_fecha_fin': evento.eve_fecha_fin,
        'eve_estado': evento.eve_estado,
        'eve_capacidad': evento.eve_capacidad,
        'eve_tienecosto': evento.eve_tienecosto,
        'tiene_costo_legible': 'Sí' if evento.eve_tienecosto.upper() == 'SI' else 'No',
        'eve_programacion': evento.eve_programacion,
        'eve_informacion_tecnica': evento.eve_informacion_tecnica,
        'eve_memorias': evento.eve_memorias,
        'adm_nombre': administrador.get_full_name(),
        'adm_correo': administrador.email,
        'categorias': categorias_data,
    }

    return render(request, 'evento_completo_participante.html', {'evento': evento_data})

@login_required
@user_passes_test(es_participante, login_url='login')
def instrumento_evaluacion(request, evento_id):
    participante = request.user.participante
    evento = get_object_or_404(Evento, pk=evento_id)
    inscrito = ParticipanteEvento.objects.filter(participante=participante, evento=evento).exists()
    if not inscrito:
        messages.warning(request, "No estás inscrito en este evento.")
        return redirect('dashboard_participante', evento_id=evento_id)
    criterios = Criterio.objects.filter(cri_evento_fk=evento)
    return render(request, 'instrumento_evaluacion_participante.html', {
        'evento': evento,
        'criterios': criterios,
    })

@login_required
@user_passes_test(es_participante, login_url='login')
def ver_calificaciones_participante(request, evento_id):
    participante = request.user.participante
    evento = get_object_or_404(Evento, pk=evento_id)

    pe_usuario = ParticipanteEvento.objects.filter(
        participante=participante,
        evento=evento
    ).first()

    if not pe_usuario:
        messages.warning(request, "No estás inscrito en este evento.")
        return redirect('dashboard_participante_evento', evento_id=evento_id)

    # Por defecto, se usan sus propias calificaciones
    participante_referencia = participante

    # Si es grupal (tiene código), buscar dentro del grupo quién tiene calificaciones
    if pe_usuario.codigo:
        grupo = ParticipanteEvento.objects.filter(
            evento=evento,
            codigo=pe_usuario.codigo
        ).select_related('participante')

        ref = None
        for pe in grupo:
            if Calificacion.objects.filter(
                participante=pe.participante,
                criterio__cri_evento_fk=evento
            ).exists():
                ref = pe.participante
                break

        if ref:
            participante_referencia = ref

    calificaciones = Calificacion.objects.select_related('evaluador__usuario', 'criterio').filter(
        participante=participante_referencia,
        criterio__cri_evento_fk=evento
    )

    return render(request, 'ver_calificaciones_participante.html', {
        'calificaciones': calificaciones,
        'evento': evento,
    })

@login_required
@user_passes_test(es_participante, login_url='login')
def descargar_informacion_tecnica(request, evento_id):
    participante = request.user.participante
    evento = get_object_or_404(Evento, pk=evento_id)
    
    # Verificar que el participante esté inscrito y aprobado
    inscripcion = get_object_or_404(
        ParticipanteEvento, 
        participante=participante, 
        evento=evento,
        par_eve_estado='Aprobado'
    )
    
    if not evento.eve_informacion_tecnica:
        messages.error(request, "Este evento no tiene información técnica disponible.")
        return redirect('dashboard_participante_evento', evento_id=evento_id)
    
    try:
        response = HttpResponse(
            evento.eve_informacion_tecnica.read(),
            content_type='application/pdf'
        )
        filename = f'informacion_tecnica_{evento.eve_nombre.replace(" ", "_")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except FileNotFoundError:
        messages.error(request, "El archivo de información técnica no se encuentra disponible.")
        return redirect('dashboard_participante_evento', evento_id=evento_id)

@login_required
@user_passes_test(es_participante, login_url='login')
def descargar_memorias(request, evento_id):
    participante = request.user.participante
    evento = get_object_or_404(Evento, pk=evento_id)

    # Verificar que el participante esté inscrito y aprobado
    inscripcion = get_object_or_404(
        ParticipanteEvento,
        participante=participante,
        evento=evento,
        par_eve_estado='Aprobado'
    )

    if not evento.eve_memorias:
        messages.error(request, "Este evento no tiene memorias disponibles.")
        return redirect('dashboard_participante_evento', evento_id=evento_id)

    # Forzar descarga del archivo (ZIP, PDF o lo que sea)
    try:
        nombre_archivo = evento.eve_memorias.name.split('/')[-1]
        response = FileResponse(
            open(evento.eve_memorias.path, 'rb'),
            as_attachment=True,
            filename=nombre_archivo
        )
        return response
    except FileNotFoundError:
        messages.error(request, "El archivo de memorias no se encuentra disponible.")
        return redirect('dashboard_participante_evento', evento_id=evento_id)

    
# Agregar estas funciones actualizadas a tu views.py de app_participantes

@login_required
def mis_proyectos(request):
    """Lista de proyectos en los que participa el usuario logueado"""
    participante = getattr(request.user, 'participante', None)
    if not participante:
        return render(request, "mis_proyectos.html", {"proyectos_data": []})

    from app_participantes.models import Proyecto

    proyectos_map = {}

    # 1) Proyectos donde participa vía ParticipanteEvento (principal o integrante)
    inscripciones = ParticipanteEvento.objects.filter(
        participante=participante,
        proyecto__isnull=False
    ).select_related('proyecto', 'evento')

    for inscripcion in inscripciones:
        proyecto = inscripcion.proyecto
        key = (proyecto.id, inscripcion.evento.eve_id)
        if key not in proyectos_map:
            proyectos_map[key] = {
                'proyecto': proyecto,
                'evento': inscripcion.evento,
                'estado_inscripcion': inscripcion.par_eve_estado,
            }

    # 2) Proyectos que el participante creó (principal + extras) en cada evento
    # 2) Proyectos que el participante creó (principal + extras) en cada evento
    proyectos_creados = Proyecto.objects.filter(creador=participante).select_related('evento')

    for proyecto in proyectos_creados:
        key = (proyecto.id, proyecto.evento.eve_id)
        if key not in proyectos_map:
            # Buscar la inscripción del participante en ese evento para tomar su estado real
            pe = ParticipanteEvento.objects.filter(
                participante=participante,
                evento=proyecto.evento
            ).first()

            estado = pe.par_eve_estado if pe else 'Pendiente'

            proyectos_map[key] = {
                'proyecto': proyecto,
                'evento': proyecto.evento,
                'estado_inscripcion': estado,
            }


    # 3) Si es integrante grupal (no creador), incluir también los proyectos del líder del grupo
    #    para cada evento donde tenga código de grupo.
    pe_con_codigo = ParticipanteEvento.objects.filter(
        participante=participante,
        codigo__isnull=False
    ).select_related('evento')

    for pe_usuario in pe_con_codigo:
        evento = pe_usuario.evento

        # Buscar líder del grupo en este evento: alguien del mismo código que sea creador de proyectos
        lider_ids = Proyecto.objects.filter(
            evento=evento
        ).exclude(creador__isnull=True).values_list('creador_id', flat=True)

        pe_lider = ParticipanteEvento.objects.filter(
            evento=evento,
            codigo=pe_usuario.codigo,
            participante_id__in=lider_ids
        ).first()

        if not pe_lider:
            continue

        # Proyectos del líder en este evento = proyectos del grupo
        proyectos_lider = Proyecto.objects.filter(
            evento=evento,
            creador_id=pe_lider.participante_id
        ).select_related('evento')

        for proyecto in proyectos_lider:
            key = (proyecto.id, proyecto.evento.eve_id)
            if key not in proyectos_map:
                # El estado que ve el integrante es el de su propia inscripción
                estado = pe_usuario.par_eve_estado
                proyectos_map[key] = {
                    'proyecto': proyecto,
                    'evento': proyecto.evento,
                    'estado_inscripcion': estado,
                }

    proyectos_data = list(proyectos_map.values())

    return render(request, "mis_proyectos.html", {"proyectos_data": proyectos_data})

@login_required
def detalle_proyecto(request, proyecto_id):
    """Detalle de un proyecto del usuario (individual o grupal)."""
    proyecto = get_object_or_404(Proyecto, pk=proyecto_id)

    participante = getattr(request.user, 'participante', None)
    if not participante:
        messages.error(request, "No tienes acceso a este proyecto.")
        return redirect('mis_proyectos')

    # 1) Es creador del proyecto (individual o líder grupal)
    es_creador = (proyecto.creador_id == getattr(participante, 'id', None))

    # 2) Tiene relación directa en ParticipanteEvento con este proyecto
    tiene_pe_directo = ParticipanteEvento.objects.filter(
        participante=participante,
        evento=proyecto.evento,
        proyecto=proyecto
    ).exists()

    # 3) Es integrante de un grupo cuyo líder es el creador de este proyecto
    es_integrante_del_grupo = False
    if not es_creador and not tiene_pe_directo:
        # ParticipanteEvento del usuario en este evento (puede ser principal o integrante extra)
        pe_usuario = ParticipanteEvento.objects.filter(
            participante=participante,
            evento=proyecto.evento,
            codigo__isnull=False
        ).first()

        # ParticipanteEvento del creador (líder) en este evento
        pe_creador = None
        if proyecto.creador_id:
            pe_creador = ParticipanteEvento.objects.filter(
                participante_id=proyecto.creador_id,
                evento=proyecto.evento
            ).first()

        if pe_usuario and pe_creador and pe_usuario.codigo and pe_creador.codigo:
            # Mismo código de grupo => mismo grupo
            es_integrante_del_grupo = (pe_usuario.codigo == pe_creador.codigo)

    if not (es_creador or tiene_pe_directo or es_integrante_del_grupo):
        messages.error(request, "No tienes acceso a este proyecto.")
        return redirect('mis_proyectos')

    # -------- Integrantes a mostrar --------
    integrantes_qs = ParticipanteEvento.objects.none()

    # Si el proyecto es grupal (creador tiene código en este evento), mostrar a todo el grupo
    if proyecto.creador_id:
        pe_creador = ParticipanteEvento.objects.filter(
            participante_id=proyecto.creador_id,
            evento=proyecto.evento
        ).first()

        if pe_creador and pe_creador.codigo:
            integrantes_qs = ParticipanteEvento.objects.filter(
                evento=proyecto.evento,
                codigo=pe_creador.codigo
            ).select_related("participante__usuario", "evento")
        else:
            # No tiene código (proyecto individual): solo el creador aparece como integrante
            integrantes_qs = ParticipanteEvento.objects.filter(
                participante_id=proyecto.creador_id,
                evento=proyecto.evento
            ).select_related("participante__usuario", "evento")
    else:
        # Sin creador (casos viejos): usar los PE que ya apunten al proyecto
        integrantes_qs = ParticipanteEvento.objects.filter(
            evento=proyecto.evento,
            proyecto=proyecto
        ).select_related("participante__usuario", "evento")

    return render(request, "detalle_proyecto.html", {
        "proyecto": proyecto,
        "integrantes": integrantes_qs
    })

def manual_participante(request):
    """
    Sirve el manual del Participante en formato PDF.
    """
    ruta_manual = os.path.join(settings.MEDIA_ROOT, "manuales", "MANUAL_EXPOSITOR_SISTEMA_EVENTSOFT.pdf")
    if os.path.exists(ruta_manual):
        return FileResponse(open(ruta_manual, "rb"), content_type="application/pdf")
    raise Http404("Manual no encontrado")

@login_required
@user_passes_test(es_participante, login_url='login')
def gestionar_proyectos_evento(request, evento_id):
    """
    Para el participante logueado:
    - Si es creador de proyectos en este evento: ve SUS proyectos (principal + extras) con Editar/Eliminar.
    - Si no es creador (integrante grupal): ve todos los proyectos del grupo, solo con Ver detalles.
    Solo disponible mientras su inscripción esté en estado Pendiente.
    """
    participante = request.user.participante
    evento = get_object_or_404(Evento, pk=evento_id)

    # Inscripción principal del usuario en este evento
    inscripcion = get_object_or_404(
        ParticipanteEvento,
        participante=participante,
        evento=evento
    )

    if inscripcion.par_eve_estado != 'Pendiente':
        messages.warning(request, "Solo puedes gestionar proyectos mientras tu inscripción esté en estado Pendiente.")
        return redirect('dashboard_participante_evento', evento_id=evento_id)

    from app_participantes.models import Proyecto

    # ¿Es líder / creador de algún proyecto en este evento?
    proyectos_creados = Proyecto.objects.filter(evento=evento, creador=participante)

    if proyectos_creados.exists():
        # LÍDER O PARTICIPANTE INDIVIDUAL:
        # ve solo los proyectos que él creó (principal + extras) y puede editar / eliminar.
        proyectos = proyectos_creados
        es_lider = True

    else:
        # INTEGRANTE GRUPAL:
        # buscar el código de grupo del usuario en este evento
        pe_usuario = ParticipanteEvento.objects.filter(
            participante=participante,
            evento=evento,
            codigo__isnull=False
        ).first()

        if pe_usuario and pe_usuario.codigo:
            # Obtener al líder del grupo: cualquier PE del mismo código cuyo participante sea creador
            # de algún proyecto en este evento.
            lider_ids = Proyecto.objects.filter(
                evento=evento
            ).exclude(creador__isnull=True).values_list('creador_id', flat=True)

            pe_lider = ParticipanteEvento.objects.filter(
                evento=evento,
                codigo=pe_usuario.codigo,
                participante_id__in=lider_ids
            ).first()

            if pe_lider:
                # Proyectos del líder en este evento = proyectos del grupo
                proyectos = Proyecto.objects.filter(
                    evento=evento,
                    creador_id=pe_lider.participante_id
                )
            else:
                # Si no se encuentra líder (caso raro), el integrante solo verá proyectos donde tenga PE directo
                proyectos = Proyecto.objects.filter(
                    evento=evento,
                    participantes__participante=participante
                ).distinct()
        else:
            # No es líder ni tiene código de grupo; usar solo proyectos vinculados vía ParticipanteEvento
            proyectos = Proyecto.objects.filter(
                evento=evento,
                participantes__participante=participante
            ).distinct()

        es_lider = False

    return render(request, 'gestionar_proyectos_evento.html', {
        'evento': evento,
        'proyectos': proyectos,
        'es_lider': es_lider,
    })

@login_required
@user_passes_test(es_participante, login_url='login')
def editar_proyecto_participante(request, evento_id, proyecto_id):
    participante = request.user.participante
    evento = get_object_or_404(Evento, pk=evento_id)
    # Solo proyectos donde este participante es creador (líder o dueño)
    proyecto = get_object_or_404(Proyecto, pk=proyecto_id, evento=evento, creador=participante)

    inscripcion = get_object_or_404(
        ParticipanteEvento,
        participante=participante,
        evento=evento
    )
    if inscripcion.par_eve_estado != 'Pendiente':
        messages.warning(request, "Solo puedes editar proyectos mientras tu inscripción esté en estado Pendiente.")
        return redirect('dashboard_participante_evento', evento_id=evento_id)

    if request.method == 'POST':
        proyecto.titulo = request.POST.get('titulo') or proyecto.titulo
        proyecto.descripcion = request.POST.get('descripcion') or proyecto.descripcion
        archivo_nuevo = request.FILES.get('archivo')
        if archivo_nuevo:
            proyecto.archivo = archivo_nuevo
        proyecto.save()
        messages.success(request, "Proyecto actualizado correctamente.")
        return redirect('gestionar_proyectos_evento', evento_id=evento_id)

    return render(request, 'editar_proyecto_participante.html', {
        'evento': evento,
        'proyecto': proyecto,
    })


@login_required
@user_passes_test(es_participante, login_url='login')
def eliminar_proyecto_participante(request, evento_id, proyecto_id):
    participante = request.user.participante
    evento = get_object_or_404(Evento, pk=evento_id)
    proyecto = get_object_or_404(Proyecto, pk=proyecto_id, evento=evento, creador=participante)

    inscripcion = get_object_or_404(
        ParticipanteEvento,
        participante=participante,
        evento=evento
    )
    if inscripcion.par_eve_estado != 'Pendiente':
        messages.warning(request, "Solo puedes eliminar proyectos mientras tu inscripción esté en estado Pendiente.")
        return redirect('dashboard_participante_evento', evento_id=evento_id)

    if request.method == 'POST':
        proyecto.delete()
        messages.success(request, "Proyecto eliminado correctamente.")
        return redirect('gestionar_proyectos_evento', evento_id=evento_id)

    return render(request, 'confirmar_eliminar_proyecto.html', {
        'evento': evento,
        'proyecto': proyecto,
    })