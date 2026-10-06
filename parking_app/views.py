import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse

from .models import (
    CustomUser, ParkingZone, VehicleType, Tariff, ParkingTicket, ActivityLog
)
from .forms import (
    UserLoginForm, CustomUserCreationForm, CustomUserUpdateForm,
    ParkingZoneForm, VehicleTypeForm, TariffForm,
    TicketEntryForm, TicketCheckoutForm, TicketDeactivateForm, TicketFilterForm
)
from .utils import (
    log_activity, generate_ticket_number, admin_required, agent_or_admin_required,
    generate_ticket_pdf, generate_financial_report_pdf
)


# ==============================================================================
# AUTHENTIFICATION & PROFIL
# ==============================================================================

def login_view(request):
    """Connexion sécurisée des utilisateurs (Admin & Agents de parking)"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_active:
                messages.error(request, "Votre compte a été désactivé par l'administration.")
                return render(request, 'parking_app/auth/login.html', {'form': form})
            
            login(request, user)
            log_activity(
                request,
                action='CONNEXION',
                target_model='CustomUser',
                target_id=user.id,
                target_repr=str(user),
                details=f"Connexion réussie au système par {user.username} ({user.get_role_display()})"
            )
            messages.success(request, f"Bienvenue {user.get_full_name() or user.username} ! Vous êtes connecté en tant que {user.get_role_display()}.")
            return redirect('dashboard')
        else:
            messages.error(request, "Identifiants invalides. Veuillez vérifier votre nom d'utilisateur et mot de passe.")
    else:
        form = UserLoginForm()

    return render(request, 'parking_app/auth/login.html', {'form': form})


@login_required
def logout_view(request):
    """Déconnexion sécurisée avec journalisation dans l'Audit Trail"""
    user = request.user
    log_activity(
        request,
        action='DECONNEXION',
        target_model='CustomUser',
        target_id=user.id,
        target_repr=str(user),
        details=f"Déconnexion du système par {user.username}"
    )
    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect('login')


