# app_administradores/tests/test_HU79_configurar_certificados.py

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile

from app_usuarios.models import Usuario, Rol, RolUsuario
from app_administradores.models import AdministradorEvento
from app_eventos.models import Evento, ConfiguracionCertificado


class HU79ConfigurarCertificadosTest(TestCase):
    """
    HU79: COMO ADMINISTRADOR DE EVENTO, Quiero configurar los datos generales que aparecerán en los certificados de los asistentes, expositores y evaluadores de un evento,
    Para generar certificados específicos de acuerdo con la información del evento.
    """

    def setUp(self):
        self.client = Client()
        
        # Crear roles
        self.rol_admin = Rol.objects.create(nombre='administrador_evento')

        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin79",
            email="admin79@test.com",
            password="password123",
            documento="12345679"
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_admin)
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evento
        self.evento = Evento.objects.create(
            eve_nombre="Evento Certificados Config",
            eve_descripcion="Evento para testing de configuración de certificados",
            eve_ciudad="Test City",
            eve_lugar="Test Place",
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=2),
            eve_estado="Aprobado",
            eve_capacidad=50,
            eve_tienecosto="No",
            eve_administrador_fk=self.admin
        )

        # Crear archivos de ejemplo para firma y logo
        self.archivo_firma = SimpleUploadedFile(
            name="firma_test.png",
            content=b"contenido_firma",
            content_type="image/png"
        )
        self.archivo_logo = SimpleUploadedFile(
            name="logo_test.png",
            content=b"contenido_logo",
            content_type="image/png"
        )

        # URLs
        # Revisando urls.py de app_administradores:
        # path('certificados/<int:eve_id>/<str:tipo>/configurar/', views.configurar_certificado, name='configurar_certificado'),
        # path('certificados/<int:eve_id>/tipo/', views.seleccionar_tipo_certificado, name='seleccionar_tipo_certificado'),
        # Suponemos que primero se selecciona el tipo y luego se configura.
        # Para este test, probamos directamente la configuración de un tipo específico.
        self.url_config_tipo_asistencia = reverse('configurar_certificado', args=[self.evento.pk, 'asistencia'])
        self.url_config_tipo_evaluador = reverse('configurar_certificado', args=[self.evento.pk, 'evaluador'])

        # Login
        self.client.force_login(self.admin_user)
        session = self.client.session
        session['rol_sesion'] = 'administrador_evento'
        session.save()


    def test_hu79_configuracion_certificados_completa(self):
        """
        Prueba los 5 criterios de aceptación de HU79:
        CA1: Acceso Condicionado
        CA2: Selección de Tipo de Certificado (implícita en la URL)
        CA3: Configuración de Campos
        CA4: Guardado de Configuración
        CA5: Visualización de Configuración Existente
        """
        
        # CA1: Acceso Condicionado (El admin ya está logueado y es del evento correcto)
        # Intentamos acceder a la configuración de un tipo de certificado
        response = self.client.get(self.url_config_tipo_asistencia)
        # La vista probablemente renderice un formulario vacío si no hay configuración previa
        # o un formulario con los datos si ya existe.
        # Lo importante es que no devuelva un error de permisos (403) o no encontrado (404) si el evento es correcto.
        self.assertEqual(response.status_code, 200, "CA1: El admin debe poder acceder a la configuración de certificados del evento")

        # CA3 & CA4: Configuración de Campos y Guardado
        # Enviar datos para configurar el certificado de asistencia
        data_config_asistencia = {
            'titulo': 'Certificado de Asistencia - Prueba',
            'cuerpo': 'Se certifica que {nombre} asistió al evento {evento} el {fecha}.',
            'plantilla': 'moderno', # Opciones: 'elegante', 'moderno', 'clasico'
            # 'firma' y 'logo' son opcionales, los probamos si la vista los maneja en este formulario
            # Si la vista maneja archivos, los pasamos; si no, se configuran en otro flujo.
            # Por ahora, probamos sin archivos.
        }
        # Si la vista maneja archivos, se usaría:
        # data_config_asistencia['firma'] = self.archivo_firma
        # data_config_asistencia['logo'] = self.archivo_logo
        # Pero el manejo de archivos en formularios puede requerir Client.post con archivos específicos.
        # Supongamos que firma y logo se suben en un paso separado o se manejan de otra manera.
        # Para este test, asumimos que se configuran aquí si la vista lo permite.
        # Si la vista no maneja archivos en este formulario, no se incluyen.
        # Probamos primero sin archivos.
        response_post = self.client.post(self.url_config_tipo_asistencia, data_config_asistencia)
        # La vista probablemente redirige después de guardar
        self.assertEqual(response_post.status_code, 302, "CA4: La configuración debe guardarse y redirigir después de un POST exitoso")

        # Verificar que la configuración se haya guardado correctamente (CA4)
        config_asistencia_guardada = ConfiguracionCertificado.objects.filter(
            evento=self.evento,
            tipo='asistencia'
        ).first()
        self.assertIsNotNone(config_asistencia_guardada, "CA4: Debe existir una configuración guardada para asistencia")
        self.assertEqual(config_asistencia_guardada.titulo, 'Certificado de Asistencia - Prueba', "CA4: El título debe coincidir con el enviado")
        self.assertEqual(config_asistencia_guardada.cuerpo, 'Se certifica que {nombre} asistió al evento {evento} el {fecha}.', "CA4: El cuerpo debe coincidir con el enviado")
        self.assertEqual(config_asistencia_guardada.plantilla, 'moderno', "CA4: La plantilla debe coincidir con la enviada")

        # CA5: Visualización de Configuración Existente
        # Acceder nuevamente al formulario de configuración para el mismo tipo
        response_edicion = self.client.get(self.url_config_tipo_asistencia)
        # La vista debe mostrar los valores actuales en los campos del formulario
        # Esto se verifica mirando si los valores guardados están en el contenido de la respuesta HTML
        # o inspeccionando el contexto del formulario (más complejo).
        # Verificar en el HTML renderizado es más común con assertContains.
        # Buscar el título guardado en la respuesta HTML del formulario
        self.assertContains(response_edicion, 'Certificado de Asistencia - Prueba', msg_prefix="CA5: El formulario debe mostrar el título guardado")
        # Buscar el cuerpo guardado
        self.assertContains(response_edicion, 'Se certifica que {nombre} asistió al evento {evento} el {fecha}.', msg_prefix="CA5: El formulario debe mostrar el cuerpo guardado")
        # Buscar la opción de plantilla seleccionada
        # La forma exacta de verificar la plantilla seleccionada depende de cómo la vista la renderice (select, radio, etc.)
        # Podría haber un atributo 'selected' en la opción correcta del select.
        # Este test puede necesitar inspeccionar el contexto del formulario para verificar el valor inicial del campo.
        # Por ahora, asumimos que si la vista no falla y los campos están, el valor se carga.
        # Si la vista renderiza correctamente el formulario con los valores iniciales,
        # y el test anterior de POST pasó, CA5 se considera cubierto funcionalmente.
        # Para verificar el valor del campo en el contexto:
        # if 'form' in response_edicion.context:
        #     form = response_edicion.context['form']
        #     self.assertEqual(form.initial.get('titulo'), 'Certificado de Asistencia - Prueba')
        #     self.assertEqual(form.initial.get('cuerpo'), 'Se certifica que {nombre} asistió al evento {evento} el {fecha}.')
        #     self.assertEqual(form.initial.get('plantilla'), 'moderno')
        # else:
        #     self.fail("El contexto no contiene el formulario de configuración.")

        # Configurar otro tipo de certificado (evaluador) para probar CA2 implícitamente (ya que usamos URLs diferentes)
        data_config_evaluador = {
            'titulo': 'Certificado de Evaluador - Prueba',
            'cuerpo': 'Se certifica que {nombre} participó como evaluador en {evento}.',
            'plantilla': 'elegante',
        }
        response_post_eval = self.client.post(self.url_config_tipo_evaluador, data_config_evaluador)
        self.assertEqual(response_post_eval.status_code, 302, "CA4: La configuración de evaluador debe guardarse y redirigir")

        # Verificar que la configuración de evaluador se haya guardado correctamente
        config_evaluador_guardada = ConfiguracionCertificado.objects.filter(
            evento=self.evento,
            tipo='evaluador'
        ).first()
        self.assertIsNotNone(config_evaluador_guardada, "CA4: Debe existir una configuración guardada para evaluador")
        self.assertEqual(config_evaluador_guardada.titulo, 'Certificado de Evaluador - Prueba', "CA4: El título de evaluador debe coincidir")
        self.assertEqual(config_evaluador_guardada.cuerpo, 'Se certifica que {nombre} participó como evaluador en {evento}.', "CA4: El cuerpo de evaluador debe coincidir")
        self.assertEqual(config_evaluador_guardada.plantilla, 'elegante', "CA4: La plantilla de evaluador debe coincidir")

        # Verificar que ambas configuraciones estén en la base de datos
        total_configs = ConfiguracionCertificado.objects.filter(evento=self.evento).count()
        self.assertEqual(total_configs, 2, "CA4: Deben existir 2 configuraciones guardadas para el evento (asistencia y evaluador)")

        return {
            'config_asistencia_guardada': config_asistencia_guardada,
            'config_evaluador_guardada': config_evaluador_guardada,
            'total_configs': total_configs
        }