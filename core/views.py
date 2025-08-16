# core/views.py
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Case, When, IntegerField, F
from django.db.models import Q, Sum, Case, When, IntegerField, F
from django.db import transaction
from .models import Profile

from decimal import Decimal
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Prefetch
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
import csv

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

@transaction.atomic
def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()  # signal runs here; profile will exist (or be created)
            venmo = form.cleaned_data.get('venmo_handle', '').lstrip('@')

            # Idempotent: update if exists, create if missing
            Profile.objects.update_or_create(
                user=user,
                defaults={"venmo_handle": venmo},
            )

            login(request, user)
            return redirect('home')
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})


from .models import Week, Pick, Profile  # adjust import paths to match your app

LOSS_FEE = Decimal("2.00")   # $2 per loss — change here if your rule differs

def staff_required(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(staff_required)
def weekly_dues(request, week_id=None):
    """
    Admin-only table of per-user dues for the selected week.
    """
    # Choose the week: explicit by URL, or default to latest
    if week_id is None:
        week = Week.objects.order_by("-season__year", "-number").first()
        if not week:
            return render(request, "admin/weekly_dues.html", {
                "week": None, "weeks": [], "rows": [], "total": Decimal("0.00"),
                "message": "No weeks exist yet."
            })
    else:
        week = get_object_or_404(Week, pk=week_id)

    # Prefetch all picks for the week with their related game+result
    picks_qs = (Pick.objects
                .select_related("user", "game", "game__gameresult")
                .filter(game__week=week))

    # Build per-user tally in Python (clear + robust to schema differences)
    per_user = {}  # user_id -> {"user": u, "venmo": str, "losses": int}
    for p in picks_qs:
        u = p.user
        d = per_user.setdefault(u.id, {"user": u, "venmo": getattr(getattr(u, "profile", None), "venmo_handle", ""), "losses": 0})
        # Count a loss only if the game has a result
        r = getattr(p.game, "gameresult", None)
        if r:
            if getattr(r, "winner", None) != getattr(p, "selection", None):
                d["losses"] += 1

    # Produce rows sorted by username
    rows = []
    total = Decimal("0.00")
    for d in sorted(per_user.values(), key=lambda x: x["user"].username.lower()):
        amount = LOSS_FEE * d["losses"]
        total += amount
        rows.append({
            "username": d["user"].username,
            "venmo": d["venmo"] or "—",
            "losses": d["losses"],
            "amount": amount,
        })

    # CSV export: /weekly-dues/<id>/?format=csv
    if request.GET.get("format") == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="dues_week_{week.id}.csv"'
        w = csv.writer(resp)
        w.writerow(["Username", "Venmo", "Losses", "Amount Owed"])
        for r in rows:
            w.writerow([r["username"], r["venmo"], r["losses"], f"{r['amount']:.2f}"])
        w.writerow([])
        w.writerow(["TOTAL", "", "", f"{total:.2f}"])
        return resp

    # Render HTML
    weeks = Week.objects.order_by("season__year", "number").all()
    return render(request, "admin/weekly_dues.html", {
        "week": week,
        "weeks": weeks,
        "rows": rows,
        "total": total,
        "loss_fee": LOSS_FEE,
    })
