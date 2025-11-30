from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from app_usuarios.permisos import es_evaluador
from django.contrib import messages
from django.http import HttpResponse, FileResponse, Http404
from .models import Evaluador
from app_eventos.models import Evento, EventoCategoria
from app_evaluadores.models import Criterio, Calificacion, EvaluadorEvento
from app_participantes.models import ParticipanteEvento, Participante
from app_usuarios.models import Usuario
import os
from django.conf import settings
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle


def calcular_y_guardar_nota_general(participante, evento):
    criterios = Criterio.objects.filter(cri_evento_fk=evento)
    peso_total = sum(c.cri_peso for c in criterios) or 1

    calificaciones = Calificacion.objects.filter(
        participante=participante,
        criterio__cri_evento_fk=evento
    ).select_related('criterio')

    evaluadores_ids = set(c.evaluador_id for c in calificaciones)
    num_evaluadores = len(evaluadores_ids)

    if num_evaluadores > 0:
        puntaje_ponderado = sum(
            c.cal_valor * c.criterio.cri_peso for c in calificaciones
        ) / (peso_total * num_evaluadores)

        participante_evento = ParticipanteEvento.objects.get(
            participante=participante,
            evento=evento
        )
        participante_evento.par_eve_valor = round(puntaje_ponderado, 1)
        participante_evento.save()

        return round(puntaje_ponderado, 1)

    return 0

def obtener_puesto_participante(participante, evento):
    """
    Obtiene el puesto de un participante en un evento basado en su nota
    """
    # Obtener todas las participaciones del evento ordenadas por nota
    participaciones = ParticipanteEvento.objects.filter(
        evento=evento,
        par_eve_estado='Aprobado',
        par_eve_valor__isnull=False
    ).order_by('-par_eve_valor')
    
    # Encontrar el puesto del participante
    for i, pe in enumerate(participaciones, 1):
        if pe.participante == participante:
            return i
    
    return None  # No encontrado o sin calificación

@login_required
@user_passes_test(es_evaluador, login_url='login')
def dashboard_evaluador(request):
    evaluador = request.user.evaluador
    inscripciones = EvaluadorEvento.objects.select_related('evento').filter(evaluador=evaluador)

    # Agregar información sobre archivos disponibles a cada inscripción
    inscripciones_con_archivos = []
    for inscripcion in inscripciones:
        inscripcion_data = {
            'inscripcion': inscripcion,
            'evento': inscripcion.evento,
            'estado': inscripcion.eva_eve_estado,
            'tiene_memorias': bool(inscripcion.evento.eve_memorias),
            'tiene_info_tecnica': bool(inscripcion.evento.eve_informacion_tecnica),
        }
        inscripciones_con_archivos.append(inscripcion_data)

    return render(request, 'app_evaluadores/dashboard_evaluador.html', {
        'evaluador': evaluador,
        'inscripciones': inscripciones,
        'inscripciones_con_archivos': inscripciones_con_archivos
    })


@login_required
@user_passes_test(es_evaluador, login_url='login')
def gestionar_items(request, eve_id):
    evento = get_object_or_404(Evento, pk=eve_id)
    try:
        evaluador = request.user.evaluador
        inscripcion = EvaluadorEvento.objects.get(evaluador=evaluador, evento=evento)
        
        # Verificar que la inscripción esté aprobada
        if inscripcion.eva_eve_estado != 'Aprobado':
            messages.warning(request, "Tu inscripción como evaluador no ha sido aprobada para este evento.")
            return redirect('dashboard_evaluador')
        
        # Verificar que tenga permiso para gestionar la rúbrica
        if not inscripcion.puede_gestionar_rubrica:
            messages.warning(request, "No tienes permiso para gestionar la rúbrica de este evento.")
            return redirect('dashboard_evaluador')

    except (EvaluadorEvento.DoesNotExist, Evaluador.DoesNotExist):
        messages.error(request, "No estás inscrito como evaluador en este evento.")
        return redirect('dashboard_evaluador')

    # Obtener criterios del evento
    criterios = evento.criterios.all()
    peso_total_actual = sum(c.cri_peso for c in criterios if c.cri_peso is not None)

    return render(request, 'gestion_items_evaluador.html', {
        'evento': evento,
        'criterios': criterios,
        'peso_total_actual': peso_total_actual
    })

