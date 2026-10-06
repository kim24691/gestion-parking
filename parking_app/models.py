import math
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator

class CustomUser(AbstractUser):
    """
    Modèle utilisateur personnalisé avec gestion des rôles :
    - Administrateur : Accès complet au système et à la configuration.
    - Agent de parking / Contrôleur : Opérations sur le terrain (entrées, sorties, encaissement, consultation).
    """
    ROLE_CHOICES = [
        ('ADMIN', 'Administrateur'),
        ('AGENT', 'Agent de Parking / Contrôleur'),
    ]

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='AGENT',
        verbose_name="Rôle dans le système"
    )
    phone = models.CharField(
        max_length=25,
        blank=True,
        verbose_name="Numéro de téléphone (+257)"
    )
    badge_id = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Matricule / Badge Agent"
    )
    assigned_zone = models.ForeignKey(
        'ParkingZone',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_agents',
        verbose_name="Zone d'affectation principale"
    )

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['username']

    def is_admin_user(self):
        return self.role == 'ADMIN' or self.is_superuser

    def is_agent_user(self):
        return self.role == 'AGENT'

    def get_role_badge_class(self):
        if self.role == 'ADMIN':
            return 'bg-danger text-white'
        return 'bg-primary text-white'

    def __str__(self):
        full_name = self.get_full_name()
        display = full_name if full_name else self.username
        badge = f" ({self.badge_id})" if self.badge_id else ""
        return f"{display}{badge} - {self.get_role_display()}"


class ParkingZone(models.Model):
    """
    Zones de stationnement de la ville de Bujumbura :
    Ex: Centre-Ville, Rohero, Place de l'Indépendance, Marché Central, Asian.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom de la Zone")
    code = models.CharField(max_length=20, unique=True, verbose_name="Code de la Zone (ex: CV, ROH)")
    description = models.TextField(blank=True, verbose_name="Description / Localisation précise")
    total_spots = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(1)],
        verbose_name="Capacité totale (places)"
    )
    hourly_rate_default = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=1000,
        verbose_name="Tarif horaire de base (BIF)"
    )
    is_active = models.BooleanField(default=True, verbose_name="Zone active")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    class Meta:
        verbose_name = "Zone de Parking"
        verbose_name_plural = "Zones de Parking"
        ordering = ['name']

    def get_occupied_spots(self):
        """Nombre de véhicules actuellement stationnés dans cette zone"""
        return self.tickets.filter(status='EN_COURS', is_active=True).count()

    def get_available_spots(self):
        """Nombre de places libres en temps réel"""
        occupied = self.get_occupied_spots()
        return max(0, self.total_spots - occupied)

    def get_occupancy_rate(self):
        """Pourcentage d'occupation de la zone"""
        if self.total_spots == 0:
            return 0
        occupied = self.get_occupied_spots()
        return round((occupied / self.total_spots) * 100, 1)

    def get_status_color(self):
        rate = self.get_occupancy_rate()
        if rate >= 90:
            return 'danger'  # Presque plein / Saturé
        elif rate >= 70:
            return 'warning' # Remplissage modéré
        return 'success'     # Fluide / Bon nombre de places libres

    def __str__(self):
        return f"{self.name} ({self.code}) - {self.total_spots} places"


class VehicleType(models.Model):
    """
    Types de véhicules admis sur les parkings de Bujumbura :
    - Voiture (tourisme, taxi, SUV)
    - Motocyclette / Tuk-tuk
    - Minibus / Bus (transport commun)
    - Camion (poids lourd / livraison)
    """
    code = models.CharField(max_length=30, unique=True, verbose_name="Code unique (ex: VOITURE)")
    name = models.CharField(max_length=60, verbose_name="Type de véhicule")
    icon_class = models.CharField(
        max_length=50,
        default='fa-car',
        verbose_name="Icône FontAwesome (ex: fa-car, fa-motorcycle, fa-bus, fa-truck)"
    )
    default_hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=1000,
        verbose_name="Tarif par heure standard (BIF)"
    )
    default_daily_rate = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=6000,
        verbose_name="Tarif par journée standard (BIF)"
    )
    description = models.CharField(max_length=200, blank=True, verbose_name="Description")
    is_active = models.BooleanField(default=True, verbose_name="Actif")

    class Meta:
        verbose_name = "Type de Véhicule"
        verbose_name_plural = "Types de Véhicules"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.default_hourly_rate:,.0f} BIF/h)".replace(',', ' ')