@login_required
def profile_view(request):
    """Consultation du profil et modification du mot de passe"""
    user = request.user
    if request.method == 'POST' and 'change_password' in request.POST:
        password_form = PasswordChangeForm(user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            log_activity(
                request,
                action='MODIFICATION',
                target_model='CustomUser',
                target_id=user.id,
                target_repr=str(user),
                details="Modification du mot de passe personnel"
            )
            messages.success(request, "Votre mot de passe a été mis à jour avec succès.")
            return redirect('profile')
        else:
            messages.error(request, "Erreur lors du changement de mot de passe.")
    else:
        password_form = PasswordChangeForm(user)

    # Statistiques personnelles pour l'agent
    today = timezone.localdate()
    my_tickets_today = ParkingTicket.objects.filter(
        created_by=user,
        entry_time__date=today
    ).count()
    my_checkouts_today = ParkingTicket.objects.filter(
        closed_by=user,
        exit_time__date=today,
        status='PAYE'
    )
    my_revenue_today = my_checkouts_today.aggregate(total=Sum('amount_paid'))['total'] or 0

    return render(request, 'parking_app/auth/profile.html', {
        'password_form': password_form,
        'my_tickets_today': my_tickets_today,
        'my_checkouts_today': my_checkouts_today.count(),
        'my_revenue_today': my_revenue_today,
    })


# ==============================================================================
# TABLEAU DE BORD (DASHBOARD)
# ==============================================================================

@login_required
def dashboard(request):
    """
    Tableau de bord principal avec indicateurs clés (KPIs) en temps réel :
    - Places occupées / libres globales et par zone
    - Chiffre d'affaires du jour en BIF
    - Véhicules en infraction (temps dépassé > 8h)
    - Entrées récentes et actions rapides
    """
    today = timezone.localdate()
    now = timezone.now()

    # Zones actives et calculs temps réel
    zones = ParkingZone.objects.filter(is_active=True)
    zones_stats = []
    total_capacity = 0
    total_occupied = 0

    for z in zones:
        occupied = z.get_occupied_spots()
        available = z.get_available_spots()
        rate = z.get_occupancy_rate()
        color = z.get_status_color()
        total_capacity += z.total_spots
        total_occupied += occupied
        zones_stats.append({
            'zone': z,
            'occupied': occupied,
            'available': available,
            'rate': rate,
            'color': color,
        })

    total_available = max(0, total_capacity - total_occupied)
    global_rate = round((total_occupied / total_capacity * 100), 1) if total_capacity > 0 else 0

    # Chiffre d'affaires du jour en BIF
    today_paid_tickets = ParkingTicket.objects.filter(
        exit_time__date=today,
        status='PAYE',
        is_active=True
    )
    today_revenue_bif = today_paid_tickets.aggregate(total=Sum('amount_paid'))['total'] or 0

    # Entrées du jour
    today_entries_count = ParkingTicket.objects.filter(
        entry_time__date=today,
        is_active=True
    ).count()

    # Sorties du jour
    today_exits_count = today_paid_tickets.count()

    # Véhicules actuellement stationnés depuis plus de 8 heures (Alerte / Infraction)
    threshold_time = now - datetime.timedelta(hours=8)
    long_stays_count = ParkingTicket.objects.filter(
        status='EN_COURS',
        is_active=True,
        entry_time__lt=threshold_time
    ).count()

    # 10 Dernières entrées de véhicules
    recent_tickets = ParkingTicket.objects.filter(
        is_active=True
    ).select_related('zone', 'vehicle_type', 'created_by')[:8]

    # Historique financier des 7 derniers jours
    last_7_days = []
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        rev = ParkingTicket.objects.filter(
            exit_time__date=day,
            status='PAYE',
            is_active=True
        ).aggregate(total=Sum('amount_paid'))['total'] or 0
        cnt = ParkingTicket.objects.filter(
            entry_time__date=day,
            is_active=True
        ).count()
        last_7_days.append({
            'day': day.strftime('%d/%m'),
            'revenue': int(rev),
            'entries': cnt,
        })

    context = {
        'total_capacity': total_capacity,
        'total_occupied': total_occupied,
        'total_available': total_available,
        'global_rate': global_rate,
        'today_revenue_bif': today_revenue_bif,
        'today_entries_count': today_entries_count,
        'today_exits_count': today_exits_count,
        'long_stays_count': long_stays_count,
        'zones_stats': zones_stats,
        'recent_tickets': recent_tickets,
        'last_7_days': last_7_days,
    }
    return render(request, 'parking_app/dashboard.html', context)


# ==============================================================================
# MODULE STATIONNEMENTS & TICKETS
# ==============================================================================

@login_required
def ticket_list(request):
    """
    Affichage et recherche avancée des tickets de parking.
    Filtres : Immatriculation, Zone, Type de véhicule, Statut, Période.
    """
    form = TicketFilterForm(request.GET)
    tickets = ParkingTicket.objects.all().select_related('zone', 'vehicle_type', 'created_by', 'closed_by')

    if form.is_valid():
        q = form.cleaned_data.get('q')
        zone = form.cleaned_data.get('zone')
        v_type = form.cleaned_data.get('vehicle_type')
        status = form.cleaned_data.get('status')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')

        if q:
            tickets = tickets.filter(
                Q(plate_number__icontains=q) |
                Q(ticket_number__icontains=q)
            )
        if zone:
            tickets = tickets.filter(zone=zone)
        if v_type:
            tickets = tickets.filter(vehicle_type=v_type)
        if status:
            tickets = tickets.filter(status=status)
        if date_from:
            tickets = tickets.filter(entry_time__date__gte=date_from)
        if date_to:
            tickets = tickets.filter(entry_time__date__lte=date_to)

    paginator = Paginator(tickets, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'parking_app/tickets/ticket_list.html', {
        'page_obj': page_obj,
        'form': form,
        'total_count': tickets.count(),
    })


@login_required
def ticket_entry(request):
    """
    Enregistrement de l'entrée d'un véhicule dans le parking municipal :
    - Saisie de la plaque d'immatriculation
    - Choix de la zone et du type de véhicule
    - Vérification automatique de disponibilité de place
    - Attribution du numéro de ticket unique
    - Sauvegarde dans le journal d'audit
    """
    # Pré-sélection de la zone assignée à l'agent si applicable
    initial_data = {}
    if request.user.assigned_zone:
        initial_data['zone'] = request.user.assigned_zone

    if request.method == 'POST':
        form = TicketEntryForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.ticket_number = generate_ticket_number()
            ticket.created_by = request.user
            ticket.entry_time = timezone.now()
            ticket.status = 'EN_COURS'
            ticket.is_active = True
            ticket.save()

            log_activity(
                request,
                action='ENTREE_VEHICULE',
                target_model='ParkingTicket',
                target_id=ticket.id,
                target_repr=f"Ticket #{ticket.ticket_number} ({ticket.plate_number})",
                details=f"Entrée du véhicule {ticket.plate_number} ({ticket.vehicle_type.name}) dans la zone {ticket.zone.name}"
            )

            messages.success(
                request,
                f"Véhicule {ticket.plate_number} enregistré avec succès ! Ticket N° {ticket.ticket_number}."
            )
            return redirect('ticket_detail', pk=ticket.pk)
    else:
        form = TicketEntryForm(initial=initial_data)

    zones = ParkingZone.objects.filter(is_active=True)
    return render(request, 'parking_app/tickets/ticket_entry.html', {
        'form': form,
        'zones': zones,
    })


@login_required
def ticket_checkout(request, pk):
    """
    Enregistrement de la sortie d'un véhicule et encaissement :
    - Calcul automatique de la durée exacte et du montant dû en BIF
    - Choix du mode de paiement (Espèces, Lumicash, EcoCash)
    - Enregistrement de l'encaissement et libération de la place
    - Traçabilité complète
    """
    ticket = get_object_or_404(ParkingTicket, pk=pk, is_active=True)

    if ticket.status == 'PAYE':
        messages.info(request, f"Le ticket #{ticket.ticket_number} a déjà été payé et clôturé.")
        return redirect('ticket_detail', pk=ticket.pk)

    now = timezone.now()
    duration_minutes, amount_due = ticket.calculate_bill(current_time=now)

    if request.method == 'POST':
        form = TicketCheckoutForm(request.POST)
        if form.is_valid():
            ticket.exit_time = now
            ticket.duration_minutes = duration_minutes
            ticket.amount_due = amount_due
            ticket.amount_paid = form.cleaned_data['amount_paid']
            ticket.payment_method = form.cleaned_data['payment_method']
            ticket.payment_reference = form.cleaned_data['payment_reference']
            ticket.closed_by = request.user
            ticket.status = 'PAYE'
            ticket.save()

            log_activity(
                request,
                action='SORTIE_PAIEMENT',
                target_model='ParkingTicket',
                target_id=ticket.id,
                target_repr=f"Ticket #{ticket.ticket_number} ({ticket.plate_number})",
                details=(
                    f"Sortie du véhicule {ticket.plate_number} après {ticket.formatted_duration()}. "
                    f"Montant perçu : {ticket.amount_paid:,.0f} BIF via {ticket.get_payment_method_display()}."
                ).replace(',', ' ')
            )

            messages.success(
                request,
                f"Sortie validée ! Paiement de {ticket.amount_paid:,.0f} BIF enregistré pour le véhicule {ticket.plate_number}."
            )
            return redirect('ticket_detail', pk=ticket.pk)
    else:
        form = TicketCheckoutForm(initial={
            'amount_paid': amount_due,
            'payment_method': 'ESPECES',
        })

    # Calcul formaté de la durée actuelle
    hours = duration_minutes // 60
    rem_min = duration_minutes % 60
    duration_str = f"{hours}h {rem_min}min" if hours > 0 else f"{rem_min} min"

    return render(request, 'parking_app/tickets/ticket_checkout.html', {
        'ticket': ticket,
        'form': form,
        'duration_minutes': duration_minutes,
        'duration_str': duration_str,
        'amount_due': amount_due,
    })


@login_required
def ticket_detail(request, pk):
    """Consultation détaillée d'un ticket de stationnement"""
    ticket = get_object_or_404(ParkingTicket, pk=pk)
    
    # Calcul en direct si en cours
    current_minutes = 0
    current_bill = 0
    if ticket.status == 'EN_COURS':
        current_minutes, current_bill = ticket.calculate_bill()

    return render(request, 'parking_app/tickets/ticket_detail.html', {
        'ticket': ticket,
        'current_minutes': current_minutes,
        'current_bill': current_bill,
    })


@login_required
def ticket_print(request, pk):
    """Affichage du ticket optimisé pour impression web propre (format reçu thermique)"""
    ticket = get_object_or_404(ParkingTicket, pk=pk)
    return render(request, 'parking_app/tickets/ticket_print.html', {
        'ticket': ticket,
    })


@login_required
def ticket_pdf(request, pk):
    """Téléchargement du ticket officiel en format PDF généré par ReportLab"""
    ticket = get_object_or_404(ParkingTicket, pk=pk)
    pdf_content = generate_ticket_pdf(ticket)
    
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Ticket_{ticket.ticket_number}.pdf"'
    return response


@login_required
def ticket_deactivate(request, pk):
    """
    Désactivation logique / Annulation d'un ticket :
    Exige la saisie obligatoire d'un motif et trace l'opération dans le journal d'audit.
    """
    ticket = get_object_or_404(ParkingTicket, pk=pk, is_active=True)

    if request.method == 'POST':
        form = TicketDeactivateForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['cancellation_reason']
            ticket.is_active = False
            ticket.status = 'ANNULE'
            ticket.cancellation_reason = reason
            ticket.deactivated_by = request.user
            ticket.deactivated_at = timezone.now()
            ticket.save()

            log_activity(
                request,
                action='ANNULATION_TICKET',
                target_model='ParkingTicket',
                target_id=ticket.id,
                target_repr=f"Ticket #{ticket.ticket_number} ({ticket.plate_number})",
                details=f"Annulation/Désactivation logique du ticket #{ticket.ticket_number}. Motif : {reason}"
            )

            messages.warning(request, f"Le ticket #{ticket.ticket_number} a été désactivé / annulé.")
            return redirect('ticket_list')
    else:
        form = TicketDeactivateForm()

    return render(request, 'parking_app/tickets/ticket_deactivate.html', {
        'ticket': ticket,
        'form': form,
    })


@admin_required
def ticket_delete(request, pk):
    """
    Suppression définitive d'un ticket (Action stricte réservée à l'administrateur).
    Enregistre la suppression dans le journal d'audit.
    """
    ticket = get_object_or_404(ParkingTicket, pk=pk)

    if request.method == 'POST':
        ticket_repr = f"Ticket #{ticket.ticket_number} ({ticket.plate_number})"
        ticket_id = ticket.id
        ticket.delete()

        log_activity(
            request,
            action='SUPPRESSION',
            target_model='ParkingTicket',
            target_id=ticket_id,
            target_repr=ticket_repr,
            details=f"Suppression physique définitive du ticket par l'administrateur {request.user.username}"
        )

        messages.success(request, f"Le ticket {ticket_repr} a été supprimé définitivement.")
        return redirect('ticket_list')

    return render(request, 'parking_app/tickets/ticket_confirm_delete.html', {
        'ticket': ticket,
    })


# ==============================================================================
# MODULE ZONES DE PARKING
# ==============================================================================

@login_required
def zone_list(request):
    """Liste de toutes les zones de parking avec état de remplissage en temps réel"""
    zones = ParkingZone.objects.all()
    zones_data = []

    for z in zones:
        occupied = z.get_occupied_spots()
        available = z.get_available_spots()
        rate = z.get_occupancy_rate()
        color = z.get_status_color()
        zones_data.append({
            'zone': z,
            'occupied': occupied,
            'available': available,
            'rate': rate,
            'color': color,
        })

    return render(request, 'parking_app/zones/zone_list.html', {
        'zones_data': zones_data,
    })


@admin_required
def zone_create(request):
    """Ajout d'une nouvelle zone de parking municipal"""
    if request.method == 'POST':
        form = ParkingZoneForm(request.POST)
        if form.is_valid():
            zone = form.save()
            log_activity(
                request,
                action='CREATION',
                target_model='ParkingZone',
                target_id=zone.id,
                target_repr=str(zone),
                details=f"Création de la zone '{zone.name}' avec une capacité de {zone.total_spots} places."
            )
            messages.success(request, f"La zone '{zone.name}' a été créée avec succès.")
            return redirect('zone_list')
    else:
        form = ParkingZoneForm()

    return render(request, 'parking_app/zones/zone_form.html', {
        'form': form,
        'title': "Ajouter une Zone de Parking",
    })


@admin_required
def zone_edit(request, pk):
    """Modification d'une zone de parking existante"""
    zone = get_object_or_404(ParkingZone, pk=pk)

    if request.method == 'POST':
        form = ParkingZoneForm(request.POST, instance=zone)
        if form.is_valid():
            zone = form.save()
            log_activity(
                request,
                action='MODIFICATION',
                target_model='ParkingZone',
                target_id=zone.id,
                target_repr=str(zone),
                details=f"Mise à jour des paramètres de la zone '{zone.name}' (Capacité: {zone.total_spots} places)."
            )
            messages.success(request, f"La zone '{zone.name}' a été modifiée avec succès.")
            return redirect('zone_list')
    else:
        form = ParkingZoneForm(instance=zone)

    return render(request, 'parking_app/zones/zone_form.html', {
        'form': form,
        'zone': zone,
        'title': f"Modifier la Zone : {zone.name}",
    })


@admin_required
def zone_toggle_status(request, pk):
    """Activation / Désactivation d'une zone"""
    zone = get_object_or_404(ParkingZone, pk=pk)
    zone.is_active = not zone.is_active
    zone.save()

    status_str = "activée" if zone.is_active else "désactivée"
    action = 'ACTIVATION' if zone.is_active else 'DESACTIVATION'
    log_activity(
        request,
        action=action,
        target_model='ParkingZone',
        target_id=zone.id,
        target_repr=str(zone),
        details=f"Zone '{zone.name}' {status_str}."
    )
    messages.info(request, f"La zone '{zone.name}' est maintenant {status_str}.")
    return redirect('zone_list')


# ==============================================================================
# MODULE TARIFICATION & TYPES DE VÉHICULES
# ==============================================================================

@login_required
def tariff_list(request):
    """Affichage de la grille tarifaire en BIF et des types de véhicules"""
    tariffs = Tariff.objects.select_related('vehicle_type', 'zone').all()
    vehicle_types = VehicleType.objects.all()

    return render(request, 'parking_app/tariffs/tariff_list.html', {
        'tariffs': tariffs,
        'vehicle_types': vehicle_types,
    })


@admin_required
def tariff_create(request):
    """Ajout d'un tarif dans la grille tarifaire"""
    if request.method == 'POST':
        form = TariffForm(request.POST)
        if form.is_valid():
            tariff = form.save()
            log_activity(
                request,
                action='CREATION',
                target_model='Tariff',
                target_id=tariff.id,
                target_repr=str(tariff),
                details=f"Ajout d'un nouveau tarif : {tariff.amount_bif} BIF pour {tariff.vehicle_type.name}"
            )
            messages.success(request, "Tarif enregistré avec succès.")
            return redirect('tariff_list')
    else:
        form = TariffForm()

    return render(request, 'parking_app/tariffs/tariff_form.html', {
        'form': form,
        'title': "Définir un Nouveau Tarif (BIF)",
    })


@admin_required
def tariff_edit(request, pk):
    """Modification d'un tarif existant"""
    tariff = get_object_or_404(Tariff, pk=pk)

    if request.method == 'POST':
        form = TariffForm(request.POST, instance=tariff)
        if form.is_valid():
            tariff = form.save()
            log_activity(
                request,
                action='MODIFICATION',
                target_model='Tariff',
                target_id=tariff.id,
                target_repr=str(tariff),
                details=f"Mise à jour du tarif : {tariff.amount_bif} BIF pour {tariff.vehicle_type.name}"
            )
            messages.success(request, "Tarif mis à jour avec succès.")
            return redirect('tariff_list')
    else:
        form = TariffForm(instance=tariff)

    return render(request, 'parking_app/tariffs/tariff_form.html', {
        'form': form,
        'tariff': tariff,
        'title': "Modifier le Tarif",
    })


@admin_required
def tariff_delete(request, pk):
    """Suppression d'un tarif"""
    tariff = get_object_or_404(Tariff, pk=pk)
    if request.method == 'POST':
        t_repr = str(tariff)
        t_id = tariff.id
        tariff.delete()
        log_activity(
            request,
            action='SUPPRESSION',
            target_model='Tariff',
            target_id=t_id,
            target_repr=t_repr,
            details=f"Suppression de la règle tarifaire : {t_repr}"
        )
        messages.success(request, "Tarif supprimé avec succès.")
        return redirect('tariff_list')

    return render(request, 'parking_app/tariffs/tariff_confirm_delete.html', {'tariff': tariff})


@admin_required
def vehicle_type_create(request):
    """Ajout d'une catégorie de véhicule"""
    if request.method == 'POST':
        form = VehicleTypeForm(request.POST)
        if form.is_valid():
            vt = form.save()
            log_activity(
                request,
                action='CREATION',
                target_model='VehicleType',
                target_id=vt.id,
                target_repr=str(vt),
                details=f"Création de la catégorie de véhicule '{vt.name}'."
            )
            messages.success(request, f"Type de véhicule '{vt.name}' ajouté.")
            return redirect('tariff_list')
    else:
        form = VehicleTypeForm()

    return render(request, 'parking_app/tariffs/vehicle_type_form.html', {
        'form': form,
        'title': "Ajouter un Type de Véhicule",
    })


@admin_required
def vehicle_type_edit(request, pk):
    """Modification d'une catégorie de véhicule"""
    vt = get_object_or_404(VehicleType, pk=pk)
    if request.method == 'POST':
        form = VehicleTypeForm(request.POST, instance=vt)
        if form.is_valid():
            vt = form.save()
            log_activity(
                request,
                action='MODIFICATION',
                target_model='VehicleType',
                target_id=vt.id,
                target_repr=str(vt),
                details=f"Modification du type de véhicule '{vt.name}'."
            )
            messages.success(request, f"Type de véhicule '{vt.name}' modifié.")
            return redirect('tariff_list')
    else:
        form = VehicleTypeForm(instance=vt)

    return render(request, 'parking_app/tariffs/vehicle_type_form.html', {
        'form': form,
        'vehicle_type': vt,
        'title': f"Modifier le Type : {vt.name}",
    })


# ==============================================================================
# MODULE GESTION DES UTILISATEURS
# ==============================================================================

@admin_required
def user_list(request):
    """Gestion des comptes utilisateurs : Administrateurs et Agents"""
    q = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '').strip()

    users = CustomUser.objects.all().select_related('assigned_zone')

    if q:
        users = users.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(badge_id__icontains=q) |
            Q(phone__icontains=q)
        )
    if role_filter:
        users = users.filter(role=role_filter)

    return render(request, 'parking_app/users/user_list.html', {
        'users': users,
        'q': q,
        'role_filter': role_filter,
    })


