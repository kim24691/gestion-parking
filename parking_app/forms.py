from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from .models import CustomUser, ParkingZone, VehicleType, Tariff, ParkingTicket

class BootstrapFormMixin:
    """Ajoute automatiquement les classes Bootstrap 5 aux champs du formulaire"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class UserLoginForm(BootstrapFormMixin, AuthenticationForm):
    """Formulaire de connexion personnalisé"""
    username = forms.CharField(
        label="Nom d'utilisateur ou Matricule",
        widget=forms.TextInput(attrs={'placeholder': 'Ex: agent1 ou admin', 'autofocus': True})
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'})
    )


class CustomUserCreationForm(BootstrapFormMixin, forms.ModelForm):
    """Création d'un utilisateur / agent par l'administrateur"""
    password = forms.CharField(
        label="Mot de passe initial",
        widget=forms.PasswordInput(attrs={'placeholder': 'Mot de passe sécurisé'})
    )
    confirm_password = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={'placeholder': 'Répétez le mot de passe'})
    )

    class Meta:
        model = CustomUser
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'role', 'badge_id', 'phone', 'assigned_zone', 'is_active'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Nom d' + "'" + 'utilisateur unique'}),
            'badge_id': forms.TextInput(attrs={'placeholder': 'Ex: AGT-BJM-001'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Ex: +257 79 123 456'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Les deux mots de passe ne correspondent pas.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class CustomUserUpdateForm(BootstrapFormMixin, forms.ModelForm):
    """Modification d'un utilisateur existant"""
    new_password = forms.CharField(
        label="Nouveau mot de passe (laisser vide pour ne pas changer)",
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Optionnel'})
    )

    class Meta:
        model = CustomUser
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'role', 'badge_id', 'phone', 'assigned_zone', 'is_active'
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        new_pwd = self.cleaned_data.get('new_password')
        if new_pwd:
            user.set_password(new_pwd)
        if commit:
            user.save()
        return user


class ParkingZoneForm(BootstrapFormMixin, forms.ModelForm):
    """Création et modification des zones de stationnement"""
    class Meta:
        model = ParkingZone
        fields = ['name', 'code', 'description', 'total_spots', 'hourly_rate_default', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ex: Centre-Ville'}),
            'code': forms.TextInput(attrs={'placeholder': 'Ex: CV'}),
            'description': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Précisions sur la localisation...'}),
            'total_spots': forms.NumberInput(attrs={'min': 1, 'placeholder': 'Nombre de places disponibles'}),
            'hourly_rate_default': forms.NumberInput(attrs={'step': 100, 'placeholder': 'Montant en BIF'}),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code')
        return code.strip().upper() if code else code


class VehicleTypeForm(BootstrapFormMixin, forms.ModelForm):
    """Formulaire de gestion des types de véhicules"""
    class Meta:
        model = VehicleType
        fields = ['code', 'name', 'icon_class', 'default_hourly_rate', 'default_daily_rate', 'description', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'placeholder': 'Ex: VOITURE, MOTO, BUS'}),
            'name': forms.TextInput(attrs={'placeholder': 'Ex: Voiture de tourisme'}),
            'icon_class': forms.TextInput(attrs={'placeholder': 'fa-car, fa-motorcycle, fa-bus, fa-truck'}),
            'default_hourly_rate': forms.NumberInput(attrs={'step': 100, 'placeholder': 'Tarif horaire en BIF'}),
            'default_daily_rate': forms.NumberInput(attrs={'step': 500, 'placeholder': 'Tarif journalier en BIF'}),
            'description': forms.TextInput(attrs={'placeholder': 'Description sommaire'}),
        }


