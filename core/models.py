# core/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    venmo_handle = models.CharField(max_length=30, blank=True, help_text="Venmo username without @")

    def __str__(self):
        return f"Profile({self.user.username})"
    
@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    # Safe if already exists; won’t double-insert
    Profile.objects.get_or_create(user=instance)

# Auto-create a Profile for each new user
# @receiver(post_save, sender=User)
# def create_or_update_user_profile(sender, instance, created, **kwargs):
#     if created:
#         Profile.objects.create(user=instance)
#     else:
#         instance.profile.save()

class Season(models.Model):
    year = models.PositiveIntegerField(unique=True)
    buy_in_dollars = models.DecimalField(max_digits=7, decimal_places=2, default=0)  # dollars
    def __str__(self):
        return str(self.year)

class Week(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    week_number = models.PositiveIntegerField()
    start_at = models.DateTimeField()
    lock_at = models.DateTimeField()
    class Meta:
        unique_together = ('season', 'week_number')
        ordering = ['season__year', 'week_number']
    def __str__(self):
        return f"{self.season.year} - Week {self.week_number}"

class Game(models.Model):
    GAMEDAY = 'gameday'
    WILDCARD = 'wildcard'
    KIND_CHOICES = [(GAMEDAY, 'Gameday'), (WILDCARD, 'Wildcard')]

    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    kind = models.CharField(max_length=8, choices=KIND_CHOICES)
    home_team = models.CharField(max_length=64)
    away_team = models.CharField(max_length=64)
    kickoff_at = models.DateTimeField()
    spread = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('week', 'kind')  # enforce exactly one Gameday & one Wildcard per week
        ordering = ['kickoff_at']

    def is_locked(self):
        return timezone.now() >= self.kickoff_at

    def __str__(self):
        return f"{self.week}: {self.away_team} @ {self.home_team} ({self.kind})"

class GameResult(models.Model):
    WINNER_CHOICES = [('home', 'Home'), ('away', 'Away')]
    game = models.OneToOneField(Game, on_delete=models.CASCADE)
    home_score = models.PositiveIntegerField(null=True, blank=True)
    away_score = models.PositiveIntegerField(null=True, blank=True)
    winner = models.CharField(max_length=4, choices=WINNER_CHOICES, null=True, blank=True)

    def __str__(self):
        return f"Result: {self.game} -> {self.winner or 'TBD'}"

class Pick(models.Model):
    SELECTION = [('home','Home'), ('away','Away')]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    selection = models.CharField(max_length=4, choices=SELECTION)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'game')

    def outcome(self):
        try:
            r = self.game.gameresult
        except GameResult.DoesNotExist:
            return None
        if r.winner is None:
            return None
        return 'win' if self.selection == r.winner else 'loss'
