from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from app_evaluadores.models import Evaluador, EvaluadorEvento
from app_eventos.models import Evento, AdministradorEvento
import datetime

Usuario = get_user_model()

class HU39PerfilEvaluadorTest(TestCase):
    """
    HU39:
    Como EVALUADOR,
    Quiero acceder a la información de mi perfil
    Para visualizar mis datos y los documentos aportados.
    """

    def setUp(self):
        # Crear usuario administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin_evento",
            email="admin39@test.com",
            password="12345",
            documento="11111111"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear usuario evaluador
        self.evaluador_user = Usuario.objects.create_user(
            username="evaluador39",
            email="eva39@test.com",
            password="12345",
            documento="99999999",
            first_name="Carlos",
            last_name="Pérez"
        )
        self.evaluador = Evaluador.objects.create(usuario=self.evaluador_user)

        # Crear evento
        self.evento = Evento.objects.create(
            eve_nombre="Simposio de Innovación",
            eve_descripcion="Evento de innovación tecnológica",
            eve_ciudad="Lima",
            eve_lugar="Centro de Innovación",
            eve_fecha_inicio=datetime.date(2025, 11, 2),
            eve_fecha_fin=datetime.date(2025, 11, 4),
            eve_estado="Aprobado",
            eve_capacidad=200,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

        # Relación evaluador-evento con documentos
        self.evaluador_evento = EvaluadorEvento.objects.create(
            evaluador=self.evaluador,
            evento=self.evento,
            eva_eve_fecha_hora=timezone.now(),
            eva_eve_estado="Aprobado",
            eva_eve_documentos="evaluadores/documentos/cv.pdf",
            confirmado=True
        )

    def test_visualizar_informacion_perfil(self):
        """
        Cubre los criterios de aceptación de HU39:
        1. Ver información personal.
        2. Ver eventos en los que participa.
        3. Consultar documentos aportados.
        4. Ver estado de participación en cada evento.
        """

        # (1) Información personal
        self.assertEqual(self.evaluador.usuario.first_name, "Carlos")
        self.assertEqual(self.evaluador.usuario.last_name, "Pérez")
        self.assertEqual(self.evaluador.usuario.email, "eva39@test.com")
        self.assertEqual(self.evaluador.usuario.documento, "99999999")

        # (2) Eventos asociados
        eventos = EvaluadorEvento.objects.filter(evaluador=self.evaluador)
        self.assertEqual(eventos.count(), 1)
        self.assertEqual(eventos.first().evento.eve_nombre, "Simposio de Innovación")

        # (3) Documentos aportados
        self.assertIsNotNone(eventos.first().eva_eve_documentos)
        self.assertIn("cv.pdf", str(eventos.first().eva_eve_documentos))

        # (4) Estado de participación
        self.assertEqual(eventos.first().eva_eve_estado, "Aprobado")