@login_required
@user_passes_test(es_evaluador, login_url='login')
def agregar_item(request, eve_id):
    evento = get_object_or_404(Evento, pk=eve_id)    
    if request.method == 'POST':
        descripcion = request.POST.get('descripcion')
        peso_str = request.POST.get('peso', '0')

        # Validaciones antes de crear el objeto
        errores = []

        if not descripcion or descripcion.strip() == '':
            errores.append("La descripción del criterio es obligatoria.")
        
        try:
            peso = float(peso_str)
            if peso <= 0:
                errores.append("El peso debe ser un número positivo.")
        except ValueError:
            errores.append("El peso debe ser un número válido.")

        # Calcular peso total actual
        peso_total_actual = sum(c.cri_peso for c in Criterio.objects.filter(cri_evento_fk=eve_id))

        # Verificar límite de 100%
        if peso_total_actual + peso > 100:
            errores.append('El peso total no puede exceder el 100%.')

        if errores:
            # Si hay errores, mostrarlos y volver al formulario
            messages.error(request, " ".join(errores))
            peso_restante = 100 - peso_total_actual
            return render(request, 'agregar_item_evaluador.html', {
                'evento': evento,
                'peso_total_actual': peso_total_actual,
                'peso_restante': peso_restante
            })

        # Si pasaron todas las validaciones, crear el criterio
        Criterio.objects.create(
            cri_descripcion=descripcion.strip(), # Limpiar espacios
            cri_peso=peso,
            cri_evento_fk=evento
        )
        messages.success(request, 'Ítem agregado correctamente.')
        return redirect('gestionar_items_evaluador', eve_id=eve_id)

    # Si es GET, mostrar formulario
    peso_total_actual = sum(c.cri_peso for c in Criterio.objects.filter(cri_evento_fk=eve_id))
    peso_restante = 100 - peso_total_actual
    return render(request, 'agregar_item_evaluador.html', {
        'evento': evento,
        'peso_total_actual': peso_total_actual,
        'peso_restante': peso_restante
    })

@login_required
@user_passes_test(es_evaluador, login_url='login')
def editar_item(request, criterio_id):
    criterio = get_object_or_404(Criterio, pk=criterio_id)
    peso_total_actual = sum(
        c.cri_peso for c in Criterio.objects.filter(cri_evento_fk=criterio.cri_evento_fk).exclude(pk=criterio.pk)
    )
    peso_restante = 100 - peso_total_actual
    if request.method == 'POST':
        descripcion = request.POST.get('descripcion')
        peso = float(request.POST.get('peso', 0))
        if peso_total_actual + peso > 100:
            messages.error(request, 'El peso total no puede exceder el 100%.')
            return redirect('gestionar_items_evaluador', eve_id=criterio.cri_evento_fk.pk)
        criterio.cri_descripcion = descripcion
        criterio.cri_peso = peso
        criterio.save()
        messages.success(request, 'Ítem editado correctamente.')
        return redirect('gestionar_items_evaluador', eve_id=criterio.cri_evento_fk.pk)
    return render(request, 'editar_item_evaluador.html', {
        'criterio': criterio,
        'peso_total_actual': peso_total_actual,
        'peso_restante': peso_restante,
    })

@login_required
@user_passes_test(es_evaluador, login_url='login')
def eliminar_item(request, criterio_id):
    criterio = get_object_or_404(Criterio, pk=criterio_id)
    evento_id = criterio.cri_evento_fk.pk
    criterio.delete()
    messages.success(request, 'Ítem eliminado correctamente.')
    return redirect('gestionar_items_evaluador', eve_id=evento_id)

@login_required
@user_passes_test(es_evaluador, login_url='login')
def instrumento_evaluacion(request, evento_id):
    evaluador = request.user.evaluador
    evento = get_object_or_404(Evento, pk=evento_id)
    inscrito = EvaluadorEvento.objects.filter(evaluador=evaluador, evento=evento).exists()
    if not inscrito:
        messages.warning(request, "No estás inscrito en este evento.")
        return redirect('dashboard_evaluador', evento_id=evento_id)
    criterios = Criterio.objects.filter(cri_evento_fk=evento)
    return render(request, 'instrumento_evaluacion_evaluador.html', {
        'evento': evento,
        'criterios': criterios,
    })

