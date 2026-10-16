import io
import datetime
from django.utils import timezone
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm


def get_client_ip(request):
    """Récupère l'adresse IP réelle du client effectuant la requête"""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_activity(request, action, target_model, target_id="", target_repr="", details=""):
    """
    Enregistre une entrée dans le journal d'audit (ActivityLog).
    Garantit la traçabilité complète des actions utilisateurs.
    """
    from .models import ActivityLog
    
    user = getattr(request, 'user', None)
    if user and not user.is_authenticated:
        user = None

    ip_address = get_client_ip(request)

    ActivityLog.objects.create(
        user=user,
        action=action,
        target_model=str(target_model),
        target_id=str(target_id),
        target_repr=str(target_repr)[:250],
        details=str(details),
        ip_address=ip_address
    )


def generate_ticket_number():
    """
    Génère un identifiant de ticket unique au format :
    BJM-YYYYMMDD-XXXXXX (ex: BJM-20261006-894123)
    """
    import random
    now = timezone.now()
    date_str = now.strftime('%Y%m%d')
    random_suffix = f"{random.randint(1000, 9999)}"
    return f"BJM-{date_str}-{random_suffix}"


def admin_required(view_func):
    """
    Décorateur restreignant l'accès aux utilisateurs ayant le rôle Administrateur.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Veuillez vous connecter pour accéder à cette page.")
            return redirect('login')
        if not (request.user.role == 'ADMIN' or request.user.is_superuser):
            messages.error(request, "Accès refusé. Vous devez être Administrateur pour effectuer cette action.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def agent_or_admin_required(view_func):
    """
    Décorateur autorisant les Agents de parking et les Administrateurs.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Veuillez vous connecter pour accéder à cette page.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def generate_ticket_pdf(ticket):
    """
    Génère un reçu/ticket de stationnement officiel au format PDF
    avec en-tête officiel Mairie de Bujumbura - Régie des Parkings Publics.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(80 * mm, 160 * mm),  # Format ticket de caisse / reçu de poche
        rightMargin=4 * mm,
        leftMargin=4 * mm,
        topMargin=6 * mm,
        bottomMargin=6 * mm
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TicketTitle',
        parent=styles['Heading2'],
        alignment=1, # Centré
        fontSize=10,
        leading=12,
        textColor=colors.HexColor('#1a365d')
    )
    subtitle_style = ParagraphStyle(
        'TicketSubtitle',
        parent=styles['Normal'],
        alignment=1,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#4b5563')
    )
    body_style = ParagraphStyle(
        'TicketBody',
        parent=styles['Normal'],
        fontSize=8,
        leading=11
    )
    strong_style = ParagraphStyle(
        'TicketStrong',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        fontName='Helvetica-Bold'
    )
    center_bold = ParagraphStyle(
        'CenterBold',
        parent=styles['Normal'],
        alignment=1,
        fontSize=12,
        leading=14,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#059669')
    )

    elements = []

    # En-tête officiel Mairie de Bujumbura
    elements.append(Paragraph("<b>REPUBLIQUE DU BURUNDI</b>", subtitle_style))
    elements.append(Paragraph("<b>MAIRIE DE BUJUMBURA</b>", title_style))
    elements.append(Paragraph("Régie des Parkings Publics Municipaux", subtitle_style))
    elements.append(Paragraph("<font size=7>Direction des Services Financiers et Fiscaux</font>", subtitle_style))
    elements.append(Spacer(1, 2 * mm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1')))
    elements.append(Spacer(1, 2 * mm))

    # Titre du Ticket
    elements.append(Paragraph(f"<b>TICKET N° {ticket.ticket_number}</b>", ParagraphStyle('TNum', alignment=1, fontSize=9, fontName='Helvetica-Bold')))
    elements.append(Spacer(1, 2 * mm))

    # Tableau des détails
    data = [
        [Paragraph("<b>Plaque Immat. :</b>", body_style), Paragraph(f"<b>{ticket.plate_number}</b>", strong_style)],
        [Paragraph("Type Véhicule :", body_style), Paragraph(ticket.vehicle_type.name, body_style)],
        [Paragraph("Zone :", body_style), Paragraph(ticket.zone.name, body_style)],
        [Paragraph("Date/Heure Entrée :", body_style), Paragraph(ticket.entry_time.strftime('%d/%m/%Y %H:%M'), body_style)],
    ]

    if ticket.exit_time:
        data.extend([
            [Paragraph("Date/Heure Sortie :", body_style), Paragraph(ticket.exit_time.strftime('%d/%m/%Y %H:%M'), body_style)],
            [Paragraph("Durée calculée :", body_style), Paragraph(ticket.formatted_duration(), body_style)],
            [Paragraph("Frais Parking :", body_style), Paragraph(f"{ticket.parking_fee:,.0f} BIF".replace(',', ' '), body_style)],
        ])
        if ticket.has_infraction:
            data.extend([
                [Paragraph("<font color='#b91c1c'><b>Amende Infraction :</b></font>", body_style), Paragraph(f"<font color='#b91c1c'><b>+{ticket.infraction_fine:,.0f} BIF</b></font>".replace(',', ' '), strong_style)],
                [Paragraph("Motif Infraction :", body_style), Paragraph(ticket.get_infraction_type_display(), body_style)],
            ])
        data.append([Paragraph("Mode Paiement :", body_style), Paragraph(ticket.get_payment_method_display(), body_style)])

    table = Table(data, colWidths=[28 * mm, 44 * mm])
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 3 * mm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1')))
    elements.append(Spacer(1, 2 * mm))

    if ticket.status == 'PAYE':
        elements.append(Paragraph(f"MONTANT ENCAISSÉ :", subtitle_style))
        elements.append(Paragraph(f"{ticket.amount_paid:,.0f} BIF".replace(',', ' '), center_bold))
        agent_name = ticket.closed_by.get_full_name() or ticket.closed_by.username if ticket.closed_by else "Système"
        elements.append(Paragraph(f"<font size=7>Perçu par : {agent_name}</font>", subtitle_style))
    else:
        elements.append(Paragraph(f"STATUT : EN COURS DE STATIONNEMENT", ParagraphStyle('St', alignment=1, fontSize=8, fontName='Helvetica-Bold', textColor=colors.HexColor('#2563eb'))))
        agent_name = ticket.created_by.get_full_name() or ticket.created_by.username if ticket.created_by else "Système"
        elements.append(Paragraph(f"<font size=7>Agent enregistreur : {agent_name}</font>", subtitle_style))

    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph("Conservez ce ticket. En cas de perte, une pénalité forfaitaire de 50 000 BIF sera appliquée conformément aux règlements municipaux.", ParagraphStyle('Notice', alignment=1, fontSize=6, leading=8, textColor=colors.HexColor('#6b7280'))))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def generate_financial_report_pdf(start_date, end_date, total_revenue, total_tickets, zone_data, vehicle_data):
    """
    Génère un rapport financier complet et professionnel au format PDF (A4)
    des recettes de stationnement en Franc Burundi (BIF).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        alignment=1,
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#1a365d'),
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        alignment=1,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#4b5563')
    )
    section_title = ParagraphStyle(
        'SecTitle',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1e40af'),
        fontName='Helvetica-Bold'
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=9,
        leading=12
    )

    elements = []

    # En-tête
    elements.append(Paragraph("RÉPUBLIQUE DU BURUNDI", subtitle_style))
    elements.append(Paragraph("VILLE DE BUJUMBURA - GESTION DES PARKINGS PUBLICS", title_style))
    elements.append(Paragraph("Direction Générale des Services Techniques et Fiscaux Municipaux", subtitle_style))
    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1a365d')))
    elements.append(Spacer(1, 4 * mm))

    # Titre du rapport
    period_str = f"Période : {start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}"
    elements.append(Paragraph(f"<b>RAPPORT FINANCIER DES RECETTES DE STATIONNEMENT (BIF)</b>", section_title))
    elements.append(Paragraph(period_str, body_style))
    elements.append(Paragraph(f"Édité le : {timezone.now().strftime('%d/%m/%Y à %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 5 * mm))

    # Résumé exécutif
    summary_data = [
        [
            Paragraph("<b>Total des Tickets Clôturés</b>", body_style),
            Paragraph(f"<b>{total_tickets}</b>", body_style),
            Paragraph("<b>Recettes Totales Globales</b>", body_style),
            Paragraph(f"<b>{total_revenue:,.0f} BIF</b>".replace(',', ' '), ParagraphStyle('SR', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor('#059669'))),
        ]
    ]
    sum_table = Table(summary_data, colWidths=[5 * cm, 3 * cm, 5 * cm, 5 * cm])
    sum_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(sum_table)
    elements.append(Spacer(1, 6 * mm))

    # Recettes par Zone
    elements.append(Paragraph("<b>1. Répartition des Recettes par Zone de Parking</b>", section_title))
    elements.append(Spacer(1, 2 * mm))

    zone_rows = [
        [
            Paragraph("<b>Zone de Stationnement</b>", body_style),
            Paragraph("<b>Capacité</b>", body_style),
            Paragraph("<b>Tickets Payés</b>", body_style),
            Paragraph("<b>Recettes (BIF)</b>", body_style),
            Paragraph("<b>Part (%)</b>", body_style)
        ]
    ]

    for z in zone_data:
        pct = (z['revenue'] / total_revenue * 100) if total_revenue > 0 else 0
        zone_rows.append([
            Paragraph(f"{z['name']} ({z['code']})", body_style),
            Paragraph(str(z['total_spots']), body_style),
            Paragraph(str(z['tickets_count']), body_style),
            Paragraph(f"{z['revenue']:,.0f} BIF".replace(',', ' '), body_style),
            Paragraph(f"{pct:.1f} %", body_style)
        ])

    zone_table = Table(zone_rows, colWidths=[5.5 * cm, 2.5 * cm, 3 * cm, 4.5 * cm, 2.5 * cm])
    zone_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(zone_table)
    elements.append(Spacer(1, 6 * mm))

    # Recettes par Type de Véhicule
    elements.append(Paragraph("<b>2. Répartition par Type de Véhicule</b>", section_title))
    elements.append(Spacer(1, 2 * mm))

    veh_rows = [
        [
            Paragraph("<b>Type de Véhicule</b>", body_style),
            Paragraph("<b>Nombre de Véhicules</b>", body_style),
            Paragraph("<b>Recettes Totales (BIF)</b>", body_style),
            Paragraph("<b>Tarif Moyen / Véhicule</b>", body_style)
        ]
    ]

    for v in vehicle_data:
        avg = (v['revenue'] / v['count']) if v['count'] > 0 else 0
        veh_rows.append([
            Paragraph(v['name'], body_style),
            Paragraph(str(v['count']), body_style),
            Paragraph(f"{v['revenue']:,.0f} BIF".replace(',', ' '), body_style),
            Paragraph(f"{avg:,.0f} BIF".replace(',', ' '), body_style)
        ])

    veh_table = Table(veh_rows, colWidths=[5.5 * cm, 3.5 * cm, 4.5 * cm, 4.5 * cm])
    veh_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f766e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(veh_table)
    elements.append(Spacer(1, 8 * mm))

    # Signatures
    elements.append(Spacer(1, 10 * mm))
    sig_data = [
        [
            Paragraph("<b>Le Chef de Service Parkings Municipaux</b>", subtitle_style),
            Paragraph("<b>Le Responsable Administratif & Financier</b>", subtitle_style)
        ],
        [
            Paragraph("<br/><br/>(Signature et Sceau)", subtitle_style),
            Paragraph("<br/><br/>(Signature et Sceau)", subtitle_style)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[9 * cm, 9 * cm])
    elements.append(sig_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
