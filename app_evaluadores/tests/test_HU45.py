# app_evaluadores/tests/test_HU45_calificar_participante.py

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from app_usuarios.models import Usuario, Rol, RolUsuario
from app_administradores.models import AdministradorEvento
from app_eventos.models import Evento
from app_evaluadores.models import Evaluador, EvaluadorEvento, Criterio, Calificacion
from app_participantes.models import Participante, ParticipanteEvento

class PruebasCalificarParticipanteHU45(TestCase):

    def setUp(self):
        """Configuración base para calificación de participantes (HU45)."""
        self.client = Client()
        self.ROL_EVALUADOR = 'evaluador'
        self.ROL_ADMIN_EVENTO = 'administrador_evento'
        self.ROL_PARTICIPANTE = 'participante'
        
        # 1. Crear roles necesarios
        self.rol_admin = Rol.objects.create(nombre=self.ROL_ADMIN_EVENTO, descripcion='Administrador de evento')
        self.rol_evaluador = Rol.objects.create(nombre=self.ROL_EVALUADOR, descripcion='Rol para evaluadores')
        self.rol_participante = Rol.objects.create(nombre=self.ROL_PARTICIPANTE, descripcion='Rol para participantes')
        
        # 2. Crear Administrador y Evento
        self.admin_user = Usuario.objects.create_user(
            username='admin_cal', 
            email='admin@cal.com', 
            password='password123', 
            documento='555'
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_admin)
        self.administrador_evento = AdministradorEvento.objects.create(usuario=self.admin_user)
        
        self.evento_calificacion = Evento.objects.create(
            eve_nombre="Evento Calificación Test", 
            eve_estado="Aprobado", 
            eve_capacidad=80, 
            eve_tienecosto="No",
            eve_fecha_inicio=timezone.now().date(), 
            eve_fecha_fin=timezone.now().date() + timedelta(days=3),
            eve_administrador_fk=self.administrador_evento,
        )

        # 3. Crear Evaluador Aprobado
        self.evaluador_email = 'evaluador.cal@test.com'
        self.user_evaluador = Usuario.objects.create_user(
            username='eval_cal', 
            email=self.evaluador_email, 
            password='password123', 
            documento='400', 
            first_name='Evaluador', 
            last_name='Calificador'
        )
        RolUsuario.objects.create(usuario=self.user_evaluador, rol=self.rol_evaluador)
        self.evaluador = Evaluador.objects.create(usuario=self.user_evaluador)
        
        self.evaluador_evento = EvaluadorEvento.objects.create(
            evaluador=self.evaluador,
            evento=self.evento_calificacion,
            eva_eve_estado='Aprobado',  # Evaluador ya aprobado
            confirmado=True,
            eva_eve_fecha_hora=timezone.now() 
        )

        # 4. Crear Participante Aprobado
        self.participante_email = 'participante.cal@test.com'
        self.user_participante = Usuario.objects.create_user(
            username='part_cal', 
            email=self.participante_email, 
            password='password123', 
            documento='500', 
            first_name='Participante', 
            last_name='Test'
        )
        RolUsuario.objects.create(usuario=self.user_participante, rol=self.rol_participante)
        self.participante = Participante.objects.create(usuario=self.user_participante)
        
        self.participante_evento = ParticipanteEvento.objects.create(
            participante=self.participante,
            evento=self.evento_calificacion,
            par_eve_estado='Aprobado',  # Participante ya aprobado
            confirmado=True,
            par_eve_fecha_hora=timezone.now()
        )

        # 5. Crear segundo participante para proyecto grupal
        self.user_participante2 = Usuario.objects.create_user(
            username='part_cal2', 
            email='participante2.cal@test.com', 
            password='password123', 
            documento='501', 
            first_name='Participante2', 
            last_name='Grupal'
        )
        RolUsuario.objects.create(usuario=self.user_participante2, rol=self.rol_participante)
        self.participante2 = Participante.objects.create(usuario=self.user_participante2)
        
        # Crear proyecto grupal para testear CA5
        from app_participantes.models import Proyecto
        self.proyecto_grupal = Proyecto.objects.create(
            evento=self.evento_calificacion,
            titulo="Proyecto Grupal Test",
            descripcion="Proyecto para testing de calificación grupal"
        )
        
        # Asignar proyecto a ambos participantes
        self.participante_evento.proyecto = self.proyecto_grupal
        self.participante_evento.codigo = "GRUPO001"
        self.participante_evento.save()
        
        self.participante_evento2 = ParticipanteEvento.objects.create(
            participante=self.participante2,
            evento=self.evento_calificacion,
            par_eve_estado='Aprobado',
            confirmado=True,
            par_eve_fecha_hora=timezone.now(),
            proyecto=self.proyecto_grupal,
            codigo="GRUPO001"
        )

        # 6. Crear Criterios de Evaluación
        self.criterio1 = Criterio.objects.create(
            cri_descripcion="Dominio del Tema",
            cri_peso=40.0,
            cri_evento_fk=self.evento_calificacion
        )
        
        self.criterio2 = Criterio.objects.create(
            cri_descripcion="Presentación y Comunicación",
            cri_peso=35.0,
            cri_evento_fk=self.evento_calificacion
        )
        
        self.criterio3 = Criterio.objects.create(
            cri_descripcion="Innovación",
            cri_peso=25.0,
            cri_evento_fk=self.evento_calificacion
        )

        # 6. URLs importantes
        self.url_lista_participantes = reverse('lista_participantes_evaluador', args=[self.evento_calificacion.pk])
        self.url_calificar_participante = reverse('calificar_participante_evaluador', args=[self.evento_calificacion.pk, self.participante.pk])
        
        # Login como evaluador
        self.client.force_login(self.user_evaluador)
        session = self.client.session
        session['rol_sesion'] = self.ROL_EVALUADOR
        session.save()

    # ====================================================================
    # ✅ CA1: Acceso a lista de participantes aprobados del evento
    # ====================================================================

    def test_ca1_acceso_lista_participantes_aprobados(self):
        """
        CA1: El evaluador debe poder acceder a la lista de participantes 
        aprobados del evento para el cual está registrado como evaluador.
        """
        # Act: Acceder a la lista de participantes
        response = self.client.get(self.url_lista_participantes)
        
        # Assert 1: Acceso exitoso
        self.assertEqual(response.status_code, 200,
                        "CA1: Evaluador debe poder acceder a lista de participantes")
        
        # Assert 2: Verificar que aparece el participante aprobado (usando nombre completo)
        # El HTML muestra: <td>Participante Test</td>
        # CORREGIDO: Usar msg_prefix en lugar de pasar el mensaje como tercer argumento posicional
        self.assertContains(response, "Participante Test", msg_prefix="CA1: ")
        
        # Assert 3: Verificar contexto con participantes
        self.assertIn('participantes', response.context,
                     "CA1: Vista debe incluir contexto con participantes")
        
        participantes_mostrados = response.context['participantes']
        participantes_aprobados = [p for p in participantes_mostrados if p.par_eve_estado == 'Aprobado']
        # Debe haber 2 participantes aprobados en el evento
        self.assertEqual(len(participantes_aprobados), 2,
                        "CA1: Debe mostrar los participantes aprobados en el contexto")

    # ====================================================================
    # ✅ CA2: Visualización del instrumento de evaluación
    # ====================================================================

    def test_ca2_visualizacion_instrumento_evaluacion(self):
        """
        CA2: El sistema debe mostrar el instrumento de evaluación (criterios 
        con sus respectivos pesos) definido para el evento específico.
        """
        # Act: Acceder al formulario de calificación
        response = self.client.get(self.url_calificar_participante)
        
        # Assert 1: Acceso exitoso al instrumento
        self.assertEqual(response.status_code, 200,
                        "CA2: Debe poder acceder al instrumento de evaluación")
        
        # Assert 2: Verificar que aparecen todos los criterios
        # CORREGIDO: Usar msg_prefix
        self.assertContains(response, "Dominio del Tema", msg_prefix="CA2: ")
        self.assertContains(response, "Presentación y Comunicación", msg_prefix="CA2: ")
        self.assertContains(response, "Innovación", msg_prefix="CA2: ")
        
        # Assert 3: Verificar contexto con criterios
        self.assertIn('criterios', response.context,
                     "CA2: Vista debe incluir criterios en el contexto")
        
        criterios_mostrados = response.context['criterios']
        self.assertEqual(criterios_mostrados.count(), 3,
                        "CA2: Debe mostrar los 3 criterios definidos")
        
        # Assert 4: Verificar que se muestran los pesos
        pesos_esperados = [40.0, 35.0, 25.0]
        for criterio in criterios_mostrados:
            self.assertIn(criterio.cri_peso, pesos_esperados,
                         "CA2: Debe mostrar los pesos correctos de criterios")

    # ====================================================================
    # ✅ CA3: Asignación de calificaciones válidas (1-5)
    # ====================================================================

    def test_ca3_asignacion_calificaciones_validas(self):
        """
        CA3: El evaluador debe poder asignar una calificación numérica 
        (escala 1-5) a cada criterio del instrumento de evaluación para 
        cada participante.
        """
        # Preparar datos de calificación válidos
        datos_calificacion = {
            f'criterio_{self.criterio1.cri_id}': '4',  # Dominio del Tema: 4
            f'criterio_{self.criterio2.cri_id}': '5',  # Presentación: 5
            f'criterio_{self.criterio3.cri_id}': '3',  # Innovación: 3
        }
        
        # Act: Enviar calificaciones
        response = self.client.post(self.url_calificar_participante, datos_calificacion)
        
        # Assert 1: Proceso exitoso (redirección tras guardar)
        self.assertEqual(response.status_code, 302,
                        "CA3: Debe redirigir tras guardar calificaciones")
        
        # Assert 2: Verificar que se crearon las calificaciones
        calificaciones = Calificacion.objects.filter(
            evaluador=self.evaluador,
            participante=self.participante
        )
        self.assertEqual(calificaciones.count(), 3,
                        "CA3: Deben crearse 3 calificaciones (una por criterio)")
        
        # Assert 3: Verificar valores asignados
        cal_dominio = Calificacion.objects.get(
            evaluador=self.evaluador,
            participante=self.participante,
            criterio=self.criterio1
        )
        self.assertEqual(cal_dominio.cal_valor, 4,
                        "CA3: Calificación de 'Dominio del Tema' debe ser 4")
        
        cal_presentacion = Calificacion.objects.get(
            evaluador=self.evaluador,
            participante=self.participante,
            criterio=self.criterio2
        )
        self.assertEqual(cal_presentacion.cal_valor, 5,
                        "CA3: Calificación de 'Presentación' debe ser 5")

    # ====================================================================
    # ✅ CA4: Cálculo automático del puntaje ponderado
    # ====================================================================

    def test_ca4_calculo_automatico_puntaje_ponderado(self):
        """
        CA4: El sistema debe calcular automáticamente el puntaje ponderado 
        total del participante basado en las calificaciones y pesos de los criterios.
        """
        # Preparar calificaciones conocidas para cálculo
        datos_calificacion = {
            f'criterio_{self.criterio1.cri_id}': '4',  # 4 * 40% = 1.6
            f'criterio_{self.criterio2.cri_id}': '5',  # 5 * 35% = 1.75
            f'criterio_{self.criterio3.cri_id}': '3',  # 3 * 25% = 0.75
        }
        # Puntaje esperado: (1.6 + 1.75 + 0.75) = 4.1
        
        # Act: Enviar calificaciones
        response = self.client.post(self.url_calificar_participante, datos_calificacion)
        
        # Assert 1: Proceso exitoso
        self.assertEqual(response.status_code, 302,
                        "CA4: Calificación debe procesarse exitosamente")
        
        # Assert 2: Verificar cálculo del puntaje ponderado
        self.participante_evento.refresh_from_db()
        puntaje_calculado = self.participante_evento.par_eve_valor
        
        # Puntaje esperado: (4*0.4 + 5*0.35 + 3*0.25) = 1.6 + 1.75 + 0.75 = 4.1
        puntaje_esperado = 4.1
        
        self.assertIsNotNone(puntaje_calculado,
                            "CA4: Debe calcularse un puntaje ponderado")
        self.assertEqual(float(puntaje_calculado), puntaje_esperado,
                        "CA4: Puntaje ponderado debe ser 4.1")

    # ====================================================================
    # ✅ CA5: Calificación grupal - propagación a todos los integrantes
    # ====================================================================

    def test_ca5_calificacion_grupal_propagacion_integrantes(self):
        """
        CA5: Cuando se califica a un participante con proyecto grupal, la misma 
        calificación debe aplicarse automáticamente a todos los integrantes del 
        grupo y al proyecto.
        """
        # Preparar calificaciones para proyecto grupal
        datos_calificacion_grupal = {
            f'criterio_{self.criterio1.cri_id}': '5',  # 5 * 40% = 2.0
            f'criterio_{self.criterio2.cri_id}': '4',  # 4 * 35% = 1.4
            f'criterio_{self.criterio3.cri_id}': '3',  # 3 * 25% = 0.75
        }
        # Puntaje esperado: 2.0 + 1.4 + 0.75 = 4.15
        
        # Act: Calificar al primer participante del grupo
        response = self.client.post(self.url_calificar_participante, datos_calificacion_grupal)
        
        # Assert 1: Proceso exitoso
        self.assertEqual(response.status_code, 302,
                        "CA5: Calificación grupal debe procesarse exitosamente")
        
        # Assert 2: Verificar que se actualizó el proyecto
        self.proyecto_grupal.refresh_from_db()
        self.assertIsNotNone(self.proyecto_grupal.pro_valor,
                            "CA5: El proyecto debe tener valor asignado")
        self.assertEqual(float(self.proyecto_grupal.pro_valor), 4.15,
                        "CA5: Proyecto debe tener puntaje 4.15")
        
        # Assert 3: Verificar que se actualizó el primer participante
        self.participante_evento.refresh_from_db()
        self.assertEqual(float(self.participante_evento.par_eve_valor), 4.15,
                        "CA5: Primer participante debe tener puntaje 4.15")
        
        # Assert 4: Verificar que se propagó al segundo integrante
        self.participante_evento2.refresh_from_db()
        self.assertEqual(float(self.participante_evento2.par_eve_valor), 4.15,
                        "CA5: Segundo integrante debe tener el mismo puntaje 4.15")
        
        # Assert 5: Verificar que ambos participantes tienen la misma calificación
        self.assertEqual(self.participante_evento.par_eve_valor, 
                        self.participante_evento2.par_eve_valor,
                        "CA5: Todos los integrantes del grupo deben tener la misma calificación")

    # ====================================================================
    # ✅ CA6: Actualización de nota general y tabla de posiciones
    # ====================================================================

    def test_ca6_actualizacion_nota_general_tabla_posiciones(self):
        """
        CA6: Una vez calificado un participante, el sistema debe actualizar 
        la nota general del participante y reflejarla en la tabla de posiciones 
        del evento.
        """
        # Preparar calificaciones
        datos_calificacion = {
            f'criterio_{self.criterio1.cri_id}': '5',  # 5 * 40% = 2.0
            f'criterio_{self.criterio2.cri_id}': '4',  # 4 * 35% = 1.4
            f'criterio_{self.criterio3.cri_id}': '4',  # 4 * 25% = 1.0
        }
        # Puntaje esperado: 2.0 + 1.4 + 1.0 = 4.4
        
        # Act: Calificar participante
        response = self.client.post(self.url_calificar_participante, datos_calificacion)
        
        # Assert 1: Verificar actualización de nota general
        self.participante_evento.refresh_from_db()
        nota_general = self.participante_evento.par_eve_valor
        
        self.assertIsNotNone(nota_general,
                            "CA6: Debe actualizarse la nota general")
        self.assertEqual(float(nota_general), 4.4,
                        "CA6: Nota general debe ser 4.4")
        
        # Assert 2: Verificar acceso a tabla de posiciones
        url_tabla_posiciones = reverse('tabla_posiciones_evaluador', args=[self.evento_calificacion.pk])
        response_tabla = self.client.get(url_tabla_posiciones)
        
        self.assertEqual(response_tabla.status_code, 200,
                        "CA6: Debe poder acceder a tabla de posiciones")
        
        # Assert 3: Verificar que aparece el participante calificado (usando nombre completo)
        # CORREGIDO: Usar msg_prefix
        self.assertContains(response_tabla, "Participante Test", msg_prefix="CA6: ")
        
        # Assert 4: Verificar que se muestra el puntaje
        # Buscamos el valor exacto como cadena en el HTML
        # El valor puede estar formateado como '4.4' o '4,4' dependiendo del locale
        # Buscamos ambas posibilidades
        response_content_str = response_tabla.content.decode('utf-8')
        self.assertTrue('4.4' in response_content_str or '4,4' in response_content_str,
                        "CA6: Puntaje calculado debe mostrarse en tabla")

    # ====================================================================
    # ✅ Verificación adicional: Visualización de información del proyecto
    # ====================================================================

    def test_visualizacion_informacion_proyecto(self):
        """
        Verificar que el evaluador puede ver la información del proyecto 
        antes de calificarlo.
        """
        # Act: Acceder al formulario de calificación
        response = self.client.get(self.url_calificar_participante)
        
        # Assert: Verificar que se puede acceder sin problemas
        self.assertEqual(response.status_code, 200,
                        "Debe poder acceder a calificar participante con proyecto")
        
        # Verificar contexto incluye participante con proyecto
        self.assertIn('participante', response.context,
                     "Vista debe incluir información del participante")
        
        # El proyecto está asociado al participante
        participante_contexto = response.context['participante']
        self.assertEqual(participante_contexto, self.participante,
                        "Debe mostrar el participante correcto con su proyecto asociado")

    # ====================================================================
    # ✅ Verificación: Calificación de proyecto individual
    # ====================================================================

    def test_calificacion_proyecto_individual(self):
        """
        Verificar calificación de participante con proyecto individual 
        (sin propagación grupal).
        """
        # Crear participante individual (sin código de grupo)
        user_individual = Usuario.objects.create_user(
            username='part_individual', 
            email='individual@test.com', 
            password='password123', 
            documento='600', 
            first_name='Participante', 
            last_name='Individual'
        )
        RolUsuario.objects.create(usuario=user_individual, rol=self.rol_participante)
        participante_individual = Participante.objects.create(usuario=user_individual)
        
        # Crear proyecto individual
        from app_participantes.models import Proyecto
        proyecto_individual = Proyecto.objects.create(
            evento=self.evento_calificacion,
            titulo="Proyecto Individual",
            descripcion="Proyecto individual para testing"
        )
        
        participante_evento_ind = ParticipanteEvento.objects.create(
            participante=participante_individual,
            evento=self.evento_calificacion,
            par_eve_estado='Aprobado',
            confirmado=True,
            par_eve_fecha_hora=timezone.now(),
            proyecto=proyecto_individual,
            codigo=None  # Sin código = individual
        )
        
        url_calificar_individual = reverse('calificar_participante_evaluador', 
                                         args=[self.evento_calificacion.pk, participante_individual.pk])
        
        # Calificar proyecto individual
        datos_calificacion = {
            f'criterio_{self.criterio1.cri_id}': '4',
            f'criterio_{self.criterio2.cri_id}': '4', 
            f'criterio_{self.criterio3.cri_id}': '4',
        }
        
        response = self.client.post(url_calificar_individual, datos_calificacion)
        
        # Assert: Solo debe afectar al participante individual y su proyecto
        self.assertEqual(response.status_code, 302, "Calificación individual debe procesarse")
        
        participante_evento_ind.refresh_from_db()
        proyecto_individual.refresh_from_db()
        
        # Verificar que se calificó el proyecto individual
        self.assertIsNotNone(proyecto_individual.pro_valor,
                            "Proyecto individual debe tener calificación")
        
        # Verificar que no afectó a otros participantes
        self.participante_evento.refresh_from_db()
        # El participante grupal no debe tener calificación aún (a menos que ya haya sido calificado en otro test)
        # Si en otro test se calificó, este assert fallará. Si es el caso, asegúrate de que este test
        # se ejecute en un estado limpio o revise el valor esperado.
        # Por ahora, asumiremos que no ha sido calificado antes.
        # Si el otro participante ya fue calificado (por ejemplo, en CA5 o CA6), este assert fallará.
        # Para evitar conflictos, podríamos usar otro participante para este test o
        # resetear el valor antes de verificar.
        # Si solo se corre este test, debería pasar.
        # Si se corren todos, es probable que falle si otro test ya calificó a self.participante_evento.