@login_required
@user_passes_test(es_evaluador, login_url='login')
def lista_participantes(request, eve_id):
    evento = get_object_or_404(Evento, pk=eve_id)
    try:
        evaluador = request.user.evaluador
    except Evaluador.DoesNotExist:
        messages.warning(request, "No estás registrado como evaluador.")
        return redirect('login_evaluador')

    if not evento.criterios.exists():
        messages.warning(request, "Este evento aún no tiene criterios definidos.")
        return redirect('gestionar_items_evaluador', eve_id=eve_id)

    from app_participantes.models import Proyecto

    # 1) Participantes aprobados (fila principal, con su proyecto principal si lo hay)
    participantes_evento = ParticipanteEvento.objects.filter(
        evento=evento,
        par_eve_estado='Aprobado'
    ).select_related('participante__usuario', 'proyecto')

    criterios_evento = Criterio.objects.filter(cri_evento_fk=evento)
    total_criterios = criterios_evento.count()

    participantes_data = {}

    # ---- base por participante ----
    for pe in participantes_evento:
        p = pe.participante
        if p.id not in participantes_data:
            participantes_data[p.id] = {
                'participante': p,
                'principal_proyecto': pe.proyecto,   # puede ser None
                'proyectos_extra': set(),
                'codigo': pe.codigo,
            }

    # ---- proyectos creados por cada participante (principal + extras) ----
    for p_id, data in list(participantes_data.items()):
        p = data['participante']

        creados = Proyecto.objects.filter(
            evento=evento,
            creador=p
        ).order_by('fecha_subida', 'id')

        principal = data['principal_proyecto']
        extras = set()

        for pr in creados:
            if principal and pr.id == principal.id:
                continue
            extras.add(pr)

        data['proyectos_extra'] = extras

    # ---- proyectos del líder para integrantes grupales ----
    for p_id, data in list(participantes_data.items()):
        codigo = data['codigo']
        if not codigo:
            continue

        lider_ids = Proyecto.objects.filter(
            evento=evento
        ).exclude(creador__isnull=True).values_list('creador_id', flat=True)

        pe_lider = ParticipanteEvento.objects.filter(
            evento=evento,
            codigo=codigo,
            participante_id__in=lider_ids
        ).first()

        if not pe_lider:
            continue

        proyectos_lider = Proyecto.objects.filter(
            evento=evento,
            creador_id=pe_lider.participante_id
        ).order_by('fecha_subida', 'id')

        principal = data['principal_proyecto']
        extras = data['proyectos_extra']

        for pr in proyectos_lider:
            if principal and pr.id == principal.id:
                continue
            extras.add(pr)

        data['proyectos_extra'] = extras

    # ---- lista final de proyectos por participante ----
    for data in participantes_data.values():
        proyectos = []
        if data['principal_proyecto']:
            proyectos.append(data['principal_proyecto'])
        extras_ordenados = sorted(
            list(data['proyectos_extra']),
            key=lambda pr: (pr.fecha_subida, pr.id)
        )
        proyectos.extend(extras_ordenados)
        data['proyectos'] = proyectos

    # ---- participantes calificados: tienen calificación en TODOS los criterios ----
    calificados_ids = set()

    for p_id, data in participantes_data.items():
        p = data['participante']
        num_califs = Calificacion.objects.filter(
            evaluador=evaluador,
            participante=p,
            criterio__cri_evento_fk=evento
        ).values('criterio_id').distinct().count()

        if num_califs == total_criterios and total_criterios > 0:
            calificados_ids.add(p_id)

    # Para grupales: si un integrante del código está calificado,
    # marcar a todos los del mismo código como calificados también.
    codigo_to_part_ids = {}
    for p_id, data in participantes_data.items():
        codigo = data['codigo']
        if not codigo:
            continue
        codigo_to_part_ids.setdefault(codigo, set()).add(p_id)

    for codigo, ids in codigo_to_part_ids.items():
        # si alguno del grupo está en calificados_ids, añadir el resto
        if any(pid in calificados_ids for pid in ids):
            calificados_ids.update(ids)

    # ---- proyectos calificados: cualquiera cuyo dueño esté calificado ----
    proyectos_calificados = set()
    for p_id, data in participantes_data.items():
        if p_id in calificados_ids:
            for pr in data['proyectos']:
                proyectos_calificados.add(pr.id)

    context = {
        'evento': evento,
        'participantes_data': participantes_data.values(),
        'proyectos_calificados': proyectos_calificados,
        'calificados_ids': calificados_ids,
    }
    return render(request, 'lista_participantes_evaluador.html', context)

