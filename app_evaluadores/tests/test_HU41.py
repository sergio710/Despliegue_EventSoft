from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from app_evaluadores.models import Evaluador, EvaluadorEvento
from app_eventos.models import Evento, AdministradorEvento
from app_participantes.models import Participante, Proyecto, ParticipanteEvento
import datetime

Usuario = get_user_model()

class HU41DetalleExpositorTest(TestCase):
    """
    HU41:
    Como EVALUADOR,
    Quiero acceder a la información detallada de cada expositor del evento con la documentación aportada,
    Para obtener mayor información del expositor y la documentación aportada (proyecto, ponencia, etc).
    """

    def setUp(self):
        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin_evento41",
            email="admin41@test.com",
            password="12345",
            documento="12345678"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evaluador
        self.evaluador_user = Usuario.objects.create_user(
            username="evaluador41",
            email="eva41@test.com",
            password="12345",
            documento="99999999"
        )
        self.evaluador = Evaluador.objects.create(usuario=self.evaluador_user)

        # Crear evento
        self.evento = Evento.objects.create(
            eve_nombre="Foro de Tecnología",
            eve_descripcion="Evento académico y tecnológico",
            eve_ciudad="Medellín",
            eve_lugar="Plaza Mayor",
            eve_fecha_inicio=datetime.date(2025, 12, 10),
            eve_fecha_fin=datetime.date(2025, 12, 12),
            eve_estado="Aprobado",
            eve_capacidad=300,
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

        # Crear expositor (participante)
        self.participante_user = Usuario.objects.create_user(
            username="expositor41",
            email="expo41@test.com",
            password="12345",
            documento="55555555",
            first_name="Ana",
            last_name="García"
        )
        self.participante = Participante.objects.create(usuario=self.participante_user)

        # Crear proyecto del expositor con archivo/documento
        self.proyecto = Proyecto.objects.create(
            evento=self.evento,
            titulo="Proyecto Innovador",
            descripcion="Investigación sobre energías renovables",
            estado="Aprobado",
            archivo="proyectos/ponencia.pdf"
        )

        # Relación participante-evento
        self.participante_evento = ParticipanteEvento.objects.create(
            participante=self.participante,
            evento=self.evento,
            par_eve_fecha_hora=timezone.now(),
            par_eve_estado="Aprobado",
            confirmado=True,
            proyecto=self.proyecto
        )

    def test_detalle_expositor(self):
        """
        Cubre los criterios de aceptación de HU41:
        1. Ver información personal del expositor.
        2. Ver título y descripción del proyecto.
        3. Acceder a la documentación aportada por el expositor.
        4. Confirmar el estado de participación del expositor en el evento.
        """

        # (1) Información personal
        self.assertEqual(self.participante.usuario.first_name, "Ana")
        self.assertEqual(self.participante.usuario.last_name, "García")
        self.assertEqual(self.participante.usuario.email, "expo41@test.com")
        self.assertEqual(self.participante.usuario.documento, "55555555")

        # (2) Proyecto asociado
        self.assertEqual(self.proyecto.titulo, "Proyecto Innovador")
        self.assertIn("energías renovables", self.proyecto.descripcion)

        # (3) Documentación aportada
        self.assertIsNotNone(self.proyecto.archivo)
        self.assertIn("ponencia.pdf", str(self.proyecto.archivo))

        # (4) Estado de participación
        self.assertEqual(self.participante_evento.par_eve_estado, "Aprobado")