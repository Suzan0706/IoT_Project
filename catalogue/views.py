from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.db.models import Q, Count, Avg, Sum, F, Case, When, IntegerField
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
import csv
from django.conf import settings
from .models import Dataset, Domain, AuditLog, Feedback, Profile, DatasetCategory, SensorType, SystemSetting, Backup, SystemLog
from .forms import DatasetForm, DatasetRegistrationForm, AdminProfileForm, LoginForm, SignupForm, FeedbackForm, UserAccountSettingsForm, GeneralSettingsForm, DatasetSettingsForm, DatasetCategoryForm, SensorTypeForm, ResearchDomainForm, UserSettingsForm, SecuritySettingsForm, BackupForm, ProfileSettingsForm, AccountSettingsForm, NotificationPreferencesForm, PrivacySettingsForm, AppearanceSettingsForm, LanguageSettingsForm, TimeZoneSettingsForm, ProfilePictureForm
import json
import os
import time
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import authenticate, login, get_user_model


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'role', None) == 'Admin'):
            return render(request, '403.html', status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def custom_admin_login(request):
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_dashboard')
    if request.user.is_authenticated:
        return redirect('user_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)
        if user is not None and (user.is_staff or user.is_superuser):
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid admin credentials or insufficient permissions.')
            return redirect('custom_admin_login')

    return render(request, 'admin_login.html')


def auto_reload_status(request):
    if not settings.DEBUG:
        return JsonResponse({'reload': False, 'timestamp': time.time(), 'files': []})

    project_root = settings.BASE_DIR.parent
    state_path = os.path.join(settings.BASE_DIR, '.auto_reload_state.json')
    watch_extensions = {'.py', '.html', '.js', '.css', '.json', '.txt', '.md', '.svg', '.ico'}
    excluded_dirs = {'__pycache__', '.git', '.venv', 'venv', 'node_modules', 'media', 'static', 'dist'}

    def iter_watchable_files(root):
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [name for name in dirnames if name not in excluded_dirs]
            for filename in filenames:
                if os.path.splitext(filename)[1].lower() in watch_extensions:
                    yield os.path.join(dirpath, filename)

    latest_mtime = 0.0
    for file_path in iter_watchable_files(project_root):
        try:
            latest_mtime = max(latest_mtime, os.path.getmtime(file_path))
        except OSError:
            continue

    if os.path.exists(state_path):
        with open(state_path, 'r', encoding='utf-8') as handle:
            state = json.load(handle)
        last_seen = float(state.get('latest_seen_mtime', 0.0))
        should_reload = latest_mtime > last_seen
        state['latest_seen_mtime'] = latest_mtime
        with open(state_path, 'w', encoding='utf-8') as handle:
            json.dump(state, handle)
        return JsonResponse({'reload': should_reload, 'timestamp': time.time(), 'files': []})

    with open(state_path, 'w', encoding='utf-8') as handle:
        json.dump({'latest_seen_mtime': latest_mtime}, handle)

    return JsonResponse({'reload': False, 'timestamp': time.time(), 'files': []})


@admin_required
def dashboard_view(request):
    total_users = User.objects.count()
    total_datasets = Dataset.objects.filter(status='live').count()
    total_downloads = Dataset.objects.filter(status='live').aggregate(total=Sum('download_count'))['total'] or 0
    pending_datasets = Dataset.objects.filter(status='pending').count()
    total_feedback = Feedback.objects.count()

    today = timezone.now().date()
    datasets_this_month = Dataset.objects.filter(status='live', created_at__date__gte=today.replace(day=1)).count()
    new_users_this_month = User.objects.filter(date_joined__date__gte=today.replace(day=1)).count()

    most_downloaded = Dataset.objects.filter(status='live').select_related('domain', 'researcher').order_by('-download_count').first()
    domain_stats = Domain.objects.annotate(
        dataset_count=Count('datasets', filter=Q(datasets__status='live')),
        download_sum=Sum('datasets__download_count', filter=Q(datasets__status='live'))
    ).order_by('-dataset_count')

    feedback_stats = {
        'total': total_feedback,
        'new': Feedback.objects.filter(status='new').count(),
        'reviewed': Feedback.objects.filter(status='reviewed').count(),
        'resolved': Feedback.objects.filter(status='resolved').count(),
        'avg_rating': Feedback.objects.aggregate(avg=Avg('rating'))['avg'] or 0,
    }

    recent_logs = AuditLog.objects.all().select_related('user')[:10]

    try:
        admin_profile = request.user.profile
    except Profile.DoesNotExist:
        admin_profile = None

    admin_unread_notifications_count = 0
    admin_recent_notifications = []
    if request.user.is_authenticated:
        try:
            from catalogue.notifications import get_unread_notifications_count, get_recent_notifications
            admin_unread_notifications_count = get_unread_notifications_count(request.user)
            admin_recent_notifications = get_recent_notifications(request.user, limit=5)
        except Exception:
            pass

    context = {
        'total_users': total_users,
        'total_datasets': total_datasets,
        'total_downloads': total_downloads,
        'pending_datasets': pending_datasets,
        'total_feedback': total_feedback,
        'datasets_this_month': datasets_this_month,
        'new_users_this_month': new_users_this_month,
        'most_downloaded': most_downloaded,
        'domain_stats': domain_stats,
        'feedback_stats': feedback_stats,
        'recent_logs': recent_logs,
        'admin_profile': admin_profile,
        'admin_unread_notifications_count': admin_unread_notifications_count,
        'admin_recent_notifications': admin_recent_notifications,
    }
    return render(request, 'admin_dashboard.html', context)


@admin_required
def admin_theme_settings(request):
    profile = None
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)

    if request.method == 'POST':
        admin_theme = request.POST.get('admin_theme_preference', 'system')
        if admin_theme not in ['light', 'dark', 'system']:
            admin_theme = 'system'
        profile.admin_theme_preference = admin_theme
        profile.save()
        messages.success(request, 'Admin theme preference updated successfully.')
        return redirect('admin_dashboard')

    return redirect('admin_dashboard')


def home(request):
    live_datasets = Dataset.objects.filter(status='live')

    total_registered = live_datasets.count()
    active_deployments = live_datasets.values('location').distinct().count()
    mean_quality = live_datasets.aggregate(Avg('quality_score'))['quality_score__avg'] or 0

    domains = Domain.objects.annotate(
        dataset_count=Count('datasets', filter=Q(datasets__status='live'))
    ).order_by('name')

    datasets = live_datasets.select_related('domain', 'researcher').order_by('-created_at')[:20]

    search_query = request.GET.get('q', '').strip()
    domain_slug = request.GET.get('domain', '').strip()
    min_score = request.GET.get('min_score', '').strip()

    if search_query:
        datasets = datasets.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )
    if domain_slug:
        datasets = datasets.filter(domain__slug=domain_slug)
    if min_score:
        try:
            datasets = datasets.filter(quality_score__gte=float(min_score))
        except ValueError:
            pass

    total_downloads = live_datasets.aggregate(total=Sum('download_count'))['total'] or 0
    top_datasets = live_datasets.select_related('domain', 'researcher').order_by('-download_count')[:6]

    context = {
        'total_registered': total_registered,
        'active_deployments': active_deployments,
        'total_downloads': total_downloads,
        'mean_quality': round(mean_quality, 2),
        'domains': domains,
        'datasets': datasets,
        'top_datasets': top_datasets,
        'search_query': search_query,
        'selected_domain': domain_slug,
        'selected_min_score': min_score,
    }
    return render(request, 'index.html', context)


