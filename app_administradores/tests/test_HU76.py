# app_administradores/tests/test_HU76.py

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from app_usuarios.models import Usuario, Rol, RolUsuario
from app_administradores.models import AdministradorEvento
from app_eventos.models import Evento
from app_evaluadores.models import Criterio

class HU76CargarInstrumentoTest(TestCase):
    """
    HU76: Como ADMINISTRADOR DE EVENTO, Quiero cargar el Instrumento de evaluación 
    que se empleará en el evento, Para ofrecer información a los expositores sobre 
    cómo serán evaluados.
    """

    def setUp(self):
        self.client = Client()
        
        # Crear rol y administrador
        self.rol_admin = Rol.objects.create(nombre='administrador_evento')
        self.admin_user = Usuario.objects.create_user(
            username="admin76",
            email="admin76@test.com",
            password="password123",
            documento="12345676"
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_admin)
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evento aprobado
        self.evento = Evento.objects.create(
            eve_nombre="Evento Instrumento",
            eve_descripcion="Evento para cargar instrumento",
            eve_ciudad="Test City",
            eve_lugar="Test Place",
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=2),
            eve_estado="Aprobado",
            eve_capacidad=40,
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

    def test_hu76_cargar_instrumento_completo(self):
        """
        Prueba los 4 criterios de aceptación de HU76:
        CA1: Visualizar instrumento actual con criterios y pesos
        CA2: Mostrar progreso de completitud (peso actual vs 100%)
        CA3: Crear instrumento completo agregando criterios hasta 100%
        CA4: Instrumento completo disponible para expositores y evaluadores
        """
        
        # CA1: Visualizar instrumento actual (inicialmente vacío)
        response_inicial = self.client.get(self.url_gestion)
        self.assertEqual(response_inicial.status_code, 200)
        self.assertIn('criterios', response_inicial.context)
        
        criterios_iniciales = response_inicial.context['criterios']
        self.assertEqual(criterios_iniciales.count(), 0, "CA1: Inicialmente no debe haber criterios")

        # CA2: Mostrar progreso de completitud (0% inicial)
        self.assertIn('peso_total_actual', response_inicial.context)
        peso_inicial = response_inicial.context['peso_total_actual']
        self.assertEqual(peso_inicial, 0, "CA2: Peso inicial debe ser 0")

        # CA3: Crear instrumento completo paso a paso
        criterios_instrumento = [
            {'descripcion': 'Contenido Técnico', 'peso': 40},
            {'descripcion': 'Presentación Oral', 'peso': 35},
            {'descripcion': 'Material Visual', 'peso': 25}
        ]

        peso_acumulado = 0
        for criterio in criterios_instrumento:
            # Agregar criterio
            response_add = self.client.post(self.url_agregar, {
                'descripcion': criterio['descripcion'],
                'peso': str(criterio['peso'])
            })
            self.assertEqual(response_add.status_code, 302, "CA3: Debe agregar criterio")
            
            peso_acumulado += criterio['peso']
            
            # Verificar progreso después de cada adición
            response_progreso = self.client.get(self.url_gestion)
            peso_actual = response_progreso.context['peso_total_actual']
            self.assertEqual(peso_actual, peso_acumulado, f"CA2: Peso debe ser {peso_acumulado}%")

        # Verificar instrumento completo (100%)
        response_completo = self.client.get(self.url_gestion)
        peso_final = response_completo.context['peso_total_actual']
        self.assertEqual(peso_final, 100, "CA3: Instrumento debe estar completo (100%)")

        criterios_finales = response_completo.context['criterios']
        self.assertEqual(criterios_finales.count(), 3, "CA3: Debe haber 3 criterios")

        # CA4: Instrumento disponible para consulta
        criterios_bd = Criterio.objects.filter(cri_evento_fk=self.evento)
        self.assertEqual(criterios_bd.count(), 3, "CA4: Los 3 criterios deben estar en BD")
        
        peso_total_verificacion = sum(c.cri_peso for c in criterios_bd)
        self.assertEqual(peso_total_verificacion, 100.0, "CA4: Peso total debe ser exactamente 100%")
        
        # Verificar disponibilidad estructurada
        for criterio_data in criterios_instrumento:
            criterio_bd = Criterio.objects.get(
                cri_descripcion=criterio_data['descripcion'],
                cri_evento_fk=self.evento
            )
            self.assertEqual(criterio_bd.cri_peso, float(criterio_data['peso']), 
                           f"CA4: Criterio {criterio_data['descripcion']} debe tener peso correcto")