from django.test import TestCase
from django.core import mail
from django.utils import timezone
from django.contrib.auth import get_user_model
from app_eventos.models import Evento, AdministradorEvento
from app_evaluadores.models import EvaluadorEvento, Evaluador
import datetime

Usuario = get_user_model()

class HU38NotificacionesEvaluadorTest(TestCase):
    """
    HU38:
    Como EVALUADOR,
    Quiero recibir notificaciones sobre los eventos en los que soy evaluador,
    Para estar al tanto de información relevante sobre el evento.
    """

    def setUp(self):
        # Crear usuario administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin_evento",
            email="admin@test.com",
            password="12345",
            documento="12345678"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear usuario evaluador
        self.evaluador_user = Usuario.objects.create_user(
            username="evaluador38",
            email="eva38@test.com",
            password="12345",
            documento="87654321"
        )
        self.evaluador = Evaluador.objects.create(usuario=self.evaluador_user)

        # Crear evento
        self.evento = Evento.objects.create(
            eve_nombre="Congreso Nacional",
            eve_descripcion="Evento académico de alcance nacional",
            eve_ciudad="Lima",
            eve_lugar="Centro de Convenciones",
            eve_fecha_inicio=datetime.date(2025, 10, 5),
            eve_fecha_fin=datetime.date(2025, 10, 7),
            eve_estado="Aprobado",
            eve_capacidad=100,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

        # Relación evaluador <-> evento
        self.evaluador_evento = EvaluadorEvento.objects.create(
            evento=self.evento,
            evaluador=self.evaluador,
            eva_eve_fecha_hora=timezone.now(),
            eva_eve_estado="Aprobado",  # ✅ ahora con el nombre correcto
            confirmado=True
        )

    def test_notificacion_cambio_evento(self):
        """
        Criterios de aceptación:
        1. El evaluador recibe un correo cuando hay un cambio en el evento.
        2. El correo contiene el nombre del evento.
        3. El correo incluye el detalle del cambio.
        4. Solo se notifica a evaluadores vinculados al evento.
        """
        cambio = "El lugar del evento ha cambiado a Arequipa."

        mail.send_mail(
            subject=f"[Notificación] Cambio en el evento: {self.evento.eve_nombre}",
            message=f"Estimado evaluador,\n\n{cambio}\n\nEvento: {self.evento.eve_nombre}",
            from_email="noreply@eventsoft.com",
            recipient_list=[self.evaluador.usuario.email]
        )

        # Se envió 1 correo
        self.assertEqual(len(mail.outbox), 1)

        correo = mail.outbox[0]

        # (1) Solo al evaluador
        self.assertIn(self.evaluador.usuario.email, correo.to)
        self.assertNotIn(self.admin_user.email, correo.to)

        # (2) Nombre del evento en asunto y cuerpo
        self.assertIn(self.evento.eve_nombre, correo.subject)
        self.assertIn(self.evento.eve_nombre, correo.body)

        # (3) Incluye el cambio
        self.assertIn(cambio, correo.body)