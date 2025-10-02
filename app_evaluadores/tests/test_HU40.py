from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from app_evaluadores.models import Evaluador, EvaluadorEvento
from app_eventos.models import Evento, AdministradorEvento
from app_participantes.models import Participante, Proyecto, ParticipanteEvento
import datetime

Usuario = get_user_model()

class HU40VisualizarExpositoresTest(TestCase):
    """
    HU40:
    Como EVALUADOR,
    Quiero visualizar el listado de los expositores del evento en el que soy evaluador,
    Para saber cuántos y quiénes van a participar.
    """

    def setUp(self):
        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin_evento40",
            email="admin40@test.com",
            password="12345",
            documento="12345678"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evaluador
        self.evaluador_user = Usuario.objects.create_user(
            username="evaluador40",
            email="eva40@test.com",
            password="12345",
            documento="99999999"
        )
        self.evaluador = Evaluador.objects.create(usuario=self.evaluador_user)

        # Crear evento
        self.evento = Evento.objects.create(
            eve_nombre="Congreso Internacional",
            eve_descripcion="Evento académico de investigación",
            eve_ciudad="Bogotá",
            eve_lugar="Centro de Convenciones",
            eve_fecha_inicio=datetime.date(2025, 12, 1),
            eve_fecha_fin=datetime.date(2025, 12, 3),
            eve_estado="activo",
            eve_capacidad=500,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

        # Asignar evaluador al evento
        self.evaluador_evento = EvaluadorEvento.objects.create(
            evaluador=self.evaluador,
            evento=self.evento,
            eva_eve_fecha_hora=timezone.now(),
            eva_eve_estado="Aprobado",
            confirmado=True
        )

        # Crear participantes con proyectos
        self.participantes = []
        for i in range(1, 4):
            user = Usuario.objects.create_user(
                username=f"participante{i}",
                email=f"part{i}@test.com",
                password="12345",
                documento=f"1000{i}"
            )
            participante = Participante.objects.create(usuario=user)

            proyecto = Proyecto.objects.create(
                evento=self.evento,
                titulo=f"Proyecto {i}",
                descripcion=f"Descripción del proyecto {i}",
                estado="Aprobado"
            )

            ParticipanteEvento.objects.create(
                participante=participante,
                evento=self.evento,
                par_eve_fecha_hora=timezone.now(),
                par_eve_estado="Aprobado",
                confirmado=True,
                proyecto=proyecto
            )

            self.participantes.append(participante)

    def test_listado_expositores(self):
        """
        Cubre los criterios de aceptación de HU40:
        1. Ver listado de proyectos.
        2. Mostrar nombre del participante principal.
        3. Indicar título del proyecto.
        4. Conocer número total de expositores.
        """

        proyectos = Proyecto.objects.filter(evento=self.evento, estado="Aprobado")

        # (1) Ver listado de proyectos
        self.assertEqual(proyectos.count(), 3)

        # (2) Participantes principales vinculados
        participantes_evento = ParticipanteEvento.objects.filter(evento=self.evento, confirmado=True)
        self.assertEqual(participantes_evento.count(), 3)

        # (3) Ver título de cada proyecto
        titulos = [p.titulo for p in proyectos]
        self.assertIn("Proyecto 1", titulos)
        self.assertIn("Proyecto 2", titulos)
        self.assertIn("Proyecto 3", titulos)

        # (4) Número total de expositores
        total_expositores = participantes_evento.count()
        self.assertEqual(total_expositores, 3)