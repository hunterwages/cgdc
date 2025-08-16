# core/admin.py
from django.contrib import admin
from .models import Season, Week, Game, GameResult, Pick, Profile

@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ('year', 'buy_in_dollars')

@admin.register(Week)
class WeekAdmin(admin.ModelAdmin):
    list_display = ('season', 'week_number', 'start_at', 'lock_at')
    list_filter = ('season',)

class GameResultInline(admin.StackedInline):
    model = GameResult
    extra = 0

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('week', 'kind', 'away_team', 'home_team', 'kickoff_at')
    list_filter = ('week__season', 'week__week_number', 'kind')
    inlines = [GameResultInline]

@admin.register(Pick)
class PickAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'selection', 'created_at')
    list_filter = ('game__week__season', 'game__week__week_number', 'selection')

from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "venmo_handle")
    search_fields = ("user__username", "venmo_handle")