@login_required
def user_dashboard(request):
    user = request.user
    user_datasets = Dataset.objects.filter(researcher=user).select_related('domain')
    download_logs = AuditLog.objects.filter(user=user, action_type='download').select_related('user')
    downloaded_dataset_titles = []
    for log in download_logs:
        title = log.details
        if title and title.startswith('Downloaded: '):
            title = title[len('Downloaded: '):]
        if title:
            downloaded_dataset_titles.append(title)
    downloaded_datasets = Dataset.objects.filter(title__in=downloaded_dataset_titles).select_related('domain', 'researcher')
    user_feedback = Feedback.objects.filter(user=user).order_by('-created_at')[:20]
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        profile = None

    unread_notifications_count = 0
    recent_notifications = []
    if user.is_authenticated:
        try:
            from catalogue.notifications import get_unread_notifications_count, get_recent_notifications
            unread_notifications_count = get_unread_notifications_count(user)
            recent_notifications = get_recent_notifications(user, limit=5)
        except Exception:
            pass

    context = {
        'user_datasets': user_datasets,
        'downloaded_datasets': downloaded_datasets,
        'user_feedback': user_feedback,
        'profile': profile,
        'unread_notifications_count': unread_notifications_count,
        'recent_notifications': recent_notifications,
    }
    return render(request, 'user_dashboard.html', context)


@login_required
def user_account_settings(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)
    section = request.GET.get('section', 'profile')
    success_message = None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'profile_settings':
            form = ProfileSettingsForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile settings saved successfully.')
                return redirect(f'{request.path}?section=profile')
            else:
                messages.error(request, 'Please correct the errors below.')

        elif action == 'account_settings':
            form = AccountSettingsForm(request.POST)
            if form.is_valid():
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.save()
                profile.phone_number = form.cleaned_data.get('phone_number', '')
                profile.save()
                messages.success(request, 'Account settings saved successfully.')
                return redirect(f'{request.path}?section=account')
            else:
                messages.error(request, 'Please correct the errors below.')

        elif action == 'profile_picture':
            form = ProfilePictureForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile picture updated successfully.')
                return redirect(f'{request.path}?section=profile-picture')
            else:
                messages.error(request, 'Please correct the errors below.')
                profile_picture_form = form

        elif action == 'notification_preferences':
            form = NotificationPreferencesForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'Notification preferences saved successfully.')
                return redirect(f'{request.path}?section=notifications')
            else:
                messages.error(request, 'Please correct the errors below.')

        elif action == 'privacy_settings':
            form = PrivacySettingsForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'Privacy settings saved successfully.')
                return redirect(f'{request.path}?section=privacy')
            else:
                messages.error(request, 'Please correct the errors below.')

        elif action == 'appearance_settings':
            form = AppearanceSettingsForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'Appearance preference saved successfully.')
                return redirect(f'{request.path}?section=appearance')
            else:
                messages.error(request, 'Please correct the errors below.')

        elif action == 'language_settings':
            form = LanguageSettingsForm(request.POST, instance=profile)
            if form.is_valid():
                profile = form.save()
                request.session['django_language'] = profile.preferred_language
                from django.utils import translation
                translation.activate(profile.preferred_language)
                messages.success(request, 'Language preference saved successfully.')
                return redirect(f'{request.path}?section=language')
            else:
                messages.error(request, 'Please correct the errors below.')

        elif action == 'timezone_settings':
            form = TimeZoneSettingsForm(request.POST, instance=profile)
            if form.is_valid():
                profile = form.save()
                from django.utils import timezone as django_timezone
                django_timezone.activate(profile.time_zone)
                messages.success(request, 'Time zone preference saved successfully.')
                return redirect(f'{request.path}?section=timezone')
            else:
                messages.error(request, 'Please correct the errors below.')

    # Initialize forms
    profile_form = ProfileSettingsForm(instance=profile)
    account_form = AccountSettingsForm(initial={
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'phone_number': profile.phone_number,
    })
    profile_picture_form = ProfilePictureForm(instance=profile)
    notification_form = NotificationPreferencesForm(instance=profile)
    privacy_form = PrivacySettingsForm(instance=profile)
    appearance_form = AppearanceSettingsForm(instance=profile)
    language_form = LanguageSettingsForm(instance=profile)
    timezone_form = TimeZoneSettingsForm(instance=profile)

    context = {
        'profile': profile,
        'section': section,
        'profile_form': profile_form,
        'account_form': account_form,
        'profile_picture_form': profile_picture_form,
        'notification_form': notification_form,
        'privacy_form': privacy_form,
        'appearance_form': appearance_form,
        'language_form': language_form,
        'timezone_form': timezone_form,
    }
    return render(request, 'user_account_settings.html', context)


@login_required
def detect_timezone(request):
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            timezone_value = data.get('time_zone', '').strip()
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=400)

        if latitude is not None and longitude is not None:
            timezone_value = None
            try:
                import urllib.request
                url = f"https://geocode.xyz/{latitude},{longitude}?geoit=json"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    geo_data = json.loads(resp.read().decode('utf-8'))
                    timezone_value = geo_data.get('timezone')
                    if timezone_value and ('throttled' in timezone_value.lower() or 'error' in timezone_value.lower()):
                        timezone_value = None
            except Exception:
                timezone_value = None

        if not timezone_value:
            timezone_value = 'Africa/Dar_es_Salaam'

        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.time_zone = timezone_value
        profile.time_zone_auto_detected = True
        profile.save()

        from django.utils import timezone as django_timezone
        django_timezone.activate(timezone_value)

        return JsonResponse({'success': True, 'time_zone': timezone_value})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)


