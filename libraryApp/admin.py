from django.contrib import admin
from .models import UserProfile, Category, BookSet, Volume, Purchase

class VolumeInline(admin.TabularInline):
    model = Volume
    extra = 1  # Easy adding volumes inline

@admin.register(BookSet)
class BookSetAdmin(admin.ModelAdmin):
    inlines = [VolumeInline]
    list_display = ('title', 'author', 'access_type', 'price')
    search_fields = ('title', 'description')
    filter_horizontal = ('categories',)  # Nice UI for ManyToMany

admin.site.register([UserProfile, Category, Purchase])




