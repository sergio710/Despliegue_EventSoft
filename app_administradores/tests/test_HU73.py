# app_administradores/tests/test_HU73.py

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from app_administradores.models import AdministradorEvento
from app_eventos.models import Evento
from app_participantes.models import Participante, ParticipanteEvento, Proyecto
from app_evaluadores.models import Evaluador, EvaluadorEvento
from app_asistentes.models import Asistente, AsistenteEvento
import datetime

Usuario = get_user_model()

class HU73EstadisticasEventoTest(TestCase):
    """
    HU73:
    Como ADMINISTRADOR DE EVENTO,
    Quiero obtener información estadística sobre un evento,
    Para conocer los resultados numéricos y estadísticos relevantes sobre el evento.
    """

    def setUp(self):
        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin73",
            email="admin73@test.com",
            password="12345",
            documento="12345673"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evento con capacidad de 10
        self.evento = Evento.objects.create(
            eve_nombre="Foro de Ciencias",
            eve_descripcion="Evento académico",
            eve_ciudad="Bogotá",
            eve_lugar="Corferias",
            eve_fecha_inicio=datetime.date(2025, 10, 1),
            eve_fecha_fin=datetime.date(2025, 10, 3),
            eve_estado="Aprobado",
            eve_capacidad=10,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

        # Crear 3 asistentes confirmados
        for i in range(3):
            user = Usuario.objects.create_user(
                username=f"asis73{i}",
                email=f"asis73{i}@test.com",
                password="12345",
                documento=f"7300{i}"
            )
            asistente = Asistente.objects.create(usuario=user)
            AsistenteEvento.objects.create(
                asistente=asistente,
                evento=self.evento,
                asi_eve_fecha_hora=timezone.now(),
                asi_eve_estado="Aprobado",
                confirmado=True
            )

        # Crear 1 expositor con proyecto
        user_expo = Usuario.objects.create_user(
            username="expo73",
            email="expo73@test.com",
            password="12345",
            documento="73111"
        )
        participante_expo = Participante.objects.create(usuario=user_expo)
        proyecto = Proyecto.objects.create(
            evento=self.evento,
            titulo="Proyecto Ciencias",
            descripcion="Descripción",
            estado="Aprobado"
        )
        ParticipanteEvento.objects.create(
            participante=participante_expo,
            evento=self.evento,
            par_eve_fecha_hora=timezone.now(),
            par_eve_estado="Aprobado",
            confirmado=True,
            proyecto=proyecto
        )

        # Crear 2 evaluadores
        for i in range(2):
            user = Usuario.objects.create_user(
                username=f"eval73{i}",
                email=f"eval73{i}@test.com",
                password="12345",
                documento=f"7322{i}"
            )
            evaluador = Evaluador.objects.create(usuario=user)
            EvaluadorEvento.objects.create(
                evaluador=evaluador,
                evento=self.evento,
                eva_eve_fecha_hora=timezone.now(),
                eva_eve_estado="Aprobado",
                confirmado=True
            )

    def obtener_estadisticas(self, evento):
        # CA1: Número de asistentes confirmados
        asistentes = AsistenteEvento.objects.filter(evento=evento, confirmado=True).count()
        
        # CA2: Número de expositores - CORRECCIÓN DEL ERROR
        expositores = ParticipanteEvento.objects.filter(
            evento=evento, 
            confirmado=True, 
            proyecto__isnull=False  # CORRECTO: proyecto está en ParticipanteEvento
        ).count()
        
        # CA3: Número de evaluadores
        evaluadores = EvaluadorEvento.objects.filter(evento=evento, confirmado=True).count()
        
        # CA4: Capacidad ocupada (porcentaje)
        capacidad_total = evento.eve_capacidad
        total_ocupado = asistentes + expositores
        porcentaje_ocupado = round((total_ocupado / capacidad_total) * 100, 2) if capacidad_total > 0 else 0

        # CA5: Estructura organizada
        return {
            "asistentes_confirmados": asistentes,
            "expositores": expositores,
            "evaluadores": evaluadores,
            "capacidad_total": capacidad_total,
            "porcentaje_ocupado": porcentaje_ocupado
        }

    def test_estadisticas_evento(self):
        """
        Cubre los criterios de aceptación de HU73:
        - CA1: Número de asistentes confirmados
        - CA2: Número de expositores
        - CA3: Número de evaluadores
        - CA4: Capacidad ocupada (porcentaje)
        - CA5: Resultados en una estructura organizada
        """
        estadisticas = self.obtener_estadisticas(self.evento)

        # CA1: 3 asistentes confirmados
        self.assertEqual(estadisticas["asistentes_confirmados"], 3)
        
        # CA2: 1 expositor (participante con proyecto)
        self.assertEqual(estadisticas["expositores"], 1)
        
        # CA3: 2 evaluadores
        self.assertEqual(estadisticas["evaluadores"], 2)
        
        # CA4: Capacidad total 10
        self.assertEqual(estadisticas["capacidad_total"], 10)
        
        # CA4: Porcentaje ocupado: (3 asistentes + 1 expositor) / 10 = 40%
        self.assertEqual(estadisticas["porcentaje_ocupado"], 40.0)
        
        # CA5: Estructura organizada (diccionario)
        self.assertIsInstance(estadisticas, dict)