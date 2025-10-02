# app_administradores/tests/test_HU77.py

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from app_usuarios.models import Usuario, Rol, RolUsuario
from app_administradores.models import AdministradorEvento
from app_eventos.models import Evento
from app_participantes.models import Participante, ParticipanteEvento, Proyecto
from app_evaluadores.models import Evaluador, EvaluadorEvento, Criterio, Calificacion

class HU77TablaPosicionesTest(TestCase):
    """
    HU77: Como ADMINISTRADOR DE EVENTO, Quiero Visualizar y DESCARGAR la tabla 
    de posiciones con los puntajes obtenidos por todos los expositores del evento, 
    Para identificar a los ganadores y el desempeño general de los expositores.
    """

    def setUp(self):
        self.client = Client()
        
        # Crear roles
        self.rol_admin = Rol.objects.create(nombre='administrador_evento')
        self.rol_participante = Rol.objects.create(nombre='participante')
        self.rol_evaluador = Rol.objects.create(nombre='evaluador')

        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin77",
            email="admin77@test.com",
            password="password123",
            documento="12345677"
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_admin)
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evento aprobado
        self.evento = Evento.objects.create(
            eve_nombre="Evento Tabla Posiciones",
            eve_descripcion="Evento para testing tabla posiciones",
            eve_ciudad="Test City",
            eve_lugar="Test Place",
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=2),
            eve_estado="Aprobado",
            eve_capacidad=50,
            eve_tienecosto="No",
            eve_administrador_fk=self.admin
        )

        # Crear proyecto para los expositores
        self.proyecto = Proyecto.objects.create(
            evento=self.evento,
            titulo="Proyecto Competencia",
            descripcion="Proyecto para competir",
            estado="Aprobado"
        )

        # Crear 3 expositores con diferentes puntajes
        self.expositores = []
        puntajes = [95.5, 87.2, 82.0]  # Para crear ranking
        nombres = ["Expositor A", "Expositor B", "Expositor C"]
        
        for i, (nombre, puntaje) in enumerate(zip(nombres, puntajes)):
            user = Usuario.objects.create_user(
                username=f"expo{i}",
                email=f"expo{i}@test.com",
                password="password123",
                documento=f"7700{i}",
                first_name=nombre.split()[0],
                last_name=nombre.split()[1]
            )
            RolUsuario.objects.create(usuario=user, rol=self.rol_participante)
            participante = Participante.objects.create(usuario=user)
            
            participante_evento = ParticipanteEvento.objects.create(
                participante=participante,
                evento=self.evento,
                par_eve_fecha_hora=timezone.now(),
                par_eve_estado="Aprobado",
                confirmado=True,
                proyecto=self.proyecto,
                par_eve_valor=puntaje  # Puntaje ya calculado
            )
            
            self.expositores.append({
                'user': user,
                'participante': participante,
                'participante_evento': participante_evento,
                'puntaje': puntaje
            })

        # URLs
        self.url_tabla_posiciones = reverse('tabla_posiciones_administrador', args=[self.evento.pk])
        self.url_descargar_pdf = reverse('descargar_tabla_posiciones_pdf_admin', args=[self.evento.pk])

        # Login
        self.client.force_login(self.admin_user)
        session = self.client.session
        session['rol_sesion'] = 'administrador_evento'
        session.save()

    def test_hu77_tabla_posiciones_completa(self):
        """
        Prueba los 5 criterios de aceptación de HU77:
        CA1: Acceder a visualización de tabla de posiciones
        CA2: Mostrar información completa de expositores
        CA3: Ordenar por puntaje descendente (ranking)
        CA4: Descargar tabla en formato PDF
        CA5: Solo eventos aprobados con expositores calificados
        """
        
        # CA1: Acceder a visualización de tabla de posiciones
        response_tabla = self.client.get(self.url_tabla_posiciones)
        self.assertEqual(response_tabla.status_code, 200, "CA1: Debe acceder a tabla de posiciones")
        
        self.assertIn('posiciones', response_tabla.context, "CA1: Debe incluir datos de posiciones")
        posiciones = response_tabla.context['posiciones']
        self.assertEqual(len(posiciones), 3, "CA1: Debe mostrar 3 expositores")

        # CA2: Mostrar información completa de cada expositor
        # Verificar que aparecen nombres de expositores
        self.assertContains(response_tabla, "Expositor A", msg_prefix="CA2: Debe mostrar nombre expositor A")
        self.assertContains(response_tabla, "Expositor B", msg_prefix="CA2: Debe mostrar nombre expositor B")
        self.assertContains(response_tabla, "Expositor C", msg_prefix="CA2: Debe mostrar nombre expositor C")
        
        # Verificar que aparecen emails
        self.assertContains(response_tabla, "expo0@test.com", msg_prefix="CA2: Debe mostrar email")
        
        # Verificar que aparecen puntajes
        self.assertContains(response_tabla, "95,5", msg_prefix="CA2: Debe mostrar puntaje más alto")
        self.assertContains(response_tabla, "87,2", msg_prefix="CA2: Debe mostrar puntaje medio")
        self.assertContains(response_tabla, "82", msg_prefix="CA2: Debe mostrar puntaje más bajo")
        
        # Verificar que aparece información del proyecto
        self.assertContains(response_tabla, "Proyecto Competencia", msg_prefix="CA2: Debe mostrar proyecto asociado")

        # CA3: Verificar ordenamiento por puntaje descendente
        posiciones_ordenadas = response_tabla.context['posiciones']
        
        # El primer expositor debe tener el puntaje más alto (95.5)
        primer_lugar = posiciones_ordenadas[0]
        self.assertEqual(primer_lugar['puntaje'], 95.5, "CA3: Primer lugar debe tener puntaje 95.5")
        
        # El segundo expositor debe tener puntaje intermedio (87.2)  
        segundo_lugar = posiciones_ordenadas[1]
        self.assertEqual(segundo_lugar['puntaje'], 87.2, "CA3: Segundo lugar debe tener puntaje 87.2")
        
        # El tercer expositor debe tener puntaje más bajo (82.0)
        tercer_lugar = posiciones_ordenadas[2]
        self.assertEqual(tercer_lugar['puntaje'], 82.0, "CA3: Tercer lugar debe tener puntaje 82.0")
        
        # Verificar ordenamiento correcto
        for i in range(len(posiciones_ordenadas) - 1):
            puntaje_actual = posiciones_ordenadas[i]['puntaje']
            puntaje_siguiente = posiciones_ordenadas[i + 1]['puntaje']
            self.assertGreaterEqual(puntaje_actual, puntaje_siguiente, 
                                   "CA3: Puntajes deben estar ordenados descendentemente")

        # CA4: Descargar tabla en formato PDF
        response_pdf = self.client.get(self.url_descargar_pdf)
        self.assertEqual(response_pdf.status_code, 200, "CA4: Debe poder descargar PDF")
        self.assertEqual(response_pdf['Content-Type'], 'application/pdf', "CA4: Debe ser archivo PDF")
        self.assertIn('attachment', response_pdf.get('Content-Disposition', ''), "CA4: Debe ser descarga")

        # CA5: Solo eventos aprobados con expositores calificados
        # Crear evento sin expositores calificados
        evento_sin_calificados = Evento.objects.create(
            eve_nombre="Evento Sin Calificados",
            eve_descripcion="Sin expositores calificados",
            eve_ciudad="Test",
            eve_lugar="Test",
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado="Aprobado",
            eve_capacidad=30,
            eve_tienecosto="No",
            eve_administrador_fk=self.admin
        )
        
        url_tabla_sin_calificados = reverse('tabla_posiciones_administrador', args=[evento_sin_calificados.pk])
        response_sin_calificados = self.client.get(url_tabla_sin_calificados)
        
        # Tu vista debe manejar eventos sin expositores calificados
        self.assertEqual(response_sin_calificados.status_code, 200, "CA5: Debe manejar evento sin calificados")
        
        if 'posiciones' in response_sin_calificados.context:
            posiciones_vacias = response_sin_calificados.context['posiciones']
            self.assertEqual(len(posiciones_vacias), 0, "CA5: No debe haber posiciones en evento sin calificados")

        # Verificar estructura final de la tabla
        self.assertIn('evento', response_tabla.context, "Debe incluir información del evento")
        evento_contexto = response_tabla.context['evento']
        self.assertEqual(evento_contexto.eve_nombre, "Evento Tabla Posiciones", "Debe mostrar evento correcto")
        
        return {
            'total_expositores': len(posiciones_ordenadas),
            'primer_lugar_puntaje': posiciones_ordenadas[0]['puntaje'],
            'ordenamiento_correcto': all(
                posiciones_ordenadas[i]['puntaje'] >= posiciones_ordenadas[i+1]['puntaje'] 
                for i in range(len(posiciones_ordenadas)-1)
            ),
            'pdf_disponible': response_pdf.status_code == 200,
            'evento_aprobado': self.evento.eve_estado == "Aprobado"
        }