@admin_required
def user_create(request):
    """Création d'un nouvel agent ou administrateur"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            log_activity(
                request,
                action='CREATION',
                target_model='CustomUser',
                target_id=new_user.id,
                target_repr=str(new_user),
                details=f"Création du compte '{new_user.username}' avec le rôle {new_user.get_role_display()}."
            )
            messages.success(request, f"Compte de l'utilisateur '{new_user.username}' créé avec succès.")
            return redirect('user_list')
    else:
        form = CustomUserCreationForm()

    return render(request, 'parking_app/users/user_form.html', {
        'form': form,
        'title': "Créer un Nouvel Utilisateur",
    })


@admin_required
def user_edit(request, pk):
    """Modification d'un utilisateur existant"""
    target_user = get_object_or_404(CustomUser, pk=pk)

    if request.method == 'POST':
        form = CustomUserUpdateForm(request.POST, instance=target_user)
        if form.is_valid():
            target_user = form.save()
            log_activity(
                request,
                action='MODIFICATION',
                target_model='CustomUser',
                target_id=target_user.id,
                target_repr=str(target_user),
                details=f"Mise à jour des informations de l'utilisateur '{target_user.username}'."
            )
            messages.success(request, f"Compte de l'utilisateur '{target_user.username}' mis à jour.")
            return redirect('user_list')
    else:
        form = CustomUserUpdateForm(instance=target_user)

    return render(request, 'parking_app/users/user_form.html', {
        'form': form,
        'target_user': target_user,
        'title': f"Modifier l'Utilisateur : {target_user.username}",
    })