@login_required
@user_passes_test(es_evaluador, login_url='login')
def calificar_participante(request, eve_id, participante_id):
    evento = get_object_or_404(Evento, pk=eve_id)
    try:
        evaluador = request.user.evaluador
        inscripcion = EvaluadorEvento.objects.get(evaluador=evaluador, evento=evento)
        if inscripcion.eva_eve_estado != 'Aprobado':
            messages.warning(request, "Tu inscripción como evaluador aún no ha sido aprobada para este evento.")
            return redirect('dashboard_evaluador')
    except (EvaluadorEvento.DoesNotExist, Evaluador.DoesNotExist):
        messages.error(request, "No estás inscrito como evaluador en este evento.")
        return redirect('dashboard_evaluador')

    participante = get_object_or_404(Participante, pk=participante_id)

    participacion = ParticipanteEvento.objects.filter(
        evento=evento,
        participante=participante,
        par_eve_estado='Aprobado'
    ).first()
    if not participacion:
        messages.error(request, "Este participante no está aprobado para ser calificado en este evento.")
        return redirect('lista_participantes_evaluador', eve_id=eve_id)

    criterios = Criterio.objects.filter(cri_evento_fk=evento)

    if request.method == "POST":
        for criterio in criterios:
            valor = request.POST.get(f"criterio_{criterio.cri_id}")
            observacion = request.POST.get(f"obs_{criterio.cri_id}", "").strip()

            try:
                valor_int = int(valor)
                if 1 <= valor_int <= 5:
                    calificacion, created = Calificacion.objects.get_or_create(
                        evaluador=evaluador,
                        criterio=criterio,
                        participante=participante,
                        defaults={'cal_valor': valor_int, 'cal_observacion': observacion or None}
                    )
                    if not created:
                        calificacion.cal_valor = valor_int
                        calificacion.cal_observacion = observacion or None
                    calificacion.save()
                else:
                    messages.error(request, f"El valor de {criterio.cri_descripcion} debe estar entre 1 y 5.")
                    return redirect(request.path)
            except (TypeError, ValueError):
                messages.error(request, f"Valor inválido para {criterio.cri_descripcion}.")
                return redirect(request.path)

        # Recalcular nota general del participante actual (1 decimal)
        nota = calcular_y_guardar_nota_general(participante, evento)

        from app_participantes.models import Proyecto

        # 1) Caso individual (sin código de grupo):
        #    aplicar la nota a TODOS los proyectos creados por este participante en el evento.
        if not participacion.codigo:
            proyectos_participante = Proyecto.objects.filter(
                evento=evento,
                creador=participante
            )
            for proyecto in proyectos_participante:
                proyecto.pro_valor = round(nota, 1)
                proyecto.save()

        else:
            # 2) Caso grupal: un solo integrante calificado basta.

            # a) Identificar al líder (creador de proyectos en este evento dentro del grupo).
            lider_ids = Proyecto.objects.filter(
                evento=evento
            ).exclude(creador__isnull=True).values_list('creador_id', flat=True)

            pe_lider = ParticipanteEvento.objects.filter(
                evento=evento,
                codigo=participacion.codigo,
                participante_id__in=lider_ids
            ).first()

            # a1) Participantes del grupo (mismo código, aprobados)
            integrantes_grupo = ParticipanteEvento.objects.filter(
                evento=evento,
                codigo=participacion.codigo,
                par_eve_estado='Aprobado'
            ).select_related('participante')

            for pe in integrantes_grupo:
                pe.par_eve_valor = round(nota, 1)
                pe.save()
                # Recalcular y guardar nota general individual según calificaciones existentes
                calcular_y_guardar_nota_general(pe.participante, evento)

            # a2) Proyectos del grupo: todos los proyectos del líder en este evento
            if pe_lider:
                proyectos_grupo = Proyecto.objects.filter(
                    evento=evento,
                    creador_id=pe_lider.participante_id
                )
                for proyecto in proyectos_grupo:
                    proyecto.pro_valor = round(nota, 1)
                    proyecto.save()

        messages.success(request, "Calificaciones guardadas exitosamente.")
        return redirect('lista_participantes_evaluador', eve_id=eve_id)

    return render(request, 'formulario_calificacion.html', {
        'criterios': criterios,
        'participante': participante,
        'evento': evento,
    })

