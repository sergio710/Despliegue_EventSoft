from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from app_asistentes.models import AsistenteEvento
from app_usuarios.models import Asistente
from app_eventos.models import Evento, Categoria, EventoCategoria
from django.contrib.messages import get_messages
from django.conf import settings
import os
import json
from datetime import date
import shutil
import tempfile

class TestAsistenteViews(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Crear directorio temporal para media
        cls.temp_dir = tempfile.mkdtemp()
        settings.MEDIA_ROOT = cls.temp_dir
    def setUp(self):
        self.client = Client()
        
        # Crear usuario y asistente
        self.user = User.objects.create_user(
            username='asistente_test',
            password='password123',
            first_name='Asistente',
            last_name='Test'
        )
        self.asistente = Asistente.objects.create(
            usuario=self.user,
            asi_tipo_documento='CC',
            asi_documento='1234567890',
            asi_fecha_nacimiento=date(2000, 1, 1)
        )
        
        # Crear evento con todos los campos necesarios
        self.evento = Evento.objects.create(
            eve_nombre='Evento Test',
            eve_fecha_inicio=date(2024, 1, 1),
            eve_fecha_fin=date(2024, 1, 2),
            eve_lugar='Lugar Test',
            eve_ciudad='Ciudad Test',
            eve_descripcion='Descripción Test'
        )
        
        # Crear relación AsistenteEvento con QR
        self.relacion = AsistenteEvento.objects.create(
            asistente=self.asistente,
            evento=self.evento,
            asi_eve_estado='Aprobado',
            asi_eve_qr='qr_code_test'
        )
        
        # Crear categoría y asociarla al evento
        self.categoria = Categoria.objects.create(cat_nombre='Categoría Test')
        EventoCategoria.objects.create(evento=self.evento, categoria=self.categoria)
        
        # Crear directorios necesarios
        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'manuales'), exist_ok=True)
        
        # Crear archivos de prueba
        self.crear_archivos_prueba()
        
        # Login
        self.client.login(username='asistente_test', password='password123')

    def crear_archivos_prueba(self):
        # Crear archivo de programación
        content = b'Contenido de prueba para programacion'
        self.evento.eve_programacion = SimpleUploadedFile(
            'programacion.pdf',
            content,
            content_type='application/pdf'
        )
        
        # Crear archivo de memorias
        content = b'Contenido de prueba para memorias'
        self.evento.eve_memorias = SimpleUploadedFile(
            'memorias.pdf',
            content,
            content_type='application/pdf'
        )
        self.evento.save()
        
        # Crear manual de asistente
        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'manuales'), exist_ok=True)
        manual_path = os.path.join(settings.MEDIA_ROOT, 'manuales', 'MANUAL_ASISTENTE_SISTEMA_EVENTSOFT.pdf')
        with open(manual_path, 'wb') as f:
            f.write(b'Contenido del manual')

    def test_dashboard_asistente_sin_login(self):
        # Desloguear al usuario
        self.client.logout()
        response = self.client.get(reverse('dashboard_asistente'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_dashboard_asistente_no_asistente(self):
        # Crear usuario no asistente
        user2 = User.objects.create_user('no_asistente', 'pass123')
        self.client.force_login(user2)
        response = self.client.get(reverse('dashboard_asistente'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('ver_eventos'))

    def test_dashboard_asistente_success(self):
        # Crear evento adicional con memorias
        evento2 = Evento.objects.create(
            eve_nombre='Evento Test 2',
            eve_fecha_inicio=date(2024, 1, 1),
            eve_fecha_fin=date(2024, 1, 2),
            eve_lugar='Lugar Test 2',
            eve_descripcion='Descripción Test 2',
            eve_ciudad='Ciudad Test 2'
        )
        
        # Asignar archivo de memorias
        evento2.eve_memorias = SimpleUploadedFile(
            'memorias2.pdf',
            b'Contenido memorias',
            content_type='application/pdf'
        )
        evento2.save()
        
        # Crear relación pendiente
        AsistenteEvento.objects.create(
            asistente=self.asistente,
            evento=evento2,
            asi_eve_estado='Pendiente'
        )

        response = self.client.get(reverse('dashboard_asistente'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app_asistentes/dashboard_asistente.html')

        # Verificar estadísticas
        stats = response.context['estadisticas']
        self.assertEqual(stats['total'], 2)
        self.assertEqual(stats['pendientes'], 1)
        self.assertEqual(stats['aprobados'], 1)
        self.assertEqual(stats['con_qr'], 1)

        # Verificar relaciones con memorias
        rel_memorias = response.context['relaciones_con_memorias']
        self.assertEqual(len(rel_memorias), 2)
        # Verificar que hay eventos con y sin memorias
        memorias_count = sum(1 for r in rel_memorias if r['tiene_memorias'])
        self.assertEqual(memorias_count, 1)

    def test_detalle_evento_asistente(self):
        # Prueba GET
        response = self.client.get(reverse('detalle_evento_asistente', args=[self.evento.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app_asistentes/detalle_evento_asistente.html')
        
        # Verificar contenido del contexto
        self.assertIn('evento', response.context)
        self.assertIn('relacion', response.context)
        self.assertIn('tiene_memorias', response.context)
        self.assertIn('tiene_soporte', response.context)
        
        # Prueba cancelar inscripción
        response = self.client.post(reverse('detalle_evento_asistente', args=[self.evento.pk]), {
            'cancelar_inscripcion': 'true'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard_asistente'))
        
        # Verificar que se eliminó la relación
        self.assertFalse(AsistenteEvento.objects.filter(id=self.relacion.id).exists())

    def test_compartir_evento_sin_login(self):
        self.client.logout()
        response = self.client.get(reverse('compartir_evento', args=[self.evento.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_compartir_evento_no_asistente(self):
        # Crear usuario no asistente
        user2 = User.objects.create_user('no_asistente', 'pass123')
        self.client.force_login(user2)
        response = self.client.get(reverse('compartir_evento', args=[self.evento.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('ver_eventos'))

    def test_compartir_evento_no_existe(self):
        response = self.client.get(reverse('compartir_evento', args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_compartir_evento_no_inscrito(self):
        # Eliminar la relación
        self.relacion.delete()
        response = self.client.get(reverse('compartir_evento', args=[self.evento.pk]))
        self.assertEqual(response.status_code, 404)

    def test_compartir_evento_success(self):
        # GET request
        response = self.client.get(reverse('compartir_evento', args=[self.evento.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app_asistentes/compartir_evento.html')
        
        # Verificar contexto
        self.assertEqual(response.context['evento'], self.evento)
        self.assertEqual(response.context['asistente_nombre'], 'Asistente Test')
        self.assertTrue(response.context['url_evento'].endswith(
            reverse('detalle_evento_asistente', args=[self.evento.pk])
        ))
        self.assertEqual(response.context['categorias'], ['Categoría Test'])

        # POST request (no AJAX)
        response = self.client.post(reverse('compartir_evento', args=[self.evento.pk]))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.verify_share_data(data)

        # POST request (AJAX)
        response = self.client.post(
            reverse('compartir_evento', args=[self.evento.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.verify_share_data(data)

    def verify_share_data(self, data):
        self.assertTrue(data['success'])
        self.assertIn('mensaje', data)
        self.assertIn('titulo', data)
        self.assertIn('url', data)
        self.assertIn('evento_nombre', data)
        
        mensaje = data['mensaje']
        # Verificar todos los componentes del mensaje
        self.assertIn('¡Hola! Soy Asistente Test', mensaje)
        self.assertIn(self.evento.eve_nombre, mensaje)
        self.assertIn(self.evento.eve_lugar, mensaje)
        self.assertIn(self.evento.eve_ciudad, mensaje)
        self.assertIn(self.evento.eve_descripcion, mensaje)
        self.assertIn('Categoría Test', mensaje)
        self.assertIn(self.evento.eve_fecha_inicio.strftime('%d/%m/%Y'), mensaje)
        self.assertIn(self.evento.eve_fecha_fin.strftime('%d/%m/%Y'), mensaje)

    def test_descargar_programacion(self):
        # Prueba descarga exitosa
        response = self.client.get(reverse('descargar_programacion', args=[self.evento.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        
        # Prueba cuando no hay programación
        self.evento.eve_programacion = None
        self.evento.save()
        response = self.client.get(reverse('descargar_programacion', args=[self.evento.pk]))
        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('No hay programación disponible', str(messages[0]))

    def test_descargar_memorias_asistente(self):
        # Aprobar la relación
        self.relacion.asi_eve_estado = 'Aprobado'
        self.relacion.save()
        
        # Prueba descarga exitosa
        response = self.client.get(reverse('descargar_memorias_asistente', args=[self.evento.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        
        # Prueba cuando no está aprobado
        self.relacion.asi_eve_estado = 'Pendiente'
        self.relacion.save()
        response = self.client.get(reverse('descargar_memorias_asistente', args=[self.evento.pk]))
        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('Solo puedes descargar memorias si tu inscripción está aprobada', str(messages[0]))
        
        # Prueba cuando no hay memorias
        self.evento.eve_memorias = None
        self.evento.save()
        response = self.client.get(reverse('descargar_memorias_asistente', args=[self.evento.pk]))
        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('Este evento no tiene memorias disponibles', str(messages[0]))
        
        # Prueba cuando el archivo físico no existe
        self.evento.eve_memorias = SimpleUploadedFile(
            'memorias_no_existen.pdf',
            b'contenido',
            content_type='application/pdf'
        )
        self.evento.save()
        # Eliminar el archivo físico
        if os.path.exists(self.evento.eve_memorias.path):
            os.remove(self.evento.eve_memorias.path)
        response = self.client.get(reverse('descargar_memorias_asistente', args=[self.evento.pk]))
        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('El archivo de memorias no se encuentra disponible', str(messages[0]))
        
        # Prueba error al abrir el archivo
        self.evento.eve_memorias = SimpleUploadedFile(
            'memorias_error.pdf',
            b'contenido',
            content_type='application/pdf'
        )
        self.evento.save()
        # Hacer el archivo no legible
        os.chmod(self.evento.eve_memorias.path, 0o000)
        response = self.client.get(reverse('descargar_memorias_asistente', args=[self.evento.pk]))
        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('Error al descargar el archivo de memorias', str(messages[0]))

    def test_manual_asistente(self):
        # Prueba descarga exitosa
        response = self.client.get(reverse('manual_asistente'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        
        # Prueba cuando no existe el manual
        manual_path = os.path.join(settings.MEDIA_ROOT, 'manuales', 'MANUAL_ASISTENTE_SISTEMA_EVENTSOFT.pdf')
        if os.path.exists(manual_path):
            os.remove(manual_path)
        response = self.client.get(reverse('manual_asistente'))
        self.assertEqual(response.status_code, 404)

    def tearDown(self):
        # Limpiar archivos creados
        if self.evento.eve_programacion:
            if os.path.exists(self.evento.eve_programacion.path):
                os.remove(self.evento.eve_programacion.path)
                
        if self.evento.eve_memorias:
            if os.path.exists(self.evento.eve_memorias.path):
                os.remove(self.evento.eve_memorias.path)
                
        manual_path = os.path.join(settings.MEDIA_ROOT, 'manuales', 'MANUAL_ASISTENTE_SISTEMA_EVENTSOFT.pdf')
        if os.path.exists(manual_path):
            os.remove(manual_path)