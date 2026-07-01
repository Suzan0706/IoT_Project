from django import template
from django.utils.safestring import mark_safe
import datetime

register = template.Library()

DOMAIN_COLORS = {
    'transport': '#4D77FF',
    'housing': '#8A2BE2',
    'heritage': '#B4A0FF',
    'energy': '#00ff9d',
    'water': '#ffc107',
    'air quality': '#00BCD4',
    'agriculture': '#96A028',
    'health': '#E91E63',
}


@register.filter
def domain_color(name):
    return DOMAIN_COLORS.get(name.lower(), '#4D77FF')


@register.filter
def date_range(dataset):
    start = dataset.start_date.strftime('%Y-%m') if dataset.start_date else '—'
    if dataset.end_date:
        end = dataset.end_date.strftime('%Y-%m')
    else:
        end = 'ongoing'
    return f'{start} → {end}'


@register.filter
def quality_stars(score):
    full = round(float(score))
    if full > 5:
        full = 5
    if full < 0:
        full = 0
    empty = 5 - full
    filled = '<span style="color:#ff9800;">★</span>' * full
    empty_stars = '<span style="color:rgba(255,255,255,0.15);">★</span>' * empty
    return mark_safe(filled + empty_stars)


@register.filter
def dataset_tags(dataset):
    tags = []
    if dataset.domain:
        tags.append(dataset.domain.name.upper())
    if dataset.sensor_type:
        tags.append(dataset.sensor_type.upper())
    if dataset.iuc_project_code:
        tags.append(dataset.iuc_project_code.upper())
    return tags