@login_required
@user_passes_test(es_evaluador, login_url='login')
def ver_tabla_posiciones(request, eve_id):
    evento = get_object_or_404(Evento, pk=eve_id)
    try:
        evaluador = request.user.evaluador
        inscripcion = EvaluadorEvento.objects.get(evaluador=evaluador, evento=evento)
        if inscripcion.eva_eve_estado != 'Aprobado':
            messages.warning(request, "Tu inscripción a este evento aún no ha sido aprobada.")
            return redirect('dashboard_evaluador')
    except (EvaluadorEvento.DoesNotExist, Evaluador.DoesNotExist):
        messages.error(request, "No estás inscrito en este evento.")
        return redirect('dashboard_evaluador')

    criterios = Criterio.objects.filter(cri_evento_fk=evento)
    peso_total = sum(c.cri_peso for c in criterios) or 1

    from app_participantes.models import Proyecto

    participantes_evento = ParticipanteEvento.objects.filter(
        evento=evento,
        par_eve_estado='Aprobado'
    ).select_related('participante__usuario', 'proyecto')

    datos = {}

    for pe in participantes_evento:
        p = pe.participante
        if p.id not in datos:
            if pe.par_eve_valor is not None:
                puntaje_ponderado = pe.par_eve_valor
            else:
                calificaciones = Calificacion.objects.filter(
                    participante=p,
                    criterio__cri_evento_fk=evento
                ).select_related('criterio')
                evaluadores_ids = set(c.evaluador_id for c in calificaciones)
                num_evaluadores = len(evaluadores_ids)
                if num_evaluadores > 0:
                    puntaje_ponderado = sum(
                        c.cal_valor * c.criterio.cri_peso for c in calificaciones
                    ) / (peso_total * num_evaluadores)
                    puntaje_ponderado = round(puntaje_ponderado, 2)
                    pe.par_eve_valor = puntaje_ponderado
                    pe.save()
                else:
                    puntaje_ponderado = 0

            datos[p.id] = {
                'participante': p,
                'puntaje': puntaje_ponderado,
                'principal_proyecto': pe.proyecto,
                'proyectos_extra': set(),
                'codigo': pe.codigo,
            }

    for p_id, info in list(datos.items()):
        p = info['participante']
        creados = Proyecto.objects.filter(
            evento=evento,
            creador=p
        ).order_by('fecha_subida', 'id')

        principal = info['principal_proyecto']
        extras = set()
        for pr in creados:
            if principal and pr.id == principal.id:
                continue
            extras.add(pr)

        info['proyectos_extra'] = extras

    for p_id, info in list(datos.items()):
        codigo = info['codigo']
        if not codigo:
            continue

        lider_ids = Proyecto.objects.filter(
            evento=evento
        ).exclude(creador__isnull=True).values_list('creador_id', flat=True)

        pe_lider = ParticipanteEvento.objects.filter(
            evento=evento,
            codigo=codigo,
            participante_id__in=lider_ids
        ).first()
        if not pe_lider:
            continue

        proyectos_lider = Proyecto.objects.filter(
            evento=evento,
            creador_id=pe_lider.participante_id
        ).order_by('fecha_subida', 'id')

        principal = info['principal_proyecto']
        extras = info['proyectos_extra']
        for pr in proyectos_lider:
            if principal and pr.id == principal.id:
                continue
            extras.add(pr)
        info['proyectos_extra'] = extras

    posiciones = []
    for info in datos.values():
        proyectos = []
        if info['principal_proyecto']:
            proyectos.append(info['principal_proyecto'])
        extras_ordenados = sorted(
            list(info['proyectos_extra']),
            key=lambda pr: (pr.fecha_subida, pr.id)
        )
        proyectos.extend(extras_ordenados)
        posiciones.append({
            'participante': info['participante'],
            'puntaje': info['puntaje'],
            'proyectos': proyectos,
            'codigo': info['codigo'],
        })

    posiciones.sort(key=lambda x: x['puntaje'], reverse=True)

    return render(request, 'tabla_posiciones_evaluador.html', {
        'evento': evento,
        'posiciones': posiciones
    })