@admin_required
def user_toggle_status(request, pk):
    """Activer ou désactiver un compte utilisateur"""
    target_user = get_object_or_404(CustomUser, pk=pk)

    if target_user == request.user:
        messages.error(request, "Vous ne pouvez pas désactiver votre propre compte administrateur.")
        return redirect('user_list')

    target_user.is_active = not target_user.is_active
    target_user.save()

    status_str = "activé" if target_user.is_active else "désactivé"
    action = 'ACTIVATION' if target_user.is_active else 'DESACTIVATION'
    log_activity(
        request,
        action=action,
        target_model='CustomUser',
        target_id=target_user.id,
        target_repr=str(target_user),
        details=f"Le compte utilisateur '{target_user.username}' a été {status_str}."
    )
    messages.info(request, f"Le compte '{target_user.username}' a été {status_str}.")
    return redirect('user_list')


# ==============================================================================
# MODULE AUDIT TRAIL (TRAÇABILITÉ & HISTORIQUE DES ACTIONS)
# ==============================================================================

@login_required
def audit_log_list(request):
    """
    Consultation de l'historique complet des activités :
    Détaille quel utilisateur a opéré quel changement, sur quel élément et à quelle date/heure.
    """
    logs = ActivityLog.objects.select_related('user').all()

    # Filtres
    q = request.GET.get('q', '').strip()
    action = request.GET.get('action', '').strip()
    model_name = request.GET.get('model_name', '').strip()
    user_id = request.GET.get('user', '').strip()
    date_val = request.GET.get('date', '').strip()

    if q:
        logs = logs.filter(
            Q(target_repr__icontains=q) |
            Q(details__icontains=q) |
            Q(ip_address__icontains=q)
        )
    if action:
        logs = logs.filter(action=action)
    if model_name:
        logs = logs.filter(target_model=model_name)
    if user_id:
        logs = logs.filter(user_id=user_id)
    if date_val:
        logs = logs.filter(timestamp__date=date_val)

    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    users = CustomUser.objects.all()
    actions = ActivityLog.ACTION_CHOICES

    return render(request, 'parking_app/audit/audit_list.html', {
        'page_obj': page_obj,
        'users': users,
        'actions': actions,
        'q': q,
        'selected_action': action,
        'selected_model': model_name,
        'selected_user': user_id,
        'selected_date': date_val,
        'total_logs': logs.count(),
    })


