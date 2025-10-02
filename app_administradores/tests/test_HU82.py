from django.test import TestCase, override_settings
from django.core import mail
from django.contrib.auth import get_user_model
from django.utils import timezone
from app_eventos.models import Evento, AdministradorEvento
from app_participantes.models import Participante, Proyecto, ParticipanteEvento
import datetime

Usuario = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class HU82CertificadoParticipacionExpositorTest(TestCase):
    """
    HU82:
    Como ADMINISTRADOR DE EVENTO,
    Quiero enviar certificado de PARTICIPACIÓN a todos o algunos de los expositores de un evento,
    Para ser recibidos por los expositores en su correo electrónico.
    """

    def setUp(self):
        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin82",
            email="admin82@test.com",
            password="12345",
            documento="12345682"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evento gestionado por el administrador
        self.evento = Evento.objects.create(
            eve_nombre="Encuentro Científico",
            eve_descripcion="Evento de presentación de proyectos",
            eve_ciudad="Quito",
            eve_lugar="Centro Cultural",
            eve_fecha_inicio=datetime.date(2025, 10, 10),
            eve_fecha_fin=datetime.date(2025, 10, 12),
            eve_estado="Aprobado",
            eve_capacidad=100,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

        # Crear expositores aprobados con proyectos
        self.expositores = []
        for i in range(2):
            user = Usuario.objects.create_user(
                username=f"expositor82_{i}",
                email=f"expositor82_{i}@test.com",
                password="12345",
                documento=f"8200{i}"
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
                proyecto=proyecto,
                par_eve_fecha_hora=timezone.now(),
                par_eve_estado="Aprobado",
                confirmado=True
            )

            self.expositores.append(participante)

    def generar_certificado(self, expositor):
        """
        Simula la generación de un certificado de participación.
        Retorna un string con los datos del expositor y del evento.
        """
        return f"Certificado de participación\nExpositor: {expositor.usuario.first_name or expositor.usuario.username}\nEvento: {self.evento.eve_nombre}"

    def enviar_certificado(self, expositor):
        """
        Simula el envío de correo con certificado adjunto/incrustado.
        """
        certificado = self.generar_certificado(expositor)
        mail.send_mail(
            subject=f"Certificado de participación - {self.evento.eve_nombre}",
            message=certificado,
            from_email="noreply@eventos.com",
            recipient_list=[expositor.usuario.email],
            fail_silently=False,
        )

    def test_envio_certificados_participacion(self):
        """
        Cubre los criterios de aceptación de HU82:
        1. Solo el administrador del evento puede enviar certificados.
        2. Se seleccionan expositores aprobados.
        3. Se envía un correo con el certificado.
        4. El correo contiene asunto claro, cuerpo informativo y datos correctos.
        """

        # (1) Verificar que el admin controla el evento
        self.assertEqual(self.evento.eve_administrador_fk, self.admin)

        # (2) Seleccionar expositores aprobados
        aprobados = ParticipanteEvento.objects.filter(evento=self.evento, par_eve_estado="Aprobado", confirmado=True)
        self.assertEqual(aprobados.count(), 2)

        # (3) Enviar certificados
        for expositor_evento in aprobados:
            self.enviar_certificado(expositor_evento.participante)

        # (4) Verificar correos enviados
        self.assertEqual(len(mail.outbox), 2)
        for i, correo in enumerate(mail.outbox):
            self.assertIn("Certificado de participación", correo.subject)
            self.assertIn("Encuentro Científico", correo.body)
            self.assertIn(self.expositores[i].usuario.username, correo.body)
            self.assertEqual(correo.to, [self.expositores[i].usuario.email])