@login_required
@user_passes_test(es_evaluador, login_url='login')
def descargar_tabla_posiciones_pdf(request, eve_id):
    evento = get_object_or_404(Evento, pk=eve_id)
    try:
        evaluador = request.user.evaluador
        inscripcion = EvaluadorEvento.objects.get(evaluador=evaluador, evento=evento)
        if inscripcion.eva_eve_estado != 'Aprobado':
            messages.warning(request, "Tu inscripción a este evento aún no ha sido aprobada.")
            return redirect('dashboard_evaluador')
    except (EvaluadorEvento.DoesNotExist, Evaluador.DoesNotExist):
        messages.error(request, "No estás inscrito en este evento.")
        return redirect('dashboard_evaluador')

    participantes_evento = ParticipanteEvento.objects.filter(
        evento=evento,
        par_eve_estado='Aprobado',
        par_eve_valor__isnull=False
    ).select_related('participante__usuario', 'proyecto')

    from app_participantes.models import Proyecto

    datos = {}
    for pe in participantes_evento:
        p = pe.participante
        if p.id not in datos:
            datos[p.id] = {
                'participante': p,
                'puntaje': pe.par_eve_valor,
                'principal_proyecto': pe.proyecto,
                'proyectos_extra': set(),
                'codigo': pe.codigo,
            }

    for p_id, info in list(datos.items()):
        p = info['participante']
        creados = Proyecto.objects.filter(
            evento=evento,
            creador=p
        ).order_by('fecha_subida', 'id')

        principal = info['principal_proyecto']
        extras = set()
        for pr in creados:
            if principal and pr.id == principal.id:
                continue
            extras.add(pr)
        info['proyectos_extra'] = extras

    for p_id, info in list(datos.items()):
        codigo = info['codigo']
        if not codigo:
            continue
        lider_ids = Proyecto.objects.filter(
            evento=evento
        ).exclude(creador__isnull=True).values_list('creador_id', flat=True)

        pe_lider = ParticipanteEvento.objects.filter(
            evento=evento,
            codigo=codigo,
            participante_id__in=lider_ids
        ).first()
        if not pe_lider:
            continue

        proyectos_lider = Proyecto.objects.filter(
            evento=evento,
            creador_id=pe_lider.participante_id
        ).order_by('fecha_subida', 'id')

        principal = info['principal_proyecto']
        extras = info['proyectos_extra']
        for pr in proyectos_lider:
            if principal and pr.id == principal.id:
                continue
            extras.add(pr)
        info['proyectos_extra'] = extras

    posiciones = []
    for info in datos.values():
        proyectos = []
        if info['principal_proyecto']:
            proyectos.append(info['principal_proyecto'])
        extras_ordenados = sorted(
            list(info['proyectos_extra']),
            key=lambda pr: (pr.fecha_subida, pr.id)
        )
        proyectos.extend(extras_ordenados)
        posiciones.append({
            'participante': info['participante'],
            'puntaje': info['puntaje'],
            'proyectos': proyectos,
            'codigo': info['codigo'],
        })

    posiciones.sort(key=lambda x: x['puntaje'], reverse=True)

    # --- PDF landscape ---
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="tabla_posiciones_{evento.eve_nombre}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=landscape(letter))
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1,
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
        alignment=1,
    )

    elements.append(Paragraph("Tabla de Posiciones", title_style))
    elements.append(Paragraph(f"Evento: {evento.eve_nombre}", subtitle_style))
    elements.append(Spacer(1, 20))

    data = [["Posición", "Nombre del Participante", "Correo",
             "Tipo de participación", "Proyectos", "Puntaje"]]

    for i, pos in enumerate(posiciones, start=1):
        p = pos['participante']
        nombre = f"{p.usuario.first_name} {p.usuario.last_name}"
        correo = p.usuario.email
        tipo = "Grupal" if pos['codigo'] else "Individual"
        if pos['proyectos']:
            nombres_proyectos = " / ".join(pr.titulo for pr in pos['proyectos'])
        else:
            nombres_proyectos = "Individual"
        proyectos_par = Paragraph(nombres_proyectos, styles['Normal'])
        puntaje = f"{pos['puntaje']:.1f}"

        data.append([str(i), nombre, correo, tipo, proyectos_par, puntaje])

    col_widths = [
        0.8*inch,
        2.1*inch,
        2.0*inch,
        1.6*inch,
        3.0*inch,
        0.7*inch,
    ]

    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWHEIGHT', (0, 1), (-1, -1), 25),
    ]))

    elements.append(table)
    doc.build(elements)
    return response