# ==============================================================================
# MODULE RAPPORTS & IMPRESSION
# ==============================================================================

@login_required
def reports_dashboard(request):
    """Centre de contrôle des rapports statistiques et financiers"""
    return render(request, 'parking_app/reports/reports_dashboard.html')


@login_required
def report_daily_traffic(request):
    """
    Bilan des entrées et sorties de véhicules (par jour et par semaine).
    Filtre par plage de dates.
    """
    today = timezone.localdate()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        start_date = datetime.date.fromisoformat(start_date)
    else:
        start_date = today - datetime.timedelta(days=7)

    if end_date:
        end_date = datetime.date.fromisoformat(end_date)
    else:
        end_date = today

    # Données agrégées par jour
    traffic_by_day = []
    curr = start_date
    total_entries = 0
    total_exits = 0

    while curr <= end_date:
        entries = ParkingTicket.objects.filter(
            entry_time__date=curr,
            is_active=True
        ).count()
        exits = ParkingTicket.objects.filter(
            exit_time__date=curr,
            status='PAYE',
            is_active=True
        ).count()
        rev = ParkingTicket.objects.filter(
            exit_time__date=curr,
            status='PAYE',
            is_active=True
        ).aggregate(total=Sum('amount_paid'))['total'] or 0

        total_entries += entries
        total_exits += exits
        traffic_by_day.append({
            'date': curr,
            'entries': entries,
            'exits': exits,
            'revenue': int(rev),
        })
        curr += datetime.timedelta(days=1)

    return render(request, 'parking_app/reports/report_traffic.html', {
        'start_date': start_date,
        'end_date': end_date,
        'traffic_by_day': traffic_by_day,
        'total_entries': total_entries,
        'total_exits': total_exits,
    })


