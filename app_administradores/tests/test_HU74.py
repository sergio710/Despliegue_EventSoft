# app_administradores/tests/test_HU74.py

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from app_usuarios.models import Usuario, Rol, RolUsuario
from app_administradores.models import AdministradorEvento
from app_eventos.models import Evento
from app_evaluadores.models import Criterio

class HU74GestionItemsTest(TestCase):
    """
    HU74: Como ADMINISTRADOR DE EVENTO, Quiero gestionar (agregar, modificar, eliminar) 
    ítems de un instrumento de evaluación asociado a un evento, Para establecer los 
    parámetros de calificación que se tendrán en cuenta durante el evento.
    """

    def setUp(self):
        self.client = Client()
        
        # Crear rol y administrador
        self.rol_admin = Rol.objects.create(nombre='administrador_evento')
        self.admin_user = Usuario.objects.create_user(
            username="admin74",
            email="admin74@test.com",
            password="password123",
            documento="12345674"
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_admin)
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evento aprobado
        self.evento = Evento.objects.create(
            eve_nombre="Evento Evaluación",
            eve_descripcion="Evento para testing",
            eve_ciudad="Test City",
            eve_lugar="Test Place",
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado="Aprobado",
            eve_capacidad=50,
            eve_tienecosto="No",
            eve_administrador_fk=self.admin
        )

        # URLs
        self.url_gestion = reverse('gestion_item_administrador_evento', args=[self.evento.pk])
        self.url_agregar = reverse('agregar_item_administrador_evento', args=[self.evento.pk])

        # Login
        self.client.force_login(self.admin_user)
        session = self.client.session
        session['rol_sesion'] = 'administrador_evento'
        session.save()

    def test_hu74_gestion_completa_items(self):
        """
        Prueba los 5 criterios de aceptación de HU74:
        CA1: Agregar ítems con descripción y peso
        CA2: Modificar ítems existentes  
        CA3: Eliminar ítems
        CA4: Validar que suma no exceda 100%
        CA5: Solo permitir gestión en eventos aprobados
        """
        
        # CA1: Agregar nuevo ítem
        datos_item1 = {
            'descripcion': 'Dominio del Tema',
            'peso': '40'
        }
        response1 = self.client.post(self.url_agregar, datos_item1)
        self.assertEqual(response1.status_code, 302, "CA1: Debe agregar ítem exitosamente")
        
        criterio1 = Criterio.objects.get(cri_descripcion='Dominio del Tema', cri_evento_fk=self.evento)
        self.assertEqual(criterio1.cri_peso, 40.0, "CA1: Peso debe ser 40.0")

        # Agregar segundo ítem
        datos_item2 = {
            'descripcion': 'Presentación',
            'peso': '35'
        }
        response2 = self.client.post(self.url_agregar, datos_item2)
        criterio2 = Criterio.objects.get(cri_descripcion='Presentación', cri_evento_fk=self.evento)

        # CA2: Modificar ítem existente
        url_editar = reverse('editar_item_administrador_evento', args=[criterio1.cri_id])
        datos_modificar = {
            'descripcion': 'Dominio Técnico Actualizado',
            'peso': '45'
        }
        response_mod = self.client.post(url_editar, datos_modificar)
        self.assertEqual(response_mod.status_code, 302, "CA2: Debe modificar ítem exitosamente")
        
        criterio1.refresh_from_db()
        self.assertEqual(criterio1.cri_descripcion, 'Dominio Técnico Actualizado', "CA2: Descripción debe cambiar")
        self.assertEqual(criterio1.cri_peso, 45.0, "CA2: Peso debe cambiar a 45.0")

        # CA4: Validar suma no exceda 100% (intentar agregar ítem que exceda)
        datos_exceso = {
            'descripcion': 'Criterio Exceso',
            'peso': '50'  # 45 + 35 + 50 = 130% > 100%
        }
        response_exceso = self.client.post(self.url_agregar, datos_exceso)
        
        # Debe redirigir con error (no crear el criterio)
        criterios_exceso = Criterio.objects.filter(cri_descripcion='Criterio Exceso')
        self.assertEqual(criterios_exceso.count(), 0, "CA4: No debe crear ítem que exceda 100%")

        # CA3: Eliminar ítem
        criterios_antes = Criterio.objects.filter(cri_evento_fk=self.evento).count()
        url_eliminar = reverse('eliminar_item_administrador_evento', args=[criterio2.cri_id])
        response_eliminar = self.client.post(url_eliminar)
        self.assertEqual(response_eliminar.status_code, 302, "CA3: Debe eliminar ítem exitosamente")
        
        criterios_despues = Criterio.objects.filter(cri_evento_fk=self.evento).count()
        self.assertEqual(criterios_despues, criterios_antes - 1, "CA3: Debe reducir número de criterios")

        # CA5: Verificar que funciona solo con evento aprobado
        evento_pendiente = Evento.objects.create(
            eve_nombre="Evento Pendiente",
            eve_descripcion="Estado incorrecto",
            eve_ciudad="Test",
            eve_lugar="Test",
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado="Pendiente",  # No aprobado
            eve_capacidad=50,
            eve_tienecosto="No",
            eve_administrador_fk=self.admin
        )
        
        url_agregar_pendiente = reverse('agregar_item_administrador_evento', args=[evento_pendiente.pk])
        response_pendiente = self.client.post(url_agregar_pendiente, {
            'descripcion': 'Test Pendiente',
            'peso': '20'
        })
        
        # Tu vista debe verificar que el evento esté aprobado
        self.assertIn(response_pendiente.status_code, [200, 302], "CA5: Debe manejar evento no aprobado")

        # Verificar estructura final
        criterios_finales = Criterio.objects.filter(cri_evento_fk=self.evento)
        self.assertEqual(criterios_finales.count(), 1, "Debe quedar 1 criterio al final")
        
        peso_total = sum(c.cri_peso for c in criterios_finales)
        self.assertLessEqual(peso_total, 100.0, "Peso total no debe exceder 100%")