@login_required
@user_passes_test(es_evaluador, login_url='login')
def informacion_detallada(request, eve_id):
    evaluador = request.user.evaluador
    evento = get_object_or_404(Evento, pk=eve_id)

    try:
        inscripcion = EvaluadorEvento.objects.get(evaluador=evaluador, evento=evento)
        if inscripcion.eva_eve_estado != 'Aprobado':
            messages.warning(request, "No tienes acceso a este evento porque tu inscripción no está aprobada.")
            return redirect('dashboard_evaluador')
    except (EvaluadorEvento.DoesNotExist, Evaluador.DoesNotExist):
        messages.error(request, "No estás inscrito en este evento.")
        return redirect('dashboard_evaluador')

    criterios = Criterio.objects.filter(cri_evento_fk=evento)
    total_criterios = criterios.count()

    participantes_evento = ParticipanteEvento.objects.filter(
        evento=evento,
        par_eve_estado='Aprobado'
    ).select_related('participante__usuario')

    participantes_info = []

    for pe in participantes_evento:
        participante = pe.participante

        # --- determinar participante de referencia para calificaciones grupales ---
        participante_referencia = participante
        if pe.codigo:
            # buscar cualquier integrante del mismo código con calificaciones de este evaluador
            pe_grupo = ParticipanteEvento.objects.filter(
                evento=evento,
                codigo=pe.codigo
            ).select_related('participante')

            ref_encontrado = None
            for pe_g in pe_grupo:
                if Calificacion.objects.filter(
                    evaluador=evaluador,
                    participante=pe_g.participante,
                    criterio__cri_evento_fk=evento
                ).exists():
                    ref_encontrado = pe_g.participante
                    break

            if ref_encontrado:
                participante_referencia = ref_encontrado

        # --- calificaciones que este evaluador ha dado al participante/grupo ---
        calificaciones_actual = Calificacion.objects.filter(
            evaluador=evaluador,
            participante=participante_referencia,
            criterio__cri_evento_fk=evento
        ).select_related('criterio')

        total_aporte = 0
        calificaciones_lista = []

        for c in calificaciones_actual:
            aporte = (c.cal_valor * c.criterio.cri_peso) / 100
            total_aporte += aporte
            calificaciones_lista.append({
                'criterio': c.criterio,
                'cal_valor': c.cal_valor,
                'aporte': round(aporte, 2),
                'observacion': c.cal_observacion,
            })

        evaluado = len(calificaciones_lista) == total_criterios
        promedio_ponderado = round(total_aporte, 2) if calificaciones_lista else None

        participantes_info.append({
            'participante': participante,
            'evaluado': evaluado,
            'promedio_ponderado': promedio_ponderado,
            'calificaciones': calificaciones_lista,
            'evaluados': len(calificaciones_lista),
            'total_criterios': total_criterios,
        })

    context = {
        'evaluador': evaluador,
        'evento': evento,
        'criterios': criterios,
        'participantes_info': participantes_info,
    }
    return render(request, 'info_detallada_evaluador.html', context)

@login_required
@user_passes_test(es_evaluador, login_url='login')
def cancelar_inscripcion_evaluador(request, evento_id):
    evaluador_usuario = request.user
    evento = get_object_or_404(Evento, pk=evento_id)
    evaluador = evaluador_usuario.evaluador
    inscripcion = get_object_or_404(EvaluadorEvento, evaluador=evaluador, evento=evento)
    if inscripcion.eva_eve_estado != "Pendiente":
        messages.error(request, "No puedes cancelar la inscripción porque ya fue aprobada.")
        return redirect('dashboard_evaluador')
    if request.method == 'POST':
        inscripcion.delete()
        otros_eventos = EvaluadorEvento.objects.filter(evaluador=evaluador).count()
        if otros_eventos == 0:
            Evaluador.objects.filter(usuario=evaluador_usuario).delete()
            usuario_username = evaluador_usuario.username
            evaluador_usuario.delete()
            messages.success(request, f"Se canceló tu inscripción y se eliminó el usuario '{usuario_username}' porque no estaba en otros eventos.")
            return redirect('login')
        messages.success(request, "Inscripción cancelada con éxito.")
        return redirect('dashboard_evaluador')
    return render(request, 'confirmar_cancelacion.html', {
        'evento': evento
    })

@login_required
@user_passes_test(es_evaluador, login_url='login')
def modificar_inscripcion_evaluador(request, evento_id):
    usuario = request.user
    evento = get_object_or_404(Evento, pk=evento_id)
    evaluador = usuario.evaluador
    inscripcion = get_object_or_404(EvaluadorEvento, evaluador=evaluador, evento=evento)
    if inscripcion.eva_eve_estado != "Pendiente":
        messages.error(request, "Solo puedes modificar la inscripción si está en estado Pendiente.")
        return redirect('dashboard_evaluador')
    if request.method == "POST":
        usuario.first_name = request.POST.get("eva_nombres")
        usuario.last_name = request.POST.get("eva_apellidos")
        usuario.email = request.POST.get("eva_correo")
        usuario.telefono = request.POST.get("eva_telefono")
        usuario.documento = request.POST.get("eva_id")
        usuario.save()
        archivo = request.FILES.get('documentacion')
        if archivo:
            inscripcion.eva_eve_qr = archivo
            inscripcion.save()
        messages.success(request, "Información actualizada correctamente.")
        return redirect('dashboard_evaluador')
    return render(request, 'modificar_inscripcion.html', {
        'evento': evento,
        'usuario': usuario,
        'inscripcion': inscripcion
    })

