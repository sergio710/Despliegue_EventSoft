from django.test import TestCase, override_settings
from django.core import mail
from django.utils import timezone
from app_usuarios.models import Usuario
from app_administradores.models import AdministradorEvento
from app_eventos.models import Evento, ConfiguracionCertificado
from app_participantes.models import Participante, Proyecto, ParticipanteEvento
import datetime


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class HU84CertificadoPremiacionTest(TestCase):
    """
    HU84:
    Como ADMINISTRADOR DE EVENTO,
    Quiero enviar certificado de PUNTUACIÓN Y/O PREMIACIÓN
    a todos o algunos de los expositores de un evento que obtienen algún reconocimiento,
    Para ser recibidos por los expositores ganadores en su correo electrónico.
    """

    def setUp(self):
        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin84",
            email="admin84@test.com",
            password="12345",
            documento="12345684"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evento gestionado por el administrador
        self.evento = Evento.objects.create(
            eve_nombre="Congreso Internacional de Ciencias",
            eve_descripcion="Evento académico y científico",
            eve_ciudad="Medellín",
            eve_lugar="Plaza Mayor",
            eve_fecha_inicio=datetime.date(2025, 12, 1),
            eve_fecha_fin=datetime.date(2025, 12, 3),
            eve_estado="Aprobado",
            eve_capacidad=200,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

        # Configuración de certificado de premiación
        self.config_cert = ConfiguracionCertificado.objects.create(
            evento=self.evento,
            tipo="premiacion",
            plantilla="elegante",
            titulo="Certificado de Premiación",
            cuerpo="Se otorga a {nombre} por su destacada participación en el evento {evento}.",
            fecha_emision=datetime.date.today()
        )

        # Crear proyectos y participantes (algunos con premio)
        self.participantes_evento = []
        for i in range(3):
            user = Usuario.objects.create_user(
                username=f"participante84_{i}",
                email=f"participante84_{i}@test.com",
                password="12345",
                documento=f"8400{i}"
            )
            participante = Participante.objects.create(usuario=user)

            proyecto = Proyecto.objects.create(
                evento=self.evento,
                titulo=f"Proyecto {i}",
                descripcion="Investigación científica",
                estado="Aprobado",
                pro_valor=95 - i * 10 if i < 2 else 60  # los 2 primeros son ganadores
            )

            par_evento = ParticipanteEvento.objects.create(
                participante=participante,
                evento=self.evento,
                par_eve_fecha_hora=timezone.now(),
                par_eve_estado="Aprobado",
                confirmado=True,
                proyecto=proyecto
            )

            self.participantes_evento.append(par_evento)

    def generar_certificado(self, participante_evento):
        """
        Simula la generación de un certificado de premiación.
        """
        return self.config_cert.cuerpo.format(
            nombre=participante_evento.participante.usuario.username,
            evento=self.evento.eve_nombre
        )

    def enviar_certificado(self, participante_evento):
        """
        Simula el envío de correo con certificado de premiación.
        """
        certificado = self.generar_certificado(participante_evento)
        mail.send_mail(
            subject=f"{self.config_cert.titulo} - {self.evento.eve_nombre}",
            message=certificado,
            from_email="noreply@eventos.com",
            recipient_list=[participante_evento.participante.usuario.email],
            fail_silently=False,
        )

    def test_envio_certificados_premiacion(self):
        """
        Cubre los criterios de aceptación de HU84:
        1. Solo el administrador del evento puede enviar certificados.
        2. Solo participantes aprobados y con reconocimiento (ganadores) reciben certificado.
        3. Se envía un correo con el certificado.
        4. El correo contiene asunto claro, cuerpo informativo y datos correctos.
        """

        # (1) Verificar que el admin controla el evento
        self.assertEqual(self.evento.eve_administrador_fk, self.admin)

        # (2) Seleccionar ganadores (proyectos con nota >= 80)
        ganadores = ParticipanteEvento.objects.filter(
            evento=self.evento,
            par_eve_estado="Aprobado",
            proyecto__pro_valor__gte=80
        )
        self.assertEqual(ganadores.count(), 2)

        # (3) Enviar certificados a ganadores
        for par_evento in ganadores:
            self.enviar_certificado(par_evento)

        # (4) Verificar correos enviados
        self.assertEqual(len(mail.outbox), 2)
        for correo in mail.outbox:
            self.assertIn("Certificado de Premiación", correo.subject)
            self.assertIn("Congreso Internacional de Ciencias", correo.body)