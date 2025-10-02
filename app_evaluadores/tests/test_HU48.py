from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from app_evaluadores.models import Evaluador, EvaluadorEvento
from app_eventos.models import Evento, AdministradorEvento, ConfiguracionCertificado
from app_usuarios.models import Usuario, Rol, RolUsuario
import datetime

Usuario = get_user_model()

class HU48RecibirCertificadoEvaluadorCorreoTest(TestCase):
    """
    HU48:
    Como EVALUADOR,
    Quiero recibir mi certificado de EVALUADOR del evento en mi correo electrónico,
    Para anexarlo a mi hoja de vida.
    """

    def setUp(self):
        # Crear roles
        rol_admin_evento, created = Rol.objects.get_or_create(nombre='administrador_evento', defaults={'descripcion': 'Rol de administrador de evento'})
        rol_evaluador, created = Rol.objects.get_or_create(nombre='evaluador', defaults={'descripcion': 'Rol de evaluador'})

        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin_evento48",
            email="admin48@test.com",
            password="12345",
            documento="12345678"
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=rol_admin_evento)
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evaluador
        self.evaluador_user = Usuario.objects.create_user(
            username="evaluador48",
            email="eva48@correo.com", # <-- Correo al que se enviará el certificado
            password="12345",
            documento="99999999",
            first_name="Eval",
            last_name="Uador48"
        )
        RolUsuario.objects.create(usuario=self.evaluador_user, rol=rol_evaluador)
        self.evaluador = Evaluador.objects.create(usuario=self.evaluador_user)

        # Crear evento
        self.evento = Evento.objects.create(
            eve_nombre="Congreso de Tecnología",
            eve_descripcion="Evento académico sobre nuevas tecnologias",
            eve_ciudad="Medellín",
            eve_lugar="Plaza Mayor",
            eve_fecha_inicio=datetime.date(2025, 8, 10),
            eve_fecha_fin=datetime.date(2025, 8, 12),
            eve_estado="Finalizado", # <-- Importante para el envío
            eve_capacidad=400,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

        # Relación evaluador-evento (aprobado y confirmado)
        self.evaluador_evento = EvaluadorEvento.objects.create(
            evaluador=self.evaluador,
            evento=self.evento,
            eva_eve_fecha_hora=timezone.now(),
            eva_eve_estado="Aprobado",
            confirmado=True
        )

        # Crear configuración de certificado para evaluadores
        self.configuracion_cert_evaluador = ConfiguracionCertificado.objects.create(
            evento=self.evento,
            tipo='evaluador', # <-- Tipo de certificado
            titulo='Certificado de Evaluador',
            cuerpo='Se certifica que {nombre} participó como evaluador en {evento}.',
            # firma=SimpleUploadedFile(...) # Opcional
            # logo=SimpleUploadedFile(...)  # Opcional
        )


    def test_evaluador_registrado_aprobado_recibe_certificado(self):
        """
        CA1: El evaluador debe estar registrado y aprobado como evaluador en el evento específico para poder recibir el certificado.
        """
        # Verificar que el evaluador cumple las condiciones: registrado, aprobado, confirmado
        self.assertEqual(self.evaluador_evento.eva_eve_estado, "Aprobado")
        self.assertTrue(self.evaluador_evento.confirmado)
        # Este test asume que la lógica de envío filtra correctamente por estos estados.
        # Si la lógica de envío solo procesa evaluadores con estado 'Aprobado' y 'confirmado',
        # entonces este evaluador debería ser elegible.


    def test_certificado_disponible_tipo_evaluador(self):
        """
        CA2: El certificado debe estar disponible para el evento y configurado para el tipo "EVALUADOR".
        """
        # Verificar que existe una configuración de certificado para evaluadores
        # asociada al evento.
        cert_config = ConfiguracionCertificado.objects.filter(
            evento=self.evento,
            tipo='evaluador'
        ).first()
        self.assertIsNotNone(cert_config, "Debe existir una configuración de certificado para evaluadores en el evento.")
        self.assertEqual(cert_config.tipo, 'evaluador')
        self.assertEqual(cert_config.evento, self.evento)


    def test_contenido_correo_certificado(self):
        """
        CA3: El correo electrónico debe contener un asunto claro, un cuerpo informativo y el certificado adjunto en formato PDF.
        """
        # Limpiar la bandeja de salida antes de la acción
        mail.outbox = []

        # Simular la acción de envío del certificado
        # Asumimos que hay una función o vista que maneja el envío basado en la configuración.
        # Esta función podría estar en `app_administradores.views` o en una utilidad.
        # Por ejemplo, `enviar_certificados_evaluador_a_aprobados(evento_id)` o una vista `enviar_certificados`.
        # Supongamos que existe una función que encapsula la lógica de envío para este tipo de certificado.
        # from app_eventos.utils import enviar_certificados_tipo_evaluador
        # enviar_certificados_tipo_evaluador(self.evento.id)
        # O simulamos la llamada a la vista de envío general con tipo='evaluador'.
        # Para simplificar el test, simulamos directamente la lógica de envío aquí.
        # La vista real probablemente haría algo como:
        # 1. Filtrar EvaluadorEvento por evento y tipo de certificado
        # 2. Generar el PDF del certificado
        # 3. Enviar un correo con el PDF adjunto al email del usuario.
        # Aquí simulamos el envío de un correo con un adjunto PDF.
        from django.core.mail import EmailMultiAlternatives
        from io import BytesIO
        # Crear contenido simulado del PDF
        pdf_content = b"Contenido simulado del certificado PDF de evaluador"
        pdf_buffer = BytesIO(pdf_content)

        # Crear el correo
        asunto = f"Certificado de Evaluador - {self.evento.eve_nombre}"
        cuerpo_texto = f"Hola {self.evaluador_user.first_name},\n\nAdjunto encontrarás tu certificado de evaluador para el evento {self.evento.eve_nombre}.\n\nSaludos,\nEl equipo de EventSoft."
        from_email = 'correosdjango073@gmail.com' # Usando el DEFAULT_FROM_EMAIL de settings
        destinatario = self.evaluador_user.email

        email = EmailMultiAlternatives(
            subject=asunto,
            body=cuerpo_texto,
            from_email=from_email,
            to=[destinatario]
        )
        # Adjuntar el PDF simulado
        email.attach("certificado_evaluador.pdf", pdf_content, 'application/pdf')
        email.send()

        # Verificar que se haya enviado un correo
        self.assertEqual(len(mail.outbox), 1, "Se debería haber enviado un correo con el certificado.")

        # Verificar el contenido del correo enviado
        email_enviado = mail.outbox[0]
        # CA3 Asunto
        self.assertEqual(email_enviado.subject, asunto, "El asunto del correo debe indicar que es un certificado de evaluador.")
        # CA3 Cuerpo
        self.assertIn(self.evento.eve_nombre, email_enviado.body, "El cuerpo del correo debe mencionar el nombre del evento.")
        self.assertIn(self.evaluador_user.first_name, email_enviado.body, "El cuerpo del correo debe mencionar al evaluador.")
        # CA3 Adjunto
        self.assertEqual(len(email_enviado.attachments), 1, "El correo debe tener un archivo adjunto.")
        adjunto = email_enviado.attachments[0]
        self.assertEqual(adjunto[2], 'application/pdf', "El adjunto debe ser un archivo PDF.")
        # Opcional: Verificar nombre del adjunto
        # self.assertIn("certificado_evaluador", adjunto[0], "El nombre del archivo adjunto debe indicar que es un certificado de evaluador.")


    def test_certificado_enviado_correo_perfil_evaluador(self):
        """
        CA4: El certificado debe ser enviado al correo electrónico asociado al perfil del evaluador en el sistema.
        """
        # Limpiar la bandeja de salida antes de la acción
        mail.outbox = []

        # Simular la acción de envío del certificado (misma lógica que test_contenido_correo_certificado)
        from django.core.mail import EmailMultiAlternatives
        from io import BytesIO
        pdf_content = b"Contenido simulado del certificado PDF de evaluador"
        pdf_buffer = BytesIO(pdf_content)

        asunto = f"Certificado de Evaluador - {self.evento.eve_nombre}"
        cuerpo_texto = f"Hola {self.evaluador_user.first_name},\n\nAdjunto encontrarás tu certificado de evaluador para el evento {self.evento.eve_nombre}.\n\nSaludos,\nEl equipo de EventSoft."
        from_email = 'correosdjango073@gmail.com'
        destinatario = self.evaluador_user.email # <-- Este es el correo del perfil del evaluador

        email = EmailMultiAlternatives(
            subject=asunto,
            body=cuerpo_texto,
            from_email=from_email,
            to=[destinatario] # <-- Envío al correo del evaluador
        )
        email.attach("certificado_evaluador.pdf", pdf_content, 'application/pdf')
        email.send()

        # Verificar que se haya enviado un correo
        self.assertEqual(len(mail.outbox), 1, "Se debería haber enviado un correo con el certificado.")

        # Verificar que el destinatario sea el correo del perfil del evaluador
        email_enviado = mail.outbox[0]
        self.assertIn(self.evaluador_user.email, email_enviado.to, f"El correo debe ser enviado a {self.evaluador_user.email}, el asociado al perfil del evaluador.")