@login_required
def report_financial(request):
    """
    Rapport financier des recettes globales et par zone exprimées en BIF.
    Calculs détaillés, totaux et pourcentages.
    """
    today = timezone.localdate()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        start_date = datetime.date.fromisoformat(start_date)
    else:
        start_date = today.replace(day=1) # Début du mois

    if end_date:
        end_date = datetime.date.fromisoformat(end_date)
    else:
        end_date = today

    paid_tickets = ParkingTicket.objects.filter(
        exit_time__date__gte=start_date,
        exit_time__date__lte=end_date,
        status='PAYE',
        is_active=True
    )

    total_revenue = paid_tickets.aggregate(total=Sum('amount_paid'))['total'] or 0
    total_tickets = paid_tickets.count()

    # Recettes par Zone
    zones = ParkingZone.objects.all()
    zone_data = []
    for z in zones:
        z_tickets = paid_tickets.filter(zone=z)
        rev = z_tickets.aggregate(total=Sum('amount_paid'))['total'] or 0
        cnt = z_tickets.count()
        pct = (rev / total_revenue * 100) if total_revenue > 0 else 0
        zone_data.append({
            'name': z.name,
            'code': z.code,
            'total_spots': z.total_spots,
            'tickets_count': cnt,
            'revenue': int(rev),
            'percentage': round(pct, 1),
        })

    # Recettes par Type de Véhicule
    vehicles = VehicleType.objects.all()
    vehicle_data = []
    for v in vehicles:
        v_tickets = paid_tickets.filter(vehicle_type=v)
        rev = v_tickets.aggregate(total=Sum('amount_paid'))['total'] or 0
        cnt = v_tickets.count()
        vehicle_data.append({
            'name': v.name,
            'count': cnt,
            'revenue': int(rev),
        })

    # Recettes par Mode de Paiement
    payment_methods_data = []
    for code, label in ParkingTicket.PAYMENT_METHOD_CHOICES:
        p_tickets = paid_tickets.filter(payment_method=code)
        rev = p_tickets.aggregate(total=Sum('amount_paid'))['total'] or 0
        payment_methods_data.append({
            'label': label,
            'count': p_tickets.count(),
            'revenue': int(rev),
        })

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': int(total_revenue),
        'total_tickets': total_tickets,
        'zone_data': zone_data,
        'vehicle_data': vehicle_data,
        'payment_methods_data': payment_methods_data,
    }

    if request.GET.get('export') == 'pdf':
        pdf_data = generate_financial_report_pdf(
            start_date=start_date,
            end_date=end_date,
            total_revenue=total_revenue,
            total_tickets=total_tickets,
            zone_data=zone_data,
            vehicle_data=vehicle_data
        )
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Rapport_Financier_Parking_BJM_{start_date}_{end_date}.pdf"'
        return response

    return render(request, 'parking_app/reports/report_financial.html', context)


@login_required
def report_violations(request):
    """
    Liste des infractions ou véhicules ayant dépassé le temps autorisé de stationnement :
    - Véhicules stationnés depuis plus de 8 heures
    - Véhicules stationnés la nuit
    - Véhicules avec statut marqué 'EN_INFRACTION'
    """
    now = timezone.now()
    threshold_hours = int(request.GET.get('hours', 8))
    threshold_time = now - datetime.timedelta(hours=threshold_hours)

    violations_qs = ParkingTicket.objects.filter(
        status__in=['EN_COURS', 'EN_INFRACTION'],
        is_active=True,
        entry_time__lt=threshold_time
    ).select_related('zone', 'vehicle_type', 'created_by')

    violations_list = []
    for t in violations_qs:
        mins, bill = t.calculate_bill(current_time=now)
        violations_list.append({
            'ticket': t,
            'duration_minutes': mins,
            'hours_elapsed': round(mins / 60, 1),
            'bill': bill,
        })

    return render(request, 'parking_app/reports/report_violations.html', {
        'violations_list': violations_list,
        'threshold_hours': threshold_hours,
        'count': len(violations_list),
    })
