# core/views.py
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Case, When, IntegerField, F
from django.db.models import Q, Sum, Case, When, IntegerField, F

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import PickForm
from .models import Game, Pick

from django.contrib.auth.models import User
from django.shortcuts import render
from django.db.models import F, Q, Sum, Case, When, IntegerField  # if you still have the annotate version
from .models import Season, Pick, GameResult  # ensure Pick/GameResult are imported if referenced

from .forms import SignupForm
from .models import Profile
from .forms import PickForm
from .models import Game, Pick, Season, Week

# Public home: current week games + your picks if logged in

def home(request):
    season = Season.objects.order_by('-year').first()
    week = Week.objects.filter(season=season, lock_at__gte=timezone.now()).order_by('week_number').first()
    if not week:
        week = Week.objects.filter(season=season).order_by('-week_number').first()
    games = list(Game.objects.filter(week=week).select_related('week'))  # make it a list so we can annotate

    user_picks = {}
    if request.user.is_authenticated:
        user_picks = {p.game_id: p for p in Pick.objects.filter(user=request.user, game__in=games)}

    # attach the user's pick (if any) to each game
    for g in games:
        g.user_pick = user_picks.get(g.id)

    return render(request, 'home.html', {
        'season': season, 'week': week, 'games': games
    })

@login_required
def make_pick(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    # Server-side lock (authoritative)
    if timezone.now() >= game.kickoff_at:
        messages.error(request, "Picks are locked for this game (kickoff has passed).")
        return redirect('home')

    pick, _ = Pick.objects.get_or_create(user=request.user, game=game)

    if request.method == 'POST':
        form = PickForm(request.POST, instance=pick)
        if form.is_valid():
            # Double-check right before saving in case of race
            if timezone.now() >= game.kickoff_at:
                messages.error(request, "Picks are locked for this game (kickoff has passed).")
                return redirect('home')
            form.save()
            messages.success(request, "Pick saved.")
            return redirect('home')
    else:
        form = PickForm(instance=pick)

    return render(request, 'make_pick.html', {'game': game, 'form': form})

# Standings: sum wins/losses across season

def standings(request):
    season = Season.objects.order_by('-year').first()
    users = []

    for u in User.objects.all():
        picks = (Pick.objects
                 .filter(user=u, game__week__season=season)
                 .select_related('game__gameresult'))
        wins, losses = 0, 0
        for p in picks:
            try:
                r = p.game.gameresult
            except GameResult.DoesNotExist:
                continue
            if r.winner is None:
                continue
            if p.selection == r.winner:
                wins += 1
            else:
                losses += 1
        users.append({
            "username": u.username,
            "wins": wins,
            "losses": losses,
            "pot": 2 * losses,
        })

    users.sort(key=lambda x: (-x["wins"], x["losses"], x["username"]))
    return render(request, "standings.html", {"season": season, "rows": users})

# Simple signup view

def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()  # creates the User (signal runs here)

            # after user = form.save()
            Profile.objects.update_or_create(
                user=user,
                defaults={"venmo_handle": form.cleaned_data.get("venmo_handle", "").lstrip("@")}
            )
            venmo = form.cleaned_data.get('venmo_handle', '').lstrip('@')
            # set venmo safely without creating a duplicate profile:
            Profile.objects.update_or_create(
                user=user,
                defaults={"venmo_handle": venmo}
            )
            login(request, user)
            return redirect('home')
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})