class Tariff(models.Model):
    """
    Règles de tarification spécifiques par type de véhicule et éventuellement par zone.
    Exprimées en Francs Burundi (BIF).
    """
    TARIFF_TYPE_CHOICES = [
        ('HOURLY', 'Tarif par Heure entamée'),
        ('DAILY', 'Tarif par Journée (Forfait 24h)'),
        ('FIXED', 'Forfait Fixe d\'accès'),
    ]

    vehicle_type = models.ForeignKey(
        VehicleType,
        on_delete=models.CASCADE,
        related_name='tariffs',
        verbose_name="Type de véhicule"
    )
    zone = models.ForeignKey(
        ParkingZone,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tariffs',
        verbose_name="Zone spécifique (Optionnelle - Toutes si vide)"
    )
    tariff_type = models.CharField(
        max_length=15,
        choices=TARIFF_TYPE_CHOICES,
        default='HOURLY',
        verbose_name="Mode de facturation"
    )
    amount_bif = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name="Montant en Francs Burundi (BIF)"
    )
    grace_period_minutes = models.PositiveIntegerField(
        default=15,
        verbose_name="Période de grâce (minutes gratuites)"
    )
    max_daily_cap_bif = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="Plafond journalier maximal (BIF)"
    )
    is_active = models.BooleanField(default=True, verbose_name="Tarif actif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Grille Tarifaire"
        verbose_name_plural = "Grilles Tarifaires"
        ordering = ['vehicle_type', 'tariff_type']

    def __str__(self):
        zone_str = f" [{self.zone.name}]" if self.zone else " [Toutes zones]"
        return f"{self.vehicle_type.name} - {self.get_tariff_type_display()}: {self.amount_bif:,.0f} BIF{zone_str}".replace(',', ' ')


class ParkingTicket(models.Model):
    """
    Gestion des tickets d'entrée et de sortie des véhicules.
    Enregistre les données partagées et l'historique complet.
    """
    STATUS_CHOICES = [
        ('EN_COURS', 'Stationnement en cours'),
        ('PAYE', 'Payé et Sorti'),
        ('ANNULE', 'Annulé / Désactivé'),
        ('EN_INFRACTION', 'Infraction / Dépassement'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('ESPECES', 'Espèces (Cash BIF)'),
        ('LUMICASH', 'Lumicash Mobile'),
        ('ECOCASH', 'EcoCash Mobile'),
        ('BANQUE', 'Virement / Carte bancaire'),
    ]

    ticket_number = models.CharField(
        max_length=35,
        unique=True,
        db_index=True,
        verbose_name="Numéro de Ticket"
    )
    plate_number = models.CharField(
        max_length=25,
        db_index=True,
        verbose_name="Numéro d'immatriculation / Plaque"
    )
    vehicle_type = models.ForeignKey(
        VehicleType,
        on_delete=models.PROTECT,
        related_name='tickets',
        verbose_name="Type de véhicule"
    )
    zone = models.ForeignKey(
        ParkingZone,
        on_delete=models.PROTECT,
        related_name='tickets',
        verbose_name="Zone de stationnement"
    )
    entry_time = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name="Heure d'entrée"
    )
    exit_time = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Heure de sortie"
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='tickets_created',
        verbose_name="Agent d'enregistrement (Entrée)"
    )
    closed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_closed',
        verbose_name="Agent de clôture (Sortie/Encaissement)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='EN_COURS',
        db_index=True,
        verbose_name="Statut du ticket"
    )
    duration_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name="Durée de stationnement (minutes)"
    )
    amount_due = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name="Montant dû (BIF)"
    )
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name="Montant encaissé (BIF)"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='ESPECES',
        verbose_name="Mode de règlement"
    )
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Référence de transaction (Lumicash/EcoCash)"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Ticket actif (Non désactivé)"
    )
    cancellation_reason = models.TextField(
        blank=True,
        verbose_name="Motif d'annulation / désactivation"
    )
    deactivated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_deactivated',
        verbose_name="Désactivé par"
    )
    deactivated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date & Heure de désactivation"
    )

    class Meta:
        verbose_name = "Ticket de Parking"
        verbose_name_plural = "Tickets de Parking"
        ordering = ['-entry_time']

    def clean(self):
        if self.plate_number:
            self.plate_number = self.plate_number.strip().upper()

    def save(self, *args, **kwargs):
        if self.plate_number:
            self.plate_number = self.plate_number.strip().upper()
        super().save(*args, **kwargs)

    def calculate_bill(self, current_time=None):
        """
        Calcul dynamique précis du montant dû en BIF selon le barème :
        - Période de grâce (ex: 15 min gratuites).
        - Tarification par heure entamée.
        - Tarification plafonnée journalière si longue durée.
        """
        end_time = self.exit_time or current_time or timezone.now()
        delta = end_time - self.entry_time
        total_seconds = max(0, delta.total_seconds())
        total_minutes = int(total_seconds // 60)

        # Recherche de tarif personnalisé pour la zone et le type de véhicule
        tariff_qs = Tariff.objects.filter(
            vehicle_type=self.vehicle_type,
            is_active=True
        )
        zone_tariff = tariff_qs.filter(zone=self.zone, tariff_type='HOURLY').first()
        general_tariff = tariff_qs.filter(zone__isnull=True, tariff_type='HOURLY').first()

        tariff = zone_tariff or general_tariff
        grace_period = tariff.grace_period_minutes if tariff else 15
        rate_hourly = tariff.amount_bif if tariff else self.vehicle_type.default_hourly_rate
        rate_daily = self.vehicle_type.default_daily_rate

        # Si stationnement inférieur ou égal à la période de grâce
        if total_minutes <= grace_period:
            return total_minutes, 0

        # Tarification par heure entamée
        hours_billed = math.ceil(total_minutes / 60)

        # Calcul horaire
        calculated_amount = hours_billed * float(rate_hourly)

        # Plafonnement par tranche de 24h au tarif journalier
        days = total_minutes // 1440
        remainder_minutes = total_minutes % 1440
        remainder_hours = math.ceil(remainder_minutes / 60)
        daily_amount_potential = (days * float(rate_daily)) + min(float(rate_daily), remainder_hours * float(rate_hourly))

        final_amount = min(calculated_amount, daily_amount_potential)
        return total_minutes, int(final_amount)

    def formatted_duration(self):
        """Format lisible de la durée ex: '2h 15m'"""
        mins = self.duration_minutes
        if mins < 60:
            return f"{mins} min"
        hours = mins // 60
        remainder = mins % 60
        if remainder == 0:
            return f"{hours} h"
        return f"{hours} h {remainder} min"

    def get_status_badge(self):
        badges = {
            'EN_COURS': 'bg-primary text-white',
            'PAYE': 'bg-success text-white',
            'ANNULE': 'bg-secondary text-white',
            'EN_INFRACTION': 'bg-danger text-white',
        }
        return badges.get(self.status, 'bg-dark text-white')

    def __str__(self):
        return f"Ticket #{self.ticket_number} - {self.plate_number} ({self.zone.code})"


class ActivityLog(models.Model):
    """
    Système de traçabilité & historique des activités (Audit Trail) :
    Sauvegarde systématiquement qui a fait quoi, quand, sur quel élément et depuis quelle IP.
    """
    ACTION_CHOICES = [
        ('CREATION', 'Création'),
        ('MODIFICATION', 'Modification'),
        ('SUPPRESSION', 'Suppression'),
        ('DESACTIVATION', 'Désactivation / Soft Delete'),
        ('ACTIVATION', 'Activation'),
        ('ENTREE_VEHICULE', 'Enregistrement Entrée'),
        ('SORTIE_PAIEMENT', 'Sortie & Encaissement BIF'),
        ('ANNULATION_TICKET', 'Annulation Ticket'),
        ('CONNEXION', 'Connexion Utilisateur'),
        ('DECONNEXION', 'Déconnexion Utilisateur'),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
        verbose_name="Utilisateur acteur"
    )
    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
        db_index=True,
        verbose_name="Type d'action"
    )
    target_model = models.CharField(
        max_length=60,
        db_index=True,
        verbose_name="Entité concernée (Modèle)"
    )
    target_id = models.CharField(
        max_length=60,
        blank=True,
        verbose_name="Identifiant de l'objet"
    )
    target_repr = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Désignation de l'élément"
    )
    details = models.TextField(
        blank=True,
        verbose_name="Détails descriptifs de l'opération"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Adresse IP"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Date & Heure"
    )

    class Meta:
        verbose_name = "Journal d'Audit"
        verbose_name_plural = "Journaux d'Audit (Traçabilité)"
        ordering = ['-timestamp']

    def get_action_badge_class(self):
        badges = {
            'CREATION': 'bg-success text-white',
            'ENTREE_VEHICULE': 'bg-info text-dark',
            'MODIFICATION': 'bg-warning text-dark',
            'SORTIE_PAIEMENT': 'bg-primary text-white',
            'SUPPRESSION': 'bg-danger text-white',
            'DESACTIVATION': 'bg-secondary text-white',
            'ANNULATION_TICKET': 'bg-danger text-white',
            'ACTIVATION': 'bg-success text-white',
            'CONNEXION': 'bg-dark text-white',
            'DECONNEXION': 'bg-secondary text-white',
        }
        return badges.get(self.action, 'bg-light text-dark')

    def __str__(self):
        user_name = self.user.username if self.user else "Système/Anonyme"
        return f"[{self.timestamp.strftime('%d/%m/%Y %H:%M')}] {user_name} - {self.get_action_display()} sur {self.target_model}"
