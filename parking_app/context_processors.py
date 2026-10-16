from django.utils import timezone
from .models import ParkingZone, ParkingTicket

def parking_context(request):
    """
    Context processor fournissant les variables globales pour les templates :
    - Ville, Monnaie (BIF), Service officiel de la Mairie
    - Compteur rapide de places occupées / libres globales et par zone
    """
    context = {
        'APP_NAME': 'Parking Bujumbura',
        'CITY_NAME': 'Mairie de Bujumbura',
        'MUNICIPAL_SERVICE': 'Régie des Parkings Publics Municipaux',
        'COUNTRY_NAME': 'Burundi',
        'CURRENCY': 'BIF',
        'CURRENT_YEAR': timezone.now().year,
        'NOW': timezone.now(),
    }

    if request.user.is_authenticated:
        if request.user.is_admin_user():
            total_capacity = sum(z.total_spots for z in ParkingZone.objects.filter(is_active=True))
            occupied_count = ParkingTicket.objects.filter(status='EN_COURS', is_active=True).count()
            context['global_total_spots'] = total_capacity
            context['global_occupied_spots'] = occupied_count
            context['global_available_spots'] = max(0, total_capacity - occupied_count)
        elif request.user.assigned_zone:
            zone = request.user.assigned_zone
            context['global_total_spots'] = zone.total_spots
            context['global_occupied_spots'] = zone.get_occupied_spots()
            context['global_available_spots'] = zone.get_available_spots()
    
    return context
