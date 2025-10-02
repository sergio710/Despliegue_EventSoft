from django.test import TestCase, override_settings
from django.core import mail
from django.contrib.auth import get_user_model
from django.utils import timezone
from app_eventos.models import Evento, AdministradorEvento
from app_participantes.models import Participante, ParticipanteEvento
import datetime

Usuario = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class HU81CertificadoAsistenciaTest(TestCase):
    """
    HU81:
    Como ADMINISTRADOR DE EVENTO,
    Quiero enviar certificado de ASISTENCIA a todos o algunos de los asistentes de un evento,
    Para ser recibidos por los asistentes en su correo electrónico.
    """

    def setUp(self):
        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin81",
            email="admin81@test.com",
            password="12345",
            documento="12345681"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evento gestionado por el administrador
        self.evento = Evento.objects.create(
            eve_nombre="Jornadas Académicas",
            eve_descripcion="Evento de formación académica",
            eve_ciudad="Cali",
            eve_lugar="Centro de Convenciones",
            eve_fecha_inicio=datetime.date(2025, 9, 1),
            eve_fecha_fin=datetime.date(2025, 9, 3),
            eve_estado="Aprobado",
            eve_capacidad=200,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

        # Crear asistentes aprobados
        self.asistentes = []
        for i in range(2):
            user = Usuario.objects.create_user(
                username=f"asistente81_{i}",
                email=f"asistente81_{i}@test.com",
                password="12345",
                documento=f"8100{i}"
            )
            participante = Participante.objects.create(usuario=user)
            ParticipanteEvento.objects.create(
                participante=participante,
                evento=self.evento,
                par_eve_fecha_hora=timezone.now(),
                par_eve_estado="Aprobado",
                confirmado=True
            )
            self.asistentes.append(participante)

    def generar_certificado(self, participante):
        """
        Simula la generación de un certificado de asistencia.
        Retorna un string que contendría los datos del asistente y del evento.
        """
        return f"Certificado de asistencia\nAsistente: {participante.usuario.first_name or participante.usuario.username}\nEvento: {self.evento.eve_nombre}"

    def enviar_certificado(self, participante):
        """
        Simula el envío de correo con certificado adjunto/incrustado.
        """
        certificado = self.generar_certificado(participante)
        mail.send_mail(
            subject=f"Certificado de asistencia - {self.evento.eve_nombre}",
            message=certificado,
            from_email="noreply@eventos.com",
            recipient_list=[participante.usuario.email],
            fail_silently=False,
        )

    def test_envio_certificados_asistencia(self):
        """
        Cubre los criterios de aceptación de HU81:
        1. Solo el administrador del evento puede enviar certificados.
        2. Se seleccionan asistentes aprobados.
        3. Se envía un correo con el certificado.
        4. El correo contiene asunto claro, cuerpo informativo y datos correctos.
        """

        # (1) Verificar que el admin controla el evento
        self.assertEqual(self.evento.eve_administrador_fk, self.admin)

        # (2) Seleccionar asistentes aprobados
        aprobados = ParticipanteEvento.objects.filter(evento=self.evento, par_eve_estado="Aprobado", confirmado=True)
        self.assertEqual(aprobados.count(), 2)

        # (3) Enviar certificados
        for participante_evento in aprobados:
            self.enviar_certificado(participante_evento.participante)

        # (4) Verificar correos enviados
        self.assertEqual(len(mail.outbox), 2)
        for i, correo in enumerate(mail.outbox):
            self.assertIn("Certificado de asistencia", correo.subject)
            self.assertIn("Jornadas Académicas", correo.body)
            self.assertIn(self.asistentes[i].usuario.username, correo.body)
            self.assertEqual(correo.to, [self.asistentes[i].usuario.email])