@login_required
@user_passes_test(es_evaluador, login_url='login')
def ver_evento_completo(request, evento_id):
    request.user.evaluador
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

    return render(request, 'evento_completo_evaluador.html', {'evento': evento_data})

@login_required
@user_passes_test(es_evaluador, login_url='login')
def descargar_memorias_evaluador(request, evento_id):
    """Vista para descargar las memorias de un evento como evaluador"""
    evento = get_object_or_404(Evento, eve_id=evento_id)
    evaluador = request.user.evaluador
    
    # Verificar que el evaluador esté inscrito en el evento
    inscripcion = get_object_or_404(EvaluadorEvento, evaluador=evaluador, evento=evento)
    
    # Solo permitir si el estado no es "Pendiente"
    if inscripcion.eva_eve_estado == 'Pendiente':
        messages.error(request, "No puedes descargar memorias mientras tu inscripción esté pendiente.")
        return redirect('dashboard_evaluador')
    
    # Verificar que el archivo de memorias exista
    if not evento.eve_memorias:
        messages.error(request, "Este evento no tiene memorias disponibles para descargar.")
        return redirect('dashboard_evaluador')
    
    # Verificar que el archivo físico exista
    if not os.path.exists(evento.eve_memorias.path):
        messages.error(request, "El archivo de memorias no se encuentra disponible.")
        return redirect('dashboard_evaluador')
    
    try:
        response = FileResponse(
            open(evento.eve_memorias.path, 'rb'),
            as_attachment=True,
            filename=f"Memorias_{evento.eve_nombre}_{evento.eve_memorias.name.split('/')[-1]}"
        )
        return response
    except Exception as e:
        messages.error(request, "Error al descargar el archivo de memorias.")
        return redirect('dashboard_evaluador')


@login_required
@user_passes_test(es_evaluador, login_url='login')
def descargar_informacion_tecnica_evaluador(request, evento_id):
    evaluador = request.user.evaluador
    evento = get_object_or_404(Evento, pk=evento_id)
    
    # Verificar que el evaluador esté inscrito y aprobado
    inscripcion = get_object_or_404(
        EvaluadorEvento, 
        evaluador=evaluador, 
        evento=evento,
        eva_eve_estado='Aprobado'
    )
    
    if not evento.eve_informacion_tecnica:
        messages.error(request, "Este evento no tiene información técnica disponible.")
        return redirect('dashboard_evaluador')
    
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
        return redirect('dashboard_evaluador')
    
@login_required
@user_passes_test(es_evaluador, login_url='login')
@login_required
@user_passes_test(es_evaluador, login_url='login')
def ver_perfil_evaluador(request, evento_id):
    evaluador = request.user.evaluador  # Obtener el Evaluador asociado al usuario actual
    evaluador_evento = get_object_or_404(EvaluadorEvento, evento_id=evento_id, evaluador=evaluador)
    
    # Acceder al usuario asociado al evaluador
    usuario = evaluador.usuario
    
    return render(request, 'perfil_evaluador.html', {
        'evento': evaluador_evento.evento,
        'evaluador': evaluador_evento,
        'usuario': usuario,  # Agregar el usuario al contexto
        'qr_url': evaluador_evento.eva_eve_qr.url if evaluador_evento.eva_eve_qr else None,
    })

@login_required
@user_passes_test(es_evaluador, login_url='login')
def cargar_programacion_tecnica(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    if request.method == 'POST':
        archivo = request.FILES.get('programacion_tecnica')
        if archivo:
            evento.eve_informacion_tecnica = archivo  # ← usar campo real
            evento.save()
            messages.success(request, "Programación técnica cargada correctamente.")
        else:
            messages.error(request, "Debes seleccionar un archivo.")
        return redirect('dashboard_evaluador')
    return render(request, 'cargar_programacion_tecnica.html', {'evento': evento})

def manual_evaluador(request):
    """
    Sirve el manual del Evaluador en formato PDF.
    """
    ruta_manual = os.path.join(settings.MEDIA_ROOT, "manuales", "MANUAL_EVALUADOR_SISTEMA_EVENTSOFT.pdf")
    if os.path.exists(ruta_manual):
        return FileResponse(open(ruta_manual, "rb"), content_type="application/pdf")
    raise Http404("Manual no encontrado")