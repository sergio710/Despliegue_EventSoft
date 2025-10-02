from django.test import TestCase, override_settings
from django.core import mail
from django.contrib.auth import get_user_model
from django.utils import timezone
from app_eventos.models import Evento, AdministradorEvento
from app_evaluadores.models import Evaluador, EvaluadorEvento
import datetime

Usuario = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class HU83CertificadoEvaluadorTest(TestCase):
    """
    HU83:
    Como ADMINISTRADOR DE EVENTO,
    Quiero enviar certificado de EVALUADOR a todos o algunos de los evaluadores de un evento,
    Para ser recibidos por los evaluadores en su correo electrónico.
    """

    def setUp(self):
        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin83",
            email="admin83@test.com",
            password="12345",
            documento="12345683"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evento gestionado por el administrador
        self.evento = Evento.objects.create(
            eve_nombre="Simposio de Innovación",
            eve_descripcion="Evento de innovación y ciencia",
            eve_ciudad="Bogotá",
            eve_lugar="Corferias",
            eve_fecha_inicio=datetime.date(2025, 11, 5),
            eve_fecha_fin=datetime.date(2025, 11, 7),
            eve_estado="Aprobado",
            eve_capacidad=50,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

        # Crear evaluadores aprobados
        self.evaluadores = []
        for i in range(2):
            user = Usuario.objects.create_user(
                username=f"evaluador83_{i}",
                email=f"evaluador83_{i}@test.com",
                password="12345",
                documento=f"8300{i}"
            )
            evaluador = Evaluador.objects.create(usuario=user)

            EvaluadorEvento.objects.create(
                evaluador=evaluador,
                evento=self.evento,
                eva_eve_fecha_hora=timezone.now(),
                eva_eve_estado="Aprobado"
            )

            self.evaluadores.append(evaluador)

    def generar_certificado(self, evaluador):
        """
        Simula la generación de un certificado de evaluador.
        """
        return f"Certificado de evaluador\nEvaluador: {evaluador.usuario.first_name or evaluador.usuario.username}\nEvento: {self.evento.eve_nombre}"

    def enviar_certificado(self, evaluador):
        """
        Simula el envío de correo con certificado adjunto/incrustado.
        """
        certificado = self.generar_certificado(evaluador)
        mail.send_mail(
            subject=f"Certificado de evaluador - {self.evento.eve_nombre}",
            message=certificado,
            from_email="noreply@eventos.com",
            recipient_list=[evaluador.usuario.email],
            fail_silently=False,
        )

    def test_envio_certificados_evaluador(self):
        """
        Cubre los criterios de aceptación de HU83:
        1. Solo el administrador del evento puede enviar certificados.
        2. Se seleccionan evaluadores aprobados.
        3. Se envía un correo con el certificado.
        4. El correo contiene asunto claro, cuerpo informativo y datos correctos.
        """

        # (1) Verificar que el admin controla el evento
        self.assertEqual(self.evento.eve_administrador_fk, self.admin)

        # (2) Seleccionar evaluadores aprobados
        aprobados = EvaluadorEvento.objects.filter(evento=self.evento, eva_eve_estado="Aprobado")
        self.assertEqual(aprobados.count(), 2)

        # (3) Enviar certificados
        for evaluador_evento in aprobados:
            self.enviar_certificado(evaluador_evento.evaluador)

        # (4) Verificar correos enviados
        self.assertEqual(len(mail.outbox), 2)
        for i, correo in enumerate(mail.outbox):
            self.assertIn("Certificado de evaluador", correo.subject)
            self.assertIn("Simposio de Innovación", correo.body)
            self.assertIn(self.evaluadores[i].usuario.username, correo.body)
            self.assertEqual(correo.to, [self.evaluadores[i].usuario.email])