@admin_required
def admin_detect_timezone(request):
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            timezone_value = data.get('time_zone', '').strip()
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=400)

        if latitude is not None and longitude is not None:
            timezone_value = None
            try:
                import urllib.request
                url = f"https://geocode.xyz/{latitude},{longitude}?geoit=json"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    geo_data = json.loads(resp.read().decode('utf-8'))
                    timezone_value = geo_data.get('timezone')
                    if timezone_value and ('throttled' in timezone_value.lower() or 'error' in timezone_value.lower()):
                        timezone_value = None
            except Exception:
                timezone_value = None

        if not timezone_value:
            timezone_value = 'Africa/Dar_es_Salaam'

        SystemSetting.objects.update_or_create(
            key='time_zone',
            defaults={'value': timezone_value, 'setting_type': 'text', 'category': 'general'}
        )

        from django.utils import timezone as django_timezone
        django_timezone.activate(timezone_value)

        return JsonResponse({'success': True, 'time_zone': timezone_value})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)


def browse_catalogue(request):
    base_qs = Dataset.objects.select_related('domain', 'researcher')
    if request.user.is_authenticated:
        live_datasets = base_qs.filter(Q(status='live') | Q(researcher=request.user))
    else:
        live_datasets = base_qs.filter(status='live')
    domains = Domain.objects.annotate(
        dataset_count=Count('datasets', filter=Q(datasets__status='live'))
    ).order_by('name')

    q = request.GET.get('q', '').strip()
    domain_slug = request.GET.get('domain', '').strip()
    min_score = request.GET.get('min_score', '').strip()
    if not min_score:
        min_score = '0'
    sort = request.GET.get('sort', 'newest')
    sensor_type = request.GET.get('sensor_type', 'all')
    start_year = request.GET.get('start_year', '').strip()

    if q:
        live_datasets = live_datasets.filter(
            Q(title__icontains=q) | Q(description__icontains=q) | Q(location__icontains=q) | Q(iuc_project_code__icontains=q) | Q(researcher__username__icontains=q) | Q(researcher__first_name__icontains=q) | Q(researcher__last_name__icontains=q)
        )
    if domain_slug:
        live_datasets = live_datasets.filter(domain__slug=domain_slug)
    if sensor_type and sensor_type != 'all':
        live_datasets = live_datasets.filter(sensor_type=sensor_type)
    if min_score:
        try:
            live_datasets = live_datasets.filter(quality_score__gte=float(min_score))
        except ValueError:
            pass
    if start_year:
        try:
            live_datasets = live_datasets.filter(start_date__year__gte=int(start_year))
        except ValueError:
            pass

    if sort == 'oldest':
        live_datasets = live_datasets.order_by('created_at')
    elif sort == 'quality':
        live_datasets = live_datasets.order_by('-quality_score')
    elif sort == 'downloads':
        live_datasets = live_datasets.order_by('-download_count')
    else:
        live_datasets = live_datasets.order_by('-created_at')

    context = {
        'datasets': live_datasets,
        'domains': domains,
        'q': q,
        'selected_domain': domain_slug,
        'selected_min_score': min_score,
        'selected_sort': sort,
        'selected_sensor_type': sensor_type,
        'start_year': start_year,
        'sensor_type_choices': Dataset.SENSOR_TYPE_CHOICES,
    }
    return render(request, 'browse.html', context)


def map_view(request):
    live_datasets = Dataset.objects.filter(status='live').select_related('domain')
    datasets_json = json.dumps([
        {
            'title': ds.title,
            'location': ds.location,
            'quality_score': float(ds.quality_score),
            'domain': ds.domain.name,
        }
        for ds in live_datasets
    ])
    return render(request, 'map.html', {'datasets_json': datasets_json, 'datasets': live_datasets})


def dataset_detail_view(request, dataset_id):
    qs = Dataset.objects.select_related('domain', 'researcher')
    if request.user.is_authenticated:
        dataset = get_object_or_404(qs, Q(id=dataset_id, status='live') | Q(id=dataset_id, researcher=request.user))
    else:
        dataset = get_object_or_404(qs, id=dataset_id, status='live')
    dataset.download_count += 1
    dataset.save(update_fields=['download_count'])

    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action_type='view',
        ip_address=get_client_ip(request),
        endpoint_path=f'/catalogue/{dataset_id}/',
        details=f"Viewed dataset: {dataset.title}"
    )

    context = {'dataset': dataset}
    return render(request, 'dataset_detail.html', context)


def register_dataset(request):
    if not request.user.is_authenticated:
        return redirect('/accounts/google/login/')
    if request.method == 'POST':
        form = DatasetRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            dataset = form.save(commit=False)
            dataset.researcher = request.user
            if not dataset.lead_researcher:
                dataset.lead_researcher = request.user.get_full_name() or request.user.username
            if not dataset.title:
                dataset.title = f'Untitled dataset — {request.user.username} — {timezone.now().strftime("%Y-%m-%d")}'
            if not dataset.description:
                dataset.description = 'No description provided.'
            if not dataset.sensor_type:
                dataset.sensor_type = 'Other'
            if not dataset.iuc_project_code:
                dataset.iuc_project_code = 'N/A'
            if not dataset.output_format:
                dataset.output_format = 'CSV'
            if not dataset.location:
                dataset.location = 'Not specified'
            if not dataset.update_frequency:
                dataset.update_frequency = 'N/A'
            if not dataset.units_of_measurement:
                dataset.units_of_measurement = 'N/A'
            if not dataset.department:
                dataset.department = 'Not specified'
            if not dataset.license:
                dataset.license = 'CC BY 4.0'
            dataset.save()
            messages.success(request, f'"{dataset.title}" was submitted for review. A steward will curate it before publication.')

            try:
                from catalogue.notifications import send_admin_notification_to_all_users
                send_admin_notification_to_all_users(
                    title='New Dataset Submitted',
                    message=f'A new dataset "{dataset.title}" has been submitted by {request.user.get_full_name() or request.user.username} and is pending review.',
                    notification_type='info',
                )
            except Exception:
                pass

            return redirect(f'/feedback/?next={reverse("browse_catalogue")}')
        messages.error(request, 'Some required fields are missing. Please fill in at least the basics, or submit as-is and a steward will help complete it.')
    else:
        form = DatasetRegistrationForm(initial={'lead_researcher': request.user.get_full_name() or request.user.username})
    return render(request, 'catalogue/register_dataset.html', {'form': form})


@login_required
def edit_dataset(request, pk):
    dataset = get_object_or_404(Dataset, pk=pk)
    if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'role', None) == 'Admin' or dataset.researcher == request.user):
        return render(request, '403.html', status=403)
    if request.method == 'POST':
        form = DatasetRegistrationForm(request.POST, request.FILES, instance=dataset)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{dataset.title}" has been updated successfully.')
            return redirect('dataset_detail', dataset_id=dataset.pk)
    else:
        form = DatasetRegistrationForm(instance=dataset)
    return render(request, 'catalogue/register_dataset.html', {'form': form, 'dataset': dataset, 'editing': True})


