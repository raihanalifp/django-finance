from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Category, Transaction


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'type')
    list_filter = ('type',)
    search_fields = ('name',)


@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = ('category', 'amount', 'date', 'created_at')
    list_filter = ('category', 'date')
    search_fields = ('description',)
    ordering = ('-date',)
