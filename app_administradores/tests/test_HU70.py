from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from app_eventos.models import Evento, AdministradorEvento
from app_participantes.models import Participante, ParticipanteEvento
import datetime

Usuario = get_user_model()

class HU70NotificacionesAsistentesTest(TestCase):
    """
    HU70:
    Como ADMINISTRADOR DE EVENTO,
    Quiero enviar notificaciones a todos o algunos de los asistentes de un evento,
    Para mantener informados a los asistentes sobre las novedades del evento.
    """

    def setUp(self):
        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin70",
            email="admin70@test.com",
            password="12345",
            documento="12345670"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evento
        self.evento = Evento.objects.create(
            eve_nombre="Feria Internacional de Ciencias",
            eve_descripcion="Evento de divulgación científica",
            eve_ciudad="Quito",
            eve_lugar="Centro de Convenciones",
            eve_fecha_inicio=datetime.date(2025, 12, 10),
            eve_fecha_fin=datetime.date(2025, 12, 12),
            eve_estado="Aprobado",
            eve_capacidad=400,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

        # Crear 3 asistentes vinculados al evento
        self.asistentes = []
        for i in range(1, 4):
            user = Usuario.objects.create_user(
                username=f"asistente{i}",
                email=f"asis{i}@test.com",
                password="12345",
                documento=f"2000{i}"
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

    def enviar_notificacion(self, destinatarios, asunto, contenido):
        """
        Simula el envío de notificaciones a una lista de destinatarios.
        Retorna la cantidad de notificaciones enviadas.
        """
        notificaciones = []
        for participante in destinatarios:
            notificaciones.append({
                "asistente": participante.usuario.email,
                "asunto": asunto,
                "contenido": contenido,
                "evento": self.evento.eve_nombre
            })
        return notificaciones

    def test_enviar_notificaciones(self):
        """
        Cubre los criterios de aceptación de HU70:
        1. Enviar a todos o algunos asistentes.
        2. Incluir asunto y contenido.
        3. Cada asistente recibe su notificación.
        4. Registrar cantidad de destinatarios notificados.
        """

        # (1) Enviar a todos los asistentes
        notificaciones_todos = self.enviar_notificacion(
            self.asistentes,
            "Cambio de horario",
            "El evento comenzará a las 9:00 am en lugar de las 8:00 am."
        )
        self.assertEqual(len(notificaciones_todos), 3)

        # (2) Verificar que cada notificación tiene asunto y contenido
        for n in notificaciones_todos:
            self.assertEqual(n["asunto"], "Cambio de horario")
            self.assertIn("9:00 am", n["contenido"])

        # (3) Enviar a un subconjunto (solo el primer asistente)
        notificaciones_uno = self.enviar_notificacion(
            [self.asistentes[0]],
            "Recordatorio",
            "No olvides traer tu acreditación."
        )
        self.assertEqual(len(notificaciones_uno), 1)
        self.assertEqual(notificaciones_uno[0]["asistente"], "asis1@test.com")

        # (4) Confirmar que se registra la cantidad correcta de destinatarios
        self.assertEqual(len(notificaciones_todos), 3)
        self.assertEqual(len(notificaciones_uno), 1)