@admin_required
def governance_dashboard_view(request):
    logs = AuditLog.objects.all().select_related('user')[:100]
    pending_count = Dataset.objects.filter(status='pending').count()
    live_count = Dataset.objects.filter(status='live').count()

    base_date = timezone.now().date()
    date_list = [base_date - timedelta(days=x) for x in range(6, -1, -1)]

    chart_labels = [d.strftime('%b %d') for d in date_list]
    chart_data = []

    for day in date_list:
        daily_downloads = AuditLog.objects.filter(
            action_type='download',
            timestamp__date=day
        ).count()
        chart_data.append(daily_downloads)

    context = {
        'system_logs': logs,
        'pending_count': pending_count,
        'live_count': live_count,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    }
    return render(request, 'atlas/governance.html', context)


@admin_required
def admin_analytics_dashboard(request):
    today = timezone.now().date()
    date_list = [today - timedelta(days=i) for i in range(6, -1, -1)]
    chart_dates = [d.strftime('%b %d') for d in date_list]
    download_trends = [
        AuditLog.objects.filter(action_type='download', timestamp__date=d).count()
        for d in date_list
    ]
    view_trends = [
        AuditLog.objects.filter(action_type='view', timestamp__date=d).count()
        for d in date_list
    ]

    # KPI Metrics (fully dynamic)
    total_datasets = Dataset.objects.filter(status='live').count()

    this_month_start = today.replace(day=1)
    datasets_this_month = Dataset.objects.filter(status='live', created_at__date__gte=this_month_start).count()

    total_downloads = Dataset.objects.filter(status='live').aggregate(total=Sum('download_count'))['total'] or 0
    mean_quality = Dataset.objects.filter(status='live').aggregate(avg_quality=Avg('quality_score'))['avg_quality'] or 0.0
    active_domains = Domain.objects.annotate(count=Count('datasets', filter=Q(datasets__status='live'))).filter(count__gt=0).count()

    total_users = User.objects.count()
    live_datasets_count = total_datasets
    pending_count = Dataset.objects.filter(status='pending').count()
    draft_count = Dataset.objects.filter(status='draft').count()

    avg_downloads = Dataset.objects.filter(status='live').aggregate(
        avg=Avg('download_count')
    )['avg'] or 0

    # 12-month growth chart
    twelve_months = [today - timedelta(days=30 * i) for i in range(11, -1, -1)]
    month_labels = [d.strftime('%b') for d in twelve_months]
    monthly_registrations = []
    for m in twelve_months:
        month_start = m.replace(day=1)
        if m.month == 12:
            month_end = m.replace(year=m.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = m.replace(month=m.month + 1, day=1) - timedelta(days=1)
        monthly_registrations.append(
            Dataset.objects.filter(created_at__date__gte=month_start, created_at__date__lte=month_end).count()
        )
    cumulative_growth = []
    running = 0
    for val in monthly_registrations:
        running += val
        cumulative_growth.append(running)

    # Quality buckets
    quality_buckets = [
        Dataset.objects.filter(status='live', quality_score__gte=4.5).count(),
        Dataset.objects.filter(status='live', quality_score__gte=4.0, quality_score__lt=4.5).count(),
        Dataset.objects.filter(status='live', quality_score__gte=3.5, quality_score__lt=4.0).count(),
        Dataset.objects.filter(status='live', quality_score__gte=3.0, quality_score__lt=3.5).count(),
        Dataset.objects.filter(status='live', quality_score__lt=3.0).count(),
    ]

    # Domain data for charts
    domain_order = ['Transport', 'Housing', 'Heritage', 'Energy', 'Water', 'Air Quality', 'Agriculture', 'Health']
    domain_labels = domain_order
    domain_counts = []
    download_counts = []
    for name in domain_order:
        dom = Domain.objects.filter(name=name).first()
        if dom:
            domain_counts.append(Dataset.objects.filter(domain=dom, status='live').count())
            total = Dataset.objects.filter(domain=dom, status='live').aggregate(total=Sum('download_count'))['total'] or 0
            download_counts.append(total)
        else:
            domain_counts.append(0)
            download_counts.append(0)

    domain_colors = [
        'rgba(77, 119, 255, 0.75)',
        'rgba(138, 43, 226, 0.75)',
        'rgba(180, 160, 255, 0.75)',
        'rgba(0, 255, 157, 0.75)',
        'rgba(255, 193, 7, 0.75)',
        'rgba(0, 188, 212, 0.75)',
        'rgba(150, 160, 40, 0.75)',
        'rgba(233, 30, 99, 0.75)',
    ]

    download_labels = domain_order
    download_colors = domain_colors

    top_datasets = Dataset.objects.filter(status='live').select_related('domain').order_by('-download_count')[:6]

    top_researchers = User.objects.annotate(
        dataset_count=Count('datasets', filter=Q(datasets__status='live'))
    ).filter(dataset_count__gt=0).order_by('-dataset_count')[:6]

    status_counts = [
        draft_count,
        pending_count,
        live_datasets_count,
    ]
    status_labels = json.dumps(['Draft', 'Pending', 'Live'])
    status_colors = json.dumps([
        'rgba(95, 95, 95, 0.75)',
        'rgba(255, 193, 7, 0.75)',
        'rgba(0, 255, 157, 0.75)',
    ])

    system_logs = AuditLog.objects.all()[:100]
    domains_count = active_domains

    total_feedback = Feedback.objects.count()
    avg_rating = Feedback.objects.aggregate(avg=Avg('rating'))['avg'] or 0
    recent_feedback = Feedback.objects.select_related('user').order_by('-created_at')[:10]
    feedback_categories = dict(Feedback.CATEGORY_CHOICES)
    category_counts = {
        cat: Feedback.objects.filter(category=cat).count()
        for cat, _ in Feedback.CATEGORY_CHOICES
    }

    context = {
        'system_logs': system_logs,
        'chart_dates': json.dumps(chart_dates),
        'download_trends': json.dumps(download_trends),
        'view_trends': json.dumps(view_trends),
        'month_labels': json.dumps(month_labels),
        'cumulative_growth': json.dumps(cumulative_growth),
        'quality_buckets': json.dumps(quality_buckets),
        'domain_labels': json.dumps(domain_labels),
        'domain_counts': json.dumps(domain_counts),
        'domain_colors': json.dumps(domain_colors),
        'download_labels': json.dumps(download_labels),
        'download_counts': json.dumps(download_counts),
        'download_colors': json.dumps(domain_colors),
        'status_counts': json.dumps(status_counts),
        'status_labels': status_labels,
        'status_colors': status_colors,
        'top_datasets': top_datasets,
        'top_researchers': top_researchers,
        'total_datasets': total_datasets,
        'live_datasets': live_datasets_count,
        'draft_count': draft_count,
        'pending_count': pending_count,
        'total_downloads': total_downloads,
        'total_users': total_users,
        'mean_quality': round(mean_quality, 2),
        'domains_count': domains_count,
        'avg_downloads': round(avg_downloads, 1),
        'datasets_this_month': datasets_this_month,
        'active_domains': active_domains,
        'domain_data': list(Domain.objects.annotate(
            dataset_count=Count('datasets', filter=Q(datasets__status='live')),
            download_sum=Sum('datasets__download_count', filter=Q(datasets__status='live'))
        ).values('name', 'dataset_count', 'download_sum')),
        'total_feedback': total_feedback,
        'avg_rating': round(avg_rating, 1),
        'recent_feedback': recent_feedback,
        'feedback_categories': feedback_categories,
        'category_counts': category_counts,
    }
    return render(request, 'analytics.html', context)


@admin_required
def admin_profile_view(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)
    saved = False
    error = None

    if request.method == 'POST':
        form = AdminProfileForm(request.POST)
        picture_form = ProfileSettingsForm(request.POST, request.FILES, instance=profile)
        if 'update_picture' in request.POST:
            if picture_form.is_valid():
                picture_form.save()
                saved = True
                messages.success(request, 'Profile picture updated successfully.')
            else:
                error = 'Please correct the errors below.'
        elif form.is_valid():
            if not user.check_password(form.cleaned_data['current_password']):
                error = 'Current password is incorrect.'
            else:
                user.username = form.cleaned_data['username']
                new_password = form.cleaned_data.get('new_password', '').strip()
                if new_password:
                    user.set_password(new_password)
                user.save()
                saved = True
                messages.success(request, 'Profile updated successfully.')
    else:
        form = AdminProfileForm(initial={'username': user.username})
        picture_form = ProfileSettingsForm(instance=profile)

    context = {
        'form': form,
        'picture_form': picture_form,
        'saved': saved,
        'error': error,
        'profile': profile,
    }
    return render(request, 'admin_profile.html', context)


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            from django.contrib.auth import login
            login(request, user)
            messages.success(request, f'Welcome, {user.username}! Your account has been created.')
            return redirect(f'/feedback/?next={reverse("home")}')
    else:
        form = SignupForm()
    return render(request, 'registration/signup.html', {'form': form})


def role_based_redirect(request):
    user = request.user
    if not user.is_authenticated:
        return redirect('login')
    if user.is_staff or user.is_superuser or getattr(user, 'role', None) == 'Admin':
        return redirect('admin_dashboard')
    return redirect('user_dashboard')


def governance_policy_view(request):
    return render(request, 'governance_policy.html')


def dataset_download(request, pk):
    qs = Dataset.objects.select_related('researcher')
    if request.user.is_authenticated:
        dataset = get_object_or_404(qs, Q(pk=pk, status='live') | Q(pk=pk, researcher=request.user))
    else:
        dataset = get_object_or_404(qs, pk=pk, status='live')
    dataset.download_count += 1
    dataset.save(update_fields=['download_count'])

    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action_type='download',
        ip_address=get_client_ip(request),
        endpoint_path=f'/dataset/{pk}/download/',
        details=f"Downloaded: {dataset.title}"
    )

    if dataset.data_file:
        return redirect(dataset.data_file.url)
    if dataset.download_link:
        return redirect(dataset.download_link)
    messages.warning(request, 'No downloadable file or link is available for this dataset yet.')
    return redirect('browse_catalogue')


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