class TariffForm(BootstrapFormMixin, forms.ModelForm):
    """Formulaire de paramétrage de la grille tarifaire en BIF"""
    class Meta:
        model = Tariff
        fields = ['vehicle_type', 'zone', 'tariff_type', 'amount_bif', 'grace_period_minutes', 'max_daily_cap_bif', 'is_active']
        widgets = {
            'amount_bif': forms.NumberInput(attrs={'step': 100, 'placeholder': 'Montant en BIF'}),
            'grace_period_minutes': forms.NumberInput(attrs={'placeholder': 'Minutes gratuites'}),
            'max_daily_cap_bif': forms.NumberInput(attrs={'step': 500, 'placeholder': 'Plafond journalier en BIF'}),
        }


class TicketEntryForm(BootstrapFormMixin, forms.ModelForm):
    """
    Enregistrement de l'entrée d'un véhicule dans le parking municipal.
    Effectue la vérification en temps réel de la disponibilité de place dans la zone.
    """
    class Meta:
        model = ParkingTicket
        fields = ['plate_number', 'vehicle_type', 'zone']
        widgets = {
            'plate_number': forms.TextInput(attrs={
                'placeholder': 'Ex: IT 4520 A, RA 1234 B',
                'class': 'form-control form-control-lg text-uppercase fw-bold',
                'autofocus': True
            }),
        }

    def clean_plate_number(self):
        plate = self.cleaned_data.get('plate_number', '').strip().upper()
        if len(plate) < 3:
            raise ValidationError("Le numéro d'immatriculation est trop court.")
        
        # Vérification si le véhicule est déjà stationné (sans être sorti)
        active_ticket = ParkingTicket.objects.filter(
            plate_number=plate,
            status='EN_COURS',
            is_active=True
        ).first()
        if active_ticket:
            raise ValidationError(
                f"Ce véhicule ({plate}) est déjà enregistré comme stationné dans la zone "
                f"'{active_ticket.zone.name}' depuis le {active_ticket.entry_time.strftime('%d/%m/%Y %H:%M')} (Ticket N° {active_ticket.ticket_number})."
            )
        return plate

    def clean_zone(self):
        zone = self.cleaned_data.get('zone')
        if zone:
            if not zone.is_active:
                raise ValidationError(f"La zone '{zone.name}' est actuellement inactive.")
            if zone.get_available_spots() <= 0:
                raise ValidationError(
                    f"La zone '{zone.name}' est complète ({zone.total_spots}/{zone.total_spots} places occupées). "
                    "Veuillez orienter le conducteur vers une autre zone disponible."
                )
        return zone


class TicketCheckoutForm(BootstrapFormMixin, forms.Form):
    """Validation de sortie et encaissement en BIF"""
    payment_method = forms.ChoiceField(
        choices=ParkingTicket.PAYMENT_METHOD_CHOICES,
        label="Mode de paiement",
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    payment_reference = forms.CharField(
        required=False,
        label="Référence Transaction Mobile (Lumicash / EcoCash)",
        widget=forms.TextInput(attrs={'placeholder': 'Ex: TXN-984123 (Optionnel pour espèces)'})
    )
    amount_paid = forms.DecimalField(
        max_digits=12,
        decimal_places=0,
        label="Montant perçu (BIF)",
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-lg fw-bold text-success'})
    )


class TicketDeactivateForm(BootstrapFormMixin, forms.Form):
    """Désactivation logique ou annulation d'un ticket avec justification obligatoire"""
    cancellation_reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Indiquez le motif précis de l\'annulation ou de la désactivation...'}),
        label="Motif d'annulation / désactivation",
        required=True
    )


class TicketFilterForm(forms.Form):
    """Filtres pour la recherche avancée des tickets"""
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Immatriculation ou N° Ticket...'}),
        label="Recherche"
    )
    zone = forms.ModelChoiceField(
        queryset=ParkingZone.objects.all(),
        required=False,
        empty_label="Toutes les zones",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Zone"
    )
    vehicle_type = forms.ModelChoiceField(
        queryset=VehicleType.objects.all(),
        required=False,
        empty_label="Tous les types",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Type véhicule"
    )
    status = forms.ChoiceField(
        choices=[('', 'Tous les statuts')] + ParkingTicket.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Statut"
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Date début"
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Date fin"
    )
