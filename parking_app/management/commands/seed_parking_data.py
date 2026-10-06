import datetime
import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from parking_app.models import (
    CustomUser, ParkingZone, VehicleType, Tariff, ParkingTicket, ActivityLog
)
from parking_app.utils import generate_ticket_number

class Command(BaseCommand):
    help = "Peuple la base de données avec des données de démonstration réalistes pour la Ville de Bujumbura"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("== Initialisation des données de parking (Bujumbura, Burundi) =="))

        # 1. Création des Zones de Parking demandées
        zones_data = [
            {
                'name': "Centre-Ville",
                'code': "CV",
                'description': "Avenue de l'Uprona, Boulevard Patrice Lumumba et artères centrales",
                'total_spots': 120,
                'hourly_rate_default': 1000,
            },
            {
                'name': "Rohero",
                'code': "ROH",
                'description': "Boulevard de l'Indépendance, Avenue de France, quartier administratif et résidentiel",
                'total_spots': 85,
                'hourly_rate_default': 1000,
            },
            {
                'name': "Place de l'Indépendance",
                'code': "PLI",
                'description': "Rond-point central de l'Indépendance et parkings périphériques de la Place",
                'total_spots': 150,
                'hourly_rate_default': 1500,
            },
            {
                'name': "Marché Central",
                'code': "MC",
                'description': "Zone commerciale entourant le Grand Marché et les galeries marchandes",
                'total_spots': 200,
                'hourly_rate_default': 1000,
            },
            {
                'name': "Asian",
                'code': "ASI",
                'description': "Quartier Asiatique, Avenue du Commerce, zone commerciale dense",
                'total_spots': 60,
                'hourly_rate_default': 1200,
            },
        ]

        created_zones = {}
        for z in zones_data:
            zone, created = ParkingZone.objects.get_or_create(
                code=z['code'],
                defaults=z
            )
            created_zones[z['code']] = zone
            status = "Créée" if created else "Existante"
            self.stdout.write(f"  [Zone] {zone.name} ({zone.code}) - {status}")

        # 2. Types de Véhicules
        veh_types_data = [
            {
                'code': 'VOITURE',
                'name': 'Voiture de tourisme',
                'icon_class': 'fa-car',
                'default_hourly_rate': 1000,
                'default_daily_rate': 6000,
                'description': 'Berlines, SUV, taxis, citadines légères',
            },
            {
                'code': 'MOTO',
                'name': 'Motocyclette & Bajaj',
                'icon_class': 'fa-motorcycle',
                'default_hourly_rate': 500,
                'default_daily_rate': 3000,
                'description': 'Motos deux-roues et tricycles motorisés',
            },
            {
                'code': 'BUS',
                'name': 'Minibus & Bus Hiace/Coaster',
                'icon_class': 'fa-bus',
                'default_hourly_rate': 2000,
                'default_daily_rate': 12000,
                'description': 'Véhicules de transport collectif de passagers',
            },
            {
                'code': 'CAMION',
                'name': 'Camion & Poids Lourd',
                'icon_class': 'fa-truck',
                'default_hourly_rate': 3000,
                'default_daily_rate': 18000,
                'description': 'Camions de livraison, bennes et remorques',
            },
        ]

        created_vtypes = {}
        for vt in veh_types_data:
            vtype, created = VehicleType.objects.get_or_create(
                code=vt['code'],
                defaults=vt
            )
            created_vtypes[vt['code']] = vtype
            self.stdout.write(f"  [Type Véhicule] {vtype.name} - Tarif: {vtype.default_hourly_rate} BIF/h")

        # 3. Grille Tarifaire par défaut
        for vt_code, vtype in created_vtypes.items():
            Tariff.objects.get_or_create(
                vehicle_type=vtype,
                zone=None,
                tariff_type='HOURLY',
                defaults={
                    'amount_bif': vtype.default_hourly_rate,
                    'grace_period_minutes': 15,
                    'max_daily_cap_bif': vtype.default_daily_rate,
                    'is_active': True
                }
            )
            Tariff.objects.get_or_create(
                vehicle_type=vtype,
                zone=None,
                tariff_type='DAILY',
                defaults={
                    'amount_bif': vtype.default_daily_rate,
                    'grace_period_minutes': 0,
                    'is_active': True
                }
            )

        # 4. Comptes Utilisateurs (Administrateur & Agents de parking)
        # Compte Super Administrateur
        admin_user, created = CustomUser.objects.get_or_create(
            username='admin',
            defaults={
                'first_name': 'Dieudonné',
                'last_name': 'Nkurunziza',
                'email': 'admin@mairie-bujumbura.bi',
                'role': 'ADMIN',
                'badge_id': 'ADM-BJM-001',
                'phone': '+257 79 111 222',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("  [User] Administrateur 'admin' créé (Mot de passe: admin123)"))

        # Compte Agent Rohero
        agent_rohero, created = CustomUser.objects.get_or_create(
            username='agent_rohero',
            defaults={
                'first_name': 'Jean-Paul',
                'last_name': 'Ndikumasabo',
                'email': 'jp.rohero@mairie-bujumbura.bi',
                'role': 'AGENT',
                'badge_id': 'AGT-ROH-01',
                'phone': '+257 79 333 444',
                'assigned_zone': created_zones['ROH'],
            }
        )
        if created:
            agent_rohero.set_password('agent123')
            agent_rohero.save()
            self.stdout.write(self.style.SUCCESS("  [User] Agent 'agent_rohero' créé (Mot de passe: agent123)"))

        # Compte Agent Centre-Ville
        agent_centre, created = CustomUser.objects.get_or_create(
            username='agent_centre',
            defaults={
                'first_name': 'Aline',
                'last_name': 'Iradukunda',
                'email': 'aline.centre@mairie-bujumbura.bi',
                'role': 'AGENT',
                'badge_id': 'AGT-CV-02',
                'phone': '+257 79 555 666',
                'assigned_zone': created_zones['CV'],
            }
        )
        if created:
            agent_centre.set_password('agent123')
            agent_centre.save()
            self.stdout.write(self.style.SUCCESS("  [User] Agent 'agent_centre' créé (Mot de passe: agent123)"))

        # Compte Contrôleur Général
        controleur, created = CustomUser.objects.get_or_create(
            username='controleur',
            defaults={
                'first_name': 'Pierre',
                'last_name': 'Niyonzima',
                'email': 'controleur@mairie-bujumbura.bi',
                'role': 'AGENT',
                'badge_id': 'CTRL-BJM-03',
                'phone': '+257 79 777 888',
                'assigned_zone': created_zones['PLI'],
            }
        )
        if created:
            controleur.set_password('agent123')
            controleur.save()
            self.stdout.write(self.style.SUCCESS("  [User] Contrôleur 'controleur' créé (Mot de passe: agent123)"))

        # 5. Création de tickets réalistes récents et historiques
        now = timezone.now()
        sample_plates = [
            ("RA 4512 B", 'VOITURE', 'CV'),
            ("IT 3214 A", 'VOITURE', 'ROH'),
            ("D 9845 A", 'VOITURE', 'PLI'),
            ("C 1278 B", 'BUS', 'MC'),
            ("H 4410 A", 'MOTO', 'ASI'),
            ("RA 8899 A", 'VOITURE', 'CV'),
            ("IT 7765 B", 'VOITURE', 'MC'),
            ("K 2233 A", 'CAMION', 'MC'),
            ("D 4455 B", 'VOITURE', 'ROH'),
            ("RA 1122 C", 'MOTO', 'PLI'),
            ("C 9900 A", 'BUS', 'CV'),
            ("IT 5544 A", 'VOITURE', 'ASI'),
            ("RA 3366 B", 'VOITURE', 'ROH'),
        ]

        if ParkingTicket.objects.count() == 0:
            self.stdout.write("  Création d'un ensemble de tickets de test...")
            agents = [admin_user, agent_rohero, agent_centre, controleur]

            # A. Tickets en cours de stationnement (pour alimenter l'état temps réel)
            for i, (plate, vcode, zcode) in enumerate(sample_plates[:7]):
                mins_ago = random.randint(25, 240)
                entry_dt = now - datetime.timedelta(minutes=mins_ago)
                zone_obj = created_zones[zcode]
                vt_obj = created_vtypes[vcode]
                agent_obj = random.choice(agents)

                ticket = ParkingTicket.objects.create(
                    ticket_number=generate_ticket_number(),
                    plate_number=plate,
                    vehicle_type=vt_obj,
                    zone=zone_obj,
                    entry_time=entry_dt,
                    created_by=agent_obj,
                    status='EN_COURS',
                    is_active=True
                )
                ActivityLog.objects.create(
                    user=agent_obj,
                    action='ENTREE_VEHICULE',
                    target_model='ParkingTicket',
                    target_id=ticket.id,
                    target_repr=f"Ticket #{ticket.ticket_number} ({ticket.plate_number})",
                    details=f"Entrée du véhicule {plate} ({vt_obj.name}) dans la zone {zone_obj.name}",
                    ip_address="127.0.0.1",
                    timestamp=entry_dt
                )

            # B. Tickets en infraction (> 9 heures sans sortie)
            infraction_plate = "RA 0077 A"
            infract_entry = now - datetime.timedelta(hours=10, minutes=30)
            infract_ticket = ParkingTicket.objects.create(
                ticket_number=generate_ticket_number(),
                plate_number=infraction_plate,
                vehicle_type=created_vtypes['VOITURE'],
                zone=created_zones['PLI'],
                entry_time=infract_entry,
                created_by=controleur,
                status='EN_COURS',
                is_active=True
            )
            ActivityLog.objects.create(
                user=controleur,
                action='ENTREE_VEHICULE',
                target_model='ParkingTicket',
                target_id=infract_ticket.id,
                target_repr=f"Ticket #{infract_ticket.ticket_number} ({infract_ticket.plate_number})",
                details=f"Entrée de {infraction_plate} à la Place de l'Indépendance",
                ip_address="127.0.0.1",
                timestamp=infract_entry
            )

            # C. Tickets clôturés et payés aujourd'hui (pour alimenter le chiffre d'affaires du jour en BIF)
            for j, (plate, vcode, zcode) in enumerate(sample_plates[7:]):
                hours_ago = random.randint(1, 5)
                entry_dt = now - datetime.timedelta(hours=hours_ago + 1)
                exit_dt = now - datetime.timedelta(minutes=random.randint(5, 50))
                duration = int((exit_dt - entry_dt).total_seconds() // 60)
                zone_obj = created_zones[zcode]
                vt_obj = created_vtypes[vcode]
                agent_in = random.choice(agents)
                agent_out = random.choice(agents)

                # Calcul du montant
                billed_hours = max(1, (duration + 59) // 60)
                amount = int(billed_hours * vt_obj.default_hourly_rate)
                method = random.choice(['ESPECES', 'LUMICASH', 'ECOCASH'])
                ref = f"TXN-{random.randint(100000, 999999)}" if method != 'ESPECES' else ""

                t_paid = ParkingTicket.objects.create(
                    ticket_number=generate_ticket_number(),
                    plate_number=plate,
                    vehicle_type=vt_obj,
                    zone=zone_obj,
                    entry_time=entry_dt,
                    exit_time=exit_dt,
                    duration_minutes=duration,
                    amount_due=amount,
                    amount_paid=amount,
                    payment_method=method,
                    payment_reference=ref,
                    created_by=agent_in,
                    closed_by=agent_out,
                    status='PAYE',
                    is_active=True
                )
                ActivityLog.objects.create(
                    user=agent_out,
                    action='SORTIE_PAIEMENT',
                    target_model='ParkingTicket',
                    target_id=t_paid.id,
                    target_repr=f"Ticket #{t_paid.ticket_number} ({t_paid.plate_number})",
                    details=f"Sortie du véhicule {plate}. Encaissé {amount:,.0f} BIF ({method}).".replace(',', ' '),
                    ip_address="127.0.0.1",
                    timestamp=exit_dt
                )

            # D. Tickets payés les jours précédents (pour alimenter les rapports hebdomadaires et mensuels)
            for days_back in range(1, 6):
                day_target = now - datetime.timedelta(days=days_back)
                for k in range(3):
                    entry_k = day_target.replace(hour=8 + k * 2, minute=random.randint(0, 50))
                    exit_k = entry_k + datetime.timedelta(minutes=random.randint(45, 210))
                    dur_k = int((exit_k - entry_k).total_seconds() // 60)
                    z_rnd = random.choice(list(created_zones.values()))
                    vt_rnd = random.choice(list(created_vtypes.values()))
                    amt_k = max(1, (dur_k + 59) // 60) * int(vt_rnd.default_hourly_rate)
                    
                    p_num = f"RA {random.randint(1000, 9999)} {random.choice(['A', 'B', 'C'])}"
                    ParkingTicket.objects.create(
                        ticket_number=generate_ticket_number(),
                        plate_number=p_num,
                        vehicle_type=vt_rnd,
                        zone=z_rnd,
                        entry_time=entry_k,
                        exit_time=exit_k,
                        duration_minutes=dur_k,
                        amount_due=amt_k,
                        amount_paid=amt_k,
                        payment_method=random.choice(['ESPECES', 'LUMICASH', 'ECOCASH']),
                        created_by=random.choice(agents),
                        closed_by=random.choice(agents),
                        status='PAYE',
                        is_active=True
                    )

            self.stdout.write(self.style.SUCCESS("  Tickets de test et historiques générés avec succès."))

        self.stdout.write(self.style.SUCCESS("== Initialisation des données de parking terminée avec succès ! =="))
        self.stdout.write("Comptes créés pour les tests :")
        self.stdout.write("  - Administrateur : admin / admin123")
        self.stdout.write("  - Agent Rohero   : agent_rohero / agent123")
        self.stdout.write("  - Agent Centre   : agent_centre / agent123")
        self.stdout.write("  - Contrôleur     : controleur / agent123")
