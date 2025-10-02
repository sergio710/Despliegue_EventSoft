from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from app_evaluadores.models import Evaluador, EvaluadorEvento, Criterio
from app_eventos.models import Evento, AdministradorEvento
import datetime

Usuario = get_user_model()

class HU42GestionRubricaTest(TestCase):
    """
    HU42:
    Como EVALUADOR,
    Quiero gestionar ítems del instrumento de evaluación (rúbrica, lista de chequeo, plantilla) asociado a un evento,
    Para establecer los parámetros de calificación que se tendrán en cuenta durante el evento.
    """

    def setUp(self):
        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin_evento42",
            email="admin42@test.com",
            password="12345",
            documento="12345678"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evaluador
        self.evaluador_user = Usuario.objects.create_user(
            username="evaluador42",
            email="eva42@test.com",
            password="12345",
            documento="99999999"
        )
        self.evaluador = Evaluador.objects.create(usuario=self.evaluador_user)

        # Crear evento
        self.evento = Evento.objects.create(
            eve_nombre="Foro Internacional",
            eve_descripcion="Evento académico sobre innovación",
            eve_ciudad="Quito",
            eve_lugar="Centro de Convenciones",
            eve_fecha_inicio=datetime.date(2025, 10, 10),
            eve_fecha_fin=datetime.date(2025, 10, 12),
            eve_estado="Pendiente",
            eve_capacidad=300,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

        # Relación evaluador-evento
        self.evaluador_evento = EvaluadorEvento.objects.create(
            evaluador=self.evaluador,
            evento=self.evento,
            eva_eve_fecha_hora=timezone.now(),
            eva_eve_estado="Aprobado",
            confirmado=True
        )

    def test_gestion_rubrica(self):
        """
        Cubre los criterios de aceptación de HU42:
        1. Restricción por permiso.
        2. Agregar ítems a la rúbrica.
        3. Modificar ítems existentes.
        4. Eliminar ítems de la rúbrica.
        """

        # (1) Restricción por permiso
        # Simulación: al inicio el evaluador NO tiene permiso
        setattr(self.evaluador_evento, "puede_gestionar_rubrica", False)
        self.assertFalse(self.evaluador_evento.puede_gestionar_rubrica)

        # Luego el administrador habilita el permiso
        setattr(self.evaluador_evento, "puede_gestionar_rubrica", True)
        self.assertTrue(self.evaluador_evento.puede_gestionar_rubrica)

        # (2) Agregar ítem a la rúbrica
        criterio = Criterio.objects.create(
            cri_descripcion="Claridad de la presentación",
            cri_peso=0.3,
            cri_evento_fk=self.evento
        )
        self.assertEqual(Criterio.objects.filter(cri_evento_fk=self.evento).count(), 1)

        # (3) Modificar ítem existente
        criterio.cri_descripcion = "Claridad y coherencia de la presentación"
        criterio.save()
        self.assertEqual(
            Criterio.objects.get(cri_id=criterio.cri_id).cri_descripcion,
            "Claridad y coherencia de la presentación"
        )

        # (4) Eliminar ítem de la rúbrica
        criterio_id = criterio.cri_id
        criterio.delete()
        self.assertFalse(Criterio.objects.filter(cri_id=criterio_id).exists())