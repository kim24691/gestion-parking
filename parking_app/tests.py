import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from parking_app.models import (
    CustomUser, ParkingZone, VehicleType, Tariff, ParkingTicket, ActivityLog
)
from parking_app.utils import generate_ticket_number

class ParkingSystemAcademicTests(TestCase):
    """
    Tests académiques complets validant le respect du cahier des charges :
    - Rôles (Admin vs Agent)
    - Traçabilité (ActivityLog / Audit Trail)
    - CRUD & calculs de stationnement en BIF
    - Rapports et PDF
    """

    def setUp(self):
        self.client = Client()

        # 1. Utilisateurs
        self.admin_user = CustomUser.objects.create_superuser(
            username='admin_test',
            password='password123',
            role='ADMIN',
            badge_id='ADM-001'
        )

        self.agent_user = CustomUser.objects.create_user(
            username='agent_test',
            password='password123',
            role='AGENT',
            badge_id='AGT-001'
        )

        # 2. Zone de parking
        self.zone_rohero = ParkingZone.objects.create(
            name="Rohero",
            code="ROH",
            description="Boulevard de l'Indépendance",
            total_spots=10,
            hourly_rate_default=1000,
            is_active=True
        )

        # 3. Type de véhicule
        self.veh_voiture = VehicleType.objects.create(
            code="VOITURE",
            name="Voiture de tourisme",
            icon_class="fa-car",
            default_hourly_rate=1000,
            default_daily_rate=6000,
            is_active=True
        )

        # 4. Tarif
        self.tariff_hourly = Tariff.objects.create(
            vehicle_type=self.veh_voiture,
            zone=self.zone_rohero,
            tariff_type='HOURLY',
            amount_bif=1000,
            grace_period_minutes=15,
            is_active=True
        )

    def test_zone_availability_calculation(self):
        """Vérifie le calcul dynamique des places libres et occupées dans une zone"""
        self.assertEqual(self.zone_rohero.get_occupied_spots(), 0)
        self.assertEqual(self.zone_rohero.get_available_spots(), 10)
        self.assertEqual(self.zone_rohero.get_occupancy_rate(), 0)

        # Création d'un ticket en cours
        ticket = ParkingTicket.objects.create(
            ticket_number=generate_ticket_number(),
            plate_number="RA 1234 B",
            vehicle_type=self.veh_voiture,
            zone=self.zone_rohero,
            created_by=self.agent_user,
            status='EN_COURS',
            is_active=True
        )

        self.assertEqual(self.zone_rohero.get_occupied_spots(), 1)
        self.assertEqual(self.zone_rohero.get_available_spots(), 9)
        self.assertEqual(self.zone_rohero.get_occupancy_rate(), 10.0)

    def test_ticket_billing_calculation(self):
        """Vérifie la période de grâce de 15 min et la tarification par heure entamée en BIF"""
        ticket = ParkingTicket.objects.create(
            ticket_number=generate_ticket_number(),
            plate_number="IT 4520 A",
            vehicle_type=self.veh_voiture,
            zone=self.zone_rohero,
            created_by=self.agent_user,
            status='EN_COURS',
            is_active=True
        )

        # Simulation 1 : sortie après 10 minutes (période de grâce de 15 min -> 0 BIF)
        simulated_time_10m = ticket.entry_time + datetime.timedelta(minutes=10)
        mins, bill = ticket.calculate_bill(current_time=simulated_time_10m)
        self.assertEqual(mins, 10)
        self.assertEqual(bill, 0)

        # Simulation 2 : sortie après 45 minutes (1 heure entamée -> 1000 BIF)
        simulated_time_45m = ticket.entry_time + datetime.timedelta(minutes=45)
        mins, bill = ticket.calculate_bill(current_time=simulated_time_45m)
        self.assertEqual(mins, 45)
        self.assertEqual(bill, 1000)

        # Simulation 3 : sortie après 2h10 (3 heures entamées -> 3000 BIF)
        simulated_time_2h10 = ticket.entry_time + datetime.timedelta(hours=2, minutes=10)
        mins, bill = ticket.calculate_bill(current_time=simulated_time_2h10)
        self.assertEqual(mins, 130)
        self.assertEqual(bill, 3000)

    def test_authentication_and_audit_trail(self):
        """Vérifie la connexion utilisateur et la création d'une entrée d'audit"""
        response = self.client.post(reverse('login'), {
            'username': 'agent_test',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))

        # Vérification dans l'ActivityLog
        log = ActivityLog.objects.filter(user=self.agent_user, action='CONNEXION').first()
        self.assertIsNotNone(log)
        self.assertIn("Connexion", log.details)

    def test_vehicle_entry_flow(self):
        """Vérifie le formulaire d'enregistrement de l'entrée d'un véhicule"""
        self.client.login(username='agent_test', password='password123')

        response = self.client.post(reverse('ticket_entry'), {
            'plate_number': 'ra 9999 c',  # Doit être nettoyé en majuscule
            'vehicle_type': self.veh_voiture.id,
            'zone': self.zone_rohero.id,
        })
        self.assertEqual(response.status_code, 302)

        ticket = ParkingTicket.objects.filter(plate_number='RA 9999 C').first()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.status, 'EN_COURS')
        self.assertEqual(ticket.created_by, self.agent_user)
        self.assertTrue(ticket.ticket_number.startswith('BJM-'))

        # Vérification de l'Audit Log pour l'entrée
        audit = ActivityLog.objects.filter(
            action='ENTREE_VEHICULE',
            target_id=str(ticket.id)
        ).first()
        self.assertIsNotNone(audit)

    def test_vehicle_checkout_flow(self):
        """Vérifie la clôture de stationnement, encaissement en BIF et libération de place"""
        # Création préalable du ticket
        entry_time = timezone.now() - datetime.timedelta(hours=2)
        ticket = ParkingTicket.objects.create(
            ticket_number=generate_ticket_number(),
            plate_number="D 5555 A",
            vehicle_type=self.veh_voiture,
            zone=self.zone_rohero,
            entry_time=entry_time,
            created_by=self.agent_user,
            status='EN_COURS',
            is_active=True
        )

        self.client.login(username='agent_test', password='password123')

        response = self.client.post(reverse('ticket_checkout', args=[ticket.id]), {
            'payment_method': 'LUMICASH',
            'payment_reference': 'TXN-LUMI-12345',
            'amount_paid': 2000,
        })
        self.assertEqual(response.status_code, 302)

        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'PAYE')
        self.assertEqual(ticket.closed_by, self.agent_user)
        self.assertEqual(ticket.amount_paid, 2000)
        self.assertEqual(ticket.payment_method, 'LUMICASH')
        self.assertIsNotNone(ticket.exit_time)

        # Vérification Audit Log
        audit = ActivityLog.objects.filter(
            action='SORTIE_PAIEMENT',
            target_id=str(ticket.id)
        ).first()
        self.assertIsNotNone(audit)

    def test_ticket_logical_deactivation(self):
        """Vérifie la désactivation logique avec motif obligatoire"""
        ticket = ParkingTicket.objects.create(
            ticket_number=generate_ticket_number(),
            plate_number="C 7777 B",
            vehicle_type=self.veh_voiture,
            zone=self.zone_rohero,
            created_by=self.agent_user,
            status='EN_COURS',
            is_active=True
        )

        self.client.login(username='agent_test', password='password123')

        response = self.client.post(reverse('ticket_deactivate', args=[ticket.id]), {
            'cancellation_reason': 'Erreur de saisie de plaque par l\'agent',
        })
        self.assertEqual(response.status_code, 302)

        ticket.refresh_from_db()
        self.assertFalse(ticket.is_active)
        self.assertEqual(ticket.status, 'ANNULE')
        self.assertEqual(ticket.cancellation_reason, 'Erreur de saisie de plaque par l\'agent')

    def test_admin_access_control(self):
        """Vérifie que les vues sensibles sont réservées à l'administrateur"""
        # Un agent essaie d'accéder à la liste des utilisateurs
        self.client.login(username='agent_test', password='password123')
        resp_agent = self.client.get(reverse('user_list'))
        self.assertEqual(resp_agent.status_code, 302) # Redirigé car refusé

        # L'admin y accède sans problème
        self.client.login(username='admin_test', password='password123')
        resp_admin = self.client.get(reverse('user_list'))
        self.assertEqual(resp_admin.status_code, 200)

    def test_financial_report_and_pdf_export(self):
        """Vérifie le rapport financier des recettes et l'export PDF"""
        # Création d'un ticket payé
        ParkingTicket.objects.create(
            ticket_number=generate_ticket_number(),
            plate_number="RA 0001 A",
            vehicle_type=self.veh_voiture,
            zone=self.zone_rohero,
            entry_time=timezone.now() - datetime.timedelta(hours=1),
            exit_time=timezone.now(),
            duration_minutes=60,
            amount_due=1000,
            amount_paid=1000,
            payment_method='ESPECES',
            closed_by=self.admin_user,
            status='PAYE',
            is_active=True
        )

        self.client.login(username='admin_test', password='password123')

        # 1. Vue Web
        resp_web = self.client.get(reverse('report_financial'))
        self.assertEqual(resp_web.status_code, 200)
        self.assertContains(resp_web, "Rohero")
        self.assertContains(resp_web, "BIF")

        # 2. Export PDF
        resp_pdf = self.client.get(reverse('report_financial') + '?export=pdf')
        self.assertEqual(resp_pdf.status_code, 200)
        self.assertEqual(resp_pdf['Content-Type'], 'application/pdf')
        self.assertTrue(len(resp_pdf.content) > 100)

    def test_language_switch_and_i18n(self):
        """Vérifie le sélecteur de langue i18n et les traductions Kirundi et Anglais"""
        self.client.login(username='admin_test', password='password123')

        # 1. Bascule vers le Kirundi (rn)
        resp_switch_rn = self.client.post(reverse('set_language'), {
            'language': 'rn',
            'next': reverse('dashboard')
        })
        self.assertEqual(resp_switch_rn.status_code, 302)

        # Vérification sur le dashboard avec langue Kirundi
        resp_dashboard_rn = self.client.get(reverse('dashboard'))
        self.assertEqual(resp_dashboard_rn.status_code, 200)
        self.assertContains(resp_dashboard_rn, "Ikibaho Nyamukuru")

        # 2. Bascule vers l'Anglais (en)
        resp_switch_en = self.client.post(reverse('set_language'), {
            'language': 'en',
            'next': reverse('dashboard')
        })
        self.assertEqual(resp_switch_en.status_code, 302)

        # Vérification sur le dashboard avec langue Anglais
        resp_dashboard_en = self.client.get(reverse('dashboard'))
        self.assertEqual(resp_dashboard_en.status_code, 200)
        self.assertContains(resp_dashboard_en, "Dashboard")

