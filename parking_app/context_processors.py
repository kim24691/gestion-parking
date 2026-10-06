from django.utils import timezone
from .models import ParkingZone, ParkingTicket

def parking_context(request):
    """
    Context processor fournissant les variables globales pour les templates :
    - Ville, Monnaie (BIF), Titre académique
    - Compteur rapide de places occupées / libres globales
    """
    context = {
        'APP_NAME': 'Parking Bujumbura',
        'CITY_NAME': 'Ville de Bujumbura',
        'COUNTRY_NAME': 'Burundi',
        'CURRENCY': 'BIF',
        'ACADEMIC_INSTITUTION': 'Bujumbura International University (BIU) - Faculté de Génie Logiciel',
        'CURRENT_YEAR': timezone.now().year,
        'NOW': timezone.now(),
    }

    if request.user.is_authenticated:
        total_capacity = sum(z.total_spots for z in ParkingZone.objects.filter(is_active=True))
        occupied_count = ParkingTicket.objects.filter(status='EN_COURS', is_active=True).count()
        context['global_total_spots'] = total_capacity
        context['global_occupied_spots'] = occupied_count
        context['global_available_spots'] = max(0, total_capacity - occupied_count)
    
    return context