def feedback_view(request):
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = Feedback(
                user=request.user if request.user.is_authenticated else None,
                rating=form.cleaned_data['rating'],
                category=form.cleaned_data['category'],
                comment=form.cleaned_data.get('comment', ''),
            )
            feedback.save()
            messages.success(request, 'Thank you for your feedback! Your input helps us improve the portal.')

            try:
                from catalogue.notifications import send_admin_notification_to_all_users
                send_admin_notification_to_all_users(
                    title='New Feedback Submitted',
                    message=f'New feedback has been submitted by {request.user.get_full_name() or request.user.username if request.user.is_authenticated else "Anonymous"}.',
                    notification_type='info',
                )
            except Exception:
                pass

            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
    else:
        initial = {}
        if request.user.is_authenticated:
            initial['comment'] = ''
        form = FeedbackForm(initial=initial)
    return render(request, 'feedback.html', {'form': form})


@admin_required
def admin_feedback_view(request):
    feedbacks = Feedback.objects.all()

    search_query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if search_query:
        feedbacks = feedbacks.filter(
            Q(comment__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    if category_filter:
        feedbacks = feedbacks.filter(category=category_filter)
    if status_filter:
        feedbacks = feedbacks.filter(status=status_filter)

    feedbacks = feedbacks.select_related('user').order_by('-created_at')

    if request.method == 'POST':
        feedback_id = request.POST.get('feedback_id')
        new_status = request.POST.get('status')
        admin_notes = request.POST.get('admin_notes', '')
        if feedback_id and new_status:
            feedback = get_object_or_404(Feedback, pk=feedback_id)
            feedback.status = new_status
            feedback.admin_notes = admin_notes
            feedback.save()
            messages.success(request, f'Feedback #{feedback_id} updated successfully.')
            try:
                from catalogue.notifications import create_notification
                create_notification(
                    user=feedback.user,
                    title='Feedback Updated',
                    message=f'Your feedback has been updated to status: {new_status}.',
                    notification_type='info',
                    send_email=True,
                )
            except Exception:
                pass
        return redirect('admin_feedback')

    context = {
        'feedbacks': feedbacks,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'category_choices': Feedback.CATEGORY_CHOICES,
        'status_choices': Feedback.STATUS_CHOICES,
    }
    return render(request, 'admin_feedback.html', context)


@admin_required
def export_feedback_csv(request):
    feedbacks = Feedback.objects.all().select_related('user').order_by('-created_at')

    search_query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if search_query:
        feedbacks = feedbacks.filter(
            Q(comment__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    if category_filter:
        feedbacks = feedbacks.filter(category=category_filter)
    if status_filter:
        feedbacks = feedbacks.filter(status=status_filter)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="feedback_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'User', 'Email', 'Rating', 'Category', 'Comment', 'Status', 'Admin Notes', 'Submitted At', 'Updated At'])

    for f in feedbacks:
        writer.writerow([
            f.id,
            f.user.get_full_name() or f.user.username if f.user else 'Anonymous',
            f.user.email if f.user else 'N/A',
            f.rating,
            f.get_category_display(),
            f.comment,
            f.get_status_display(),
            f.admin_notes,
            f.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            f.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response


@admin_required
def admin_user_management(request):
    users = User.objects.all().select_related('profile').order_by('-is_superuser', '-is_staff', 'username')
    search_query = request.GET.get('q', '').strip()
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    context = {
        'users': users,
        'search_query': search_query,
    }
    return render(request, 'admin_user_management.html', context)


@admin_required
def admin_dataset_management(request):
    datasets = Dataset.objects.all().select_related('domain', 'researcher').order_by('-created_at')
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        datasets = datasets.filter(status=status_filter)
    if request.method == 'POST':
        dataset_id = request.POST.get('dataset_id')
        action = request.POST.get('action')
        if dataset_id and action:
            dataset = get_object_or_404(Dataset, pk=dataset_id)
            if action == 'approve':
                dataset.status = 'live'
                dataset.save()
                AuditLog.objects.create(
                    user=request.user,
                    action_type='status_change',
                    ip_address=get_client_ip(request),
                    endpoint_path=f'/admin/datasets/{dataset_id}/',
                    details=f'Approved dataset: {dataset.title}'
                )
                messages.success(request, f'Dataset "{dataset.title}" has been approved and published.')
                try:
                    from catalogue.notifications import create_notification
                    create_notification(
                        user=dataset.researcher,
                        title='Dataset Approved',
                        message=f'Your dataset "{dataset.title}" has been approved and is now live.',
                        notification_type='success',
                        send_email=True,
                    )
                except Exception:
                    pass
            elif action == 'reject':
                dataset.status = 'draft'
                dataset.save()
                AuditLog.objects.create(
                    user=request.user,
                    action_type='status_change',
                    ip_address=get_client_ip(request),
                    endpoint_path=f'/admin/datasets/{dataset_id}/',
                    details=f'Rejected dataset: {dataset.title}'
                )
                messages.success(request, f'Dataset "{dataset.title}" has been rejected and reverted to draft.')
                try:
                    from catalogue.notifications import create_notification
                    create_notification(
                        user=dataset.researcher,
                        title='Dataset Rejected',
                        message=f'Your dataset "{dataset.title}" has been rejected and reverted to draft. Please review and resubmit.',
                        notification_type='warning',
                        send_email=True,
                    )
                except Exception:
                    pass
            elif action == 'delete':
                dataset_title = dataset.title
                dataset.delete()
                AuditLog.objects.create(
                    user=request.user,
                    action_type='status_change',
                    ip_address=get_client_ip(request),
                    endpoint_path=f'/admin/datasets/{dataset_id}/',
                    details=f'Deleted dataset: {dataset_title}'
                )
                messages.success(request, f'Dataset "{dataset_title}" has been deleted.')
        return redirect('admin_dataset_management')
    context = {
        'datasets': datasets,
        'status_filter': status_filter,
        'status_choices': Dataset.STATUS_CHOICES,
    }
    return render(request, 'admin_dataset_management.html', context)


@admin_required
def admin_downloads(request):
    logs = AuditLog.objects.filter(action_type='download').select_related('user').order_by('-timestamp')
    search_query = request.GET.get('q', '').strip()
    if search_query:
        logs = logs.filter(
            Q(user__username__icontains=search_query) |
            Q(details__icontains=search_query) |
            Q(endpoint_path__icontains=search_query)
        )
    context = {
        'logs': logs,
        'search_query': search_query,
    }
    return render(request, 'admin_downloads.html', context)


@admin_required
def admin_category_management(request):
    domains = Domain.objects.all().order_by('name')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            slug = name.lower().replace(' ', '-').replace('/', '-')
            Domain.objects.get_or_create(name=name, slug=slug)
            messages.success(request, f'Category "{name}" has been added.')
            return redirect('admin_category_management')
    context = {
        'domains': domains,
    }
    return render(request, 'admin_category_management.html', context)


@admin_required
def admin_settings(request):
    return redirect('admin_settings_general')


@admin_required
def admin_settings_general(request):
    setting, _ = SystemSetting.objects.get_or_create(key='portal_name', defaults={'value': 'ARU IoT Dataset Catalogue', 'category': 'general', 'setting_type': 'text', 'is_required': True})
    setting, _ = SystemSetting.objects.get_or_create(key='institution_name', defaults={'value': 'ARU', 'category': 'general', 'setting_type': 'text'})
    setting, _ = SystemSetting.objects.get_or_create(key='contact_email', defaults={'value': 'contact@aru.ac.ug', 'category': 'general', 'setting_type': 'email', 'is_required': True})
    setting, _ = SystemSetting.objects.get_or_create(key='contact_phone', defaults={'value': '', 'category': 'general', 'setting_type': 'text'})
    setting, _ = SystemSetting.objects.get_or_create(key='time_zone', defaults={'value': 'Africa/Kampala', 'category': 'general', 'setting_type': 'text', 'is_required': True})
    setting, _ = SystemSetting.objects.get_or_create(key='default_language', defaults={'value': 'en', 'category': 'general', 'setting_type': 'text', 'is_required': True})

    settings_qs = SystemSetting.objects.filter(category='general')
    settings_map = {s.key: s.value for s in settings_qs}

    if request.method == 'POST':
        form = GeneralSettingsForm(request.POST, request.FILES)
        if form.is_valid():
            for key, value in form.cleaned_data.items():
                setting_type = 'text'
                if isinstance(value, bool):
                    setting_type = 'boolean'
                    value = 'true' if value else 'false'
                elif key in ['contact_email']:
                    setting_type = 'email'
                SystemSetting.objects.update_or_create(
                    key=key,
                    defaults={'value': str(value), 'setting_type': setting_type, 'category': 'general'}
                )
            messages.success(request, 'General settings saved successfully.')
            return redirect('admin_settings_general')
    else:
        initial_data = {
            'portal_name': settings_map.get('portal_name', ''),
            'institution_name': settings_map.get('institution_name', ''),
            'contact_email': settings_map.get('contact_email', ''),
            'contact_phone': settings_map.get('contact_phone', ''),
            'time_zone': settings_map.get('time_zone', 'Africa/Kampala'),
            'default_language': settings_map.get('default_language', 'en'),
        }
        form = GeneralSettingsForm(initial=initial_data)

    return render(request, 'settings/general.html', {'form': form, 'settings_map': settings_map})


@admin_required
def admin_settings_dataset(request):
    settings_qs = SystemSetting.objects.filter(category='dataset')
    settings_map = {s.key: s.value for s in settings_qs}

    if request.method == 'POST':
        form = DatasetSettingsForm(request.POST)
        if form.is_valid():
            for key, value in form.cleaned_data.items():
                setting_type = 'text'
                if isinstance(value, bool):
                    setting_type = 'boolean'
                    value = 'true' if value else 'false'
                elif isinstance(value, list):
                    setting_type = 'choice'
                    value = ','.join(value)
                elif key in ['max_upload_size_mb', 'default_quality_rating']:
                    setting_type = 'number'
                SystemSetting.objects.update_or_create(
                    key=key,
                    defaults={'value': str(value), 'setting_type': setting_type, 'category': 'dataset'}
                )
            messages.success(request, 'Dataset settings saved successfully.')
            return redirect('admin_settings_dataset')
    else:
        initial_data = {
            'allowed_file_formats': settings_map.get('allowed_file_formats', 'CSV,JSON,XLSX').split(','),
            'max_upload_size_mb': int(settings_map.get('max_upload_size_mb', 100)),
            'default_visibility': settings_map.get('default_visibility', 'public'),
            'default_quality_rating': float(settings_map.get('default_quality_rating', 0)),
            'enable_versioning': settings_map.get('enable_versioning', 'false') == 'true',
            'require_metadata_before_upload': settings_map.get('require_metadata_before_upload', 'false') == 'true',
        }
        form = DatasetSettingsForm(initial=initial_data)

    return render(request, 'settings/dataset.html', {'form': form, 'settings_map': settings_map})


@admin_required
def admin_settings_categories(request):
    categories = DatasetCategory.objects.all().order_by('name')
    search_query = request.GET.get('q', '').strip()
    if search_query:
        categories = categories.filter(name__icontains=search_query)

    if request.method == 'POST':
        form = DatasetCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category added successfully.')
            return redirect('admin_settings_categories')
    else:
        form = DatasetCategoryForm()

    return render(request, 'settings/categories.html', {
        'categories': categories,
        'form': form,
        'search_query': search_query,
    })


@admin_required
def admin_settings_categories_edit(request, pk):
    category = get_object_or_404(DatasetCategory, pk=pk)
    if request.method == 'POST':
        form = DatasetCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated successfully.')
            return redirect('admin_settings_categories')
    else:
        form = DatasetCategoryForm(instance=category)

    return render(request, 'settings/categories.html', {
        'categories': DatasetCategory.objects.all().order_by('name'),
        'form': form,
        'edit_category': category,
        'search_query': request.GET.get('q', '').strip(),
    })


@admin_required
def admin_settings_categories_delete(request, pk):
    category = get_object_or_404(DatasetCategory, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted successfully.')
    return redirect('admin_settings_categories')


@admin_required
def admin_settings_sensor_types(request):
    sensor_types = SensorType.objects.all().order_by('name')

    if request.method == 'POST':
        form = SensorTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sensor type added successfully.')
            return redirect('admin_settings_sensor_types')
    else:
        form = SensorTypeForm()

    return render(request, 'settings/sensor_types.html', {
        'sensor_types': sensor_types,
        'form': form,
    })


@admin_required
def admin_settings_sensor_types_edit(request, pk):
    sensor_type = get_object_or_404(SensorType, pk=pk)
    if request.method == 'POST':
        form = SensorTypeForm(request.POST, instance=sensor_type)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sensor type updated successfully.')
            return redirect('admin_settings_sensor_types')
    else:
        form = SensorTypeForm(instance=sensor_type)

    return render(request, 'settings/sensor_types.html', {
        'sensor_types': SensorType.objects.all().order_by('name'),
        'form': form,
        'edit_sensor_type': sensor_type,
    })


@admin_required
def admin_settings_sensor_types_delete(request, pk):
    sensor_type = get_object_or_404(SensorType, pk=pk)
    if request.method == 'POST':
        sensor_type.delete()
        messages.success(request, 'Sensor type deleted successfully.')
    return redirect('admin_settings_sensor_types')


@admin_required
def admin_settings_sensor_types_toggle(request, pk):
    sensor_type = get_object_or_404(SensorType, pk=pk)
    sensor_type.is_active = not sensor_type.is_active
    sensor_type.save()
    status = 'activated' if sensor_type.is_active else 'deactivated'
    messages.success(request, f'Sensor type {status} successfully.')
    return redirect('admin_settings_sensor_types')


@admin_required
def admin_settings_domains(request):
    domains = Domain.objects.all().order_by('name')

    if request.method == 'POST':
        form = ResearchDomainForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Research domain added successfully.')
            return redirect('admin_settings_domains')
    else:
        form = ResearchDomainForm()

    return render(request, 'settings/domains.html', {
        'domains': domains,
        'form': form,
    })


@admin_required
def admin_settings_domains_edit(request, pk):
    domain = get_object_or_404(Domain, pk=pk)
    if request.method == 'POST':
        form = ResearchDomainForm(request.POST, instance=domain)
        if form.is_valid():
            form.save()
            messages.success(request, 'Research domain updated successfully.')
            return redirect('admin_settings_domains')
    else:
        form = ResearchDomainForm(instance=domain)

    return render(request, 'settings/domains.html', {
        'domains': Domain.objects.all().order_by('name'),
        'form': form,
        'edit_domain': domain,
    })


@admin_required
def admin_settings_domains_delete(request, pk):
    domain = get_object_or_404(Domain, pk=pk)
    if request.method == 'POST':
        domain.delete()
        messages.success(request, 'Research domain deleted successfully.')
    return redirect('admin_settings_domains')


@admin_required
def admin_settings_domains_toggle(request, pk):
    domain = get_object_or_404(Domain, pk=pk)
    domain.is_active = not domain.is_active
    domain.save()
    status = 'activated' if domain.is_active else 'deactivated'
    messages.success(request, f'Research domain {status} successfully.')
    return redirect('admin_settings_domains')


@admin_required
def admin_settings_users(request):
    settings_qs = SystemSetting.objects.filter(category='users')
    settings_map = {s.key: s.value for s in settings_qs}

    if request.method == 'POST':
        form = UserSettingsForm(request.POST)
        if form.is_valid():
            for key, value in form.cleaned_data.items():
                setting_type = 'text'
                if isinstance(value, bool):
                    setting_type = 'boolean'
                    value = 'true' if value else 'false'
                elif isinstance(value, int):
                    setting_type = 'number'
                SystemSetting.objects.update_or_create(
                    key=key,
                    defaults={'value': str(value), 'setting_type': setting_type, 'category': 'users'}
                )
            messages.success(request, 'User settings saved successfully.')
            return redirect('admin_settings_users')
    else:
        initial_data = {
            'enable_registration': settings_map.get('enable_registration', 'true') == 'true',
            'require_admin_approval': settings_map.get('require_admin_approval', 'false') == 'true',
            'enable_email_verification': settings_map.get('enable_email_verification', 'false') == 'true',
            'default_user_role': settings_map.get('default_user_role', 'researcher'),
            'min_password_length': int(settings_map.get('min_password_length', 8)),
            'max_login_attempts': int(settings_map.get('max_login_attempts', 5)),
            'session_timeout_minutes': int(settings_map.get('session_timeout_minutes', 60)),
            'enable_email_notifications': settings_map.get('enable_email_notifications', 'false') == 'true',
        }
        form = UserSettingsForm(initial=initial_data)

    return render(request, 'settings/users.html', {'form': form, 'settings_map': settings_map})


@admin_required
def admin_settings_security(request):
    settings_qs = SystemSetting.objects.filter(category='security')
    settings_map = {s.key: s.value for s in settings_qs}

    if request.method == 'POST':
        form = SecuritySettingsForm(request.POST)
        if form.is_valid():
            for key, value in form.cleaned_data.items():
                setting_type = 'text'
                if isinstance(value, bool):
                    setting_type = 'boolean'
                    value = 'true' if value else 'false'
                elif isinstance(value, int):
                    setting_type = 'number'
                SystemSetting.objects.update_or_create(
                    key=key,
                    defaults={'value': str(value), 'setting_type': setting_type, 'category': 'security'}
                )
            messages.success(request, 'Security settings saved successfully.')
            return redirect('admin_settings_security')
    else:
        initial_data = {
            'password_complexity_rules': settings_map.get('password_complexity_rules', ''),
            'enable_two_factor_auth': settings_map.get('enable_two_factor_auth', 'false') == 'true',
            'https_enforcement': settings_map.get('https_enforcement', 'false') == 'true',
            'login_audit_logging': settings_map.get('login_audit_logging', 'false') == 'true',
            'failed_login_lockout_duration': int(settings_map.get('failed_login_lockout_duration', 30)),
        }
        form = SecuritySettingsForm(initial=initial_data)

    return render(request, 'settings/security.html', {'form': form, 'settings_map': settings_map})


@admin_required
def admin_settings_backups(request):
    backups = Backup.objects.all().order_by('-created_at')[:50]

    if request.method == 'POST':
        form = BackupForm(request.POST)
        if form.is_valid():
            backup = Backup.objects.create(
                name=form.cleaned_data['name'],
                backup_type=form.cleaned_data['backup_type'],
                created_by=request.user,
                notes=form.cleaned_data['notes'],
                status='pending'
            )
            messages.success(request, f'Backup "{backup.name}" created successfully.')
            return redirect('admin_settings_backups')
    else:
        form = BackupForm()

    return render(request, 'settings/backups.html', {
        'backups': backups,
        'form': form,
    })


@admin_required
def admin_settings_logs(request):
    log_type = request.GET.get('type', 'all')
    level = request.GET.get('level', 'all')
    logs = SystemLog.objects.all()

    if log_type != 'all':
        logs = logs.filter(log_type=log_type)
    if level != 'all':
        logs = logs.filter(level=level)

    logs = logs.order_by('-timestamp')[:200]

    return render(request, 'settings/logs.html', {
        'logs': logs,
        'log_type': log_type,
        'level': level,
        'log_types': SystemLog.LOG_TYPE_CHOICES,
        'log_levels': SystemLog.LOG_LEVEL_CHOICES,
    })

@admin_required
def admin_reports(request):
    report_type = request.GET.get('type', 'datasets')
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    export_format = request.GET.get('export', '').strip()

    datasets_qs = Dataset.objects.all().select_related('domain', 'researcher')
    users_qs = User.objects.all()
    feedbacks_qs = Feedback.objects.all().select_related('user')
    downloads_qs = AuditLog.objects.filter(action_type='download').select_related('user')

    if start_date:
        datasets_qs = datasets_qs.filter(created_at__date__gte=start_date)
        feedbacks_qs = feedbacks_qs.filter(created_at__date__gte=start_date)
        downloads_qs = downloads_qs.filter(timestamp__date__gte=start_date)
    if end_date:
        datasets_qs = datasets_qs.filter(created_at__date__lte=end_date)
        feedbacks_qs = feedbacks_qs.filter(created_at__date__lte=end_date)
        downloads_qs = downloads_qs.filter(timestamp__date__lte=end_date)

    context = {
        'report_type': report_type,
        'start_date': start_date,
        'end_date': end_date,
        'total_datasets': datasets_qs.count(),
        'total_users': users_qs.count(),
        'total_downloads': downloads_qs.count(),
        'total_feedback': feedbacks_qs.count(),
        'datasets': datasets_qs[:100],
        'users': users_qs[:100],
        'feedbacks': feedbacks_qs[:100],
        'downloads': downloads_qs[:100],
    }

    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
        writer = csv.writer(response)
        if report_type == 'datasets':
            writer.writerow(['ID', 'Title', 'Domain', 'Researcher', 'Status', 'Quality Score', 'Downloads', 'Created At'])
            for ds in datasets_qs:
                writer.writerow([ds.id, ds.title, ds.domain.name, ds.researcher.username, ds.status, ds.quality_score, ds.download_count, ds.created_at.strftime('%Y-%m-%d %H:%M:%S')])
        elif report_type == 'users':
            writer.writerow(['ID', 'Username', 'Email', 'First Name', 'Last Name', 'Is Staff', 'Is Superuser', 'Date Joined'])
            for u in users_qs:
                writer.writerow([u.id, u.username, u.email, u.first_name, u.last_name, u.is_staff, u.is_superuser, u.date_joined.strftime('%Y-%m-%d %H:%M:%S')])
        elif report_type == 'downloads':
            writer.writerow(['ID', 'User', 'Action', 'Details', 'Endpoint', 'IP Address', 'Timestamp'])
            for log in downloads_qs:
                writer.writerow([log.id, log.user.username if log.user else 'Anonymous', log.get_action_type_display(), log.details, log.endpoint_path, log.ip_address or 'N/A', log.timestamp.strftime('%Y-%m-%d %H:%M:%S')])
        elif report_type == 'feedback':
            writer.writerow(['ID', 'User', 'Rating', 'Category', 'Comment', 'Status', 'Submitted At'])
            for f in feedbacks_qs:
                writer.writerow([f.id, f.user.username if f.user else 'Anonymous', f.rating, f.get_category_display(), f.comment, f.get_status_display(), f.created_at.strftime('%Y-%m-%d %H:%M:%S')])
        return response

    return render(request, 'admin_reports.html', context)



