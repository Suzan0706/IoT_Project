from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Count, Avg, Sum, F, Case, When, IntegerField
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from .models import Dataset, Domain, AuditLog
from .forms import DatasetForm, DatasetRegistrationForm, AdminProfileForm, LoginForm, SignupForm
import json


def dashboard_view(request):
    live_datasets = Dataset.objects.filter(status='live').select_related('domain', 'researcher')
    total_registered = live_datasets.count()
    active_deployments = live_datasets.values('location').distinct().count()
    mean_quality = live_datasets.aggregate(Avg('quality_score'))['quality_score__avg'] or 0

    domains = Domain.objects.annotate(
        dataset_count=Count('datasets', filter=Q(datasets__status='live'))
    ).order_by('name')

    total_downloads = live_datasets.aggregate(total=Sum('download_count'))['total'] or 0
    top_datasets = live_datasets.select_related('domain').order_by('-download_count')[:6]
    newly_registered = live_datasets.order_by('-created_at')[:3]

    context = {
        'total_registered': total_registered,
        'active_deployments': active_deployments,
        'total_downloads': total_downloads,
        'mean_quality': round(mean_quality, 2),
        'domains': domains,
        'datasets': live_datasets,
        'top_datasets': top_datasets,
        'newly_registered': newly_registered,
        'domains_count': domains.count(),
        'datasets_this_month': live_datasets.filter(created_at__date__gte=timezone.now().date().replace(day=1)).count(),
    }
    return render(request, 'pages/atlas.html', context)


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


def analytics_view(request):
    total_datasets = Dataset.objects.filter(status='live').count()
    total_downloads = Dataset.objects.filter(status='live').aggregate(total=Sum('download_count'))['total'] or 0
    mean_quality = Dataset.objects.filter(status='live').aggregate(avg_quality=Avg('quality_score'))['avg_quality'] or 0.0
    active_domains = Domain.objects.annotate(count=Count('datasets')).filter(count__gt=0).count()

    top_datasets = Dataset.objects.filter(status='live').select_related('domain').order_by('-download_count')[:6]

    # 12-month growth chart
    today = timezone.now().date()
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

    top_researchers = User.objects.annotate(
        dataset_count=Count('datasets', filter=Q(datasets__status='live'))
    ).filter(dataset_count__gt=0).order_by('-dataset_count')[:6]

    status_counts = [
        Dataset.objects.filter(status='draft').count(),
        Dataset.objects.filter(status='pending').count(),
        total_datasets,
    ]

    context = {
        'system_logs': AuditLog.objects.all()[:100],
        'chart_labels': json.dumps(domain_labels),
        'chart_datasets': json.dumps(domain_counts),
        'chart_downloads': json.dumps(download_counts),
        'chart_dates': json.dumps(month_labels),
        'download_trends': json.dumps([0,0,0,0,0,0,0]),
        'view_trends': json.dumps([0,0,0,0,0,0,0]),
        'cumulative_growth': json.dumps(cumulative_growth),
        'quality_buckets': json.dumps(quality_buckets),
        'domain_labels': json.dumps(domain_labels),
        'domain_counts': json.dumps(domain_counts),
        'domain_colors': json.dumps(domain_colors),
        'download_labels': json.dumps(download_labels),
        'download_counts': json.dumps(download_counts),
        'download_colors': json.dumps(domain_colors),
        'status_counts': json.dumps(status_counts),
        'status_labels': json.dumps(['Draft', 'Pending', 'Live']),
        'status_colors': json.dumps([
            'rgba(95, 95, 95, 0.75)',
            'rgba(255, 193, 7, 0.75)',
            'rgba(0, 255, 157, 0.75)',
        ]),
        'top_datasets': top_datasets,
        'top_researchers': top_researchers,
        'total_datasets': total_datasets,
        'live_datasets': total_datasets,
        'draft_count': status_counts[0],
        'pending_count': status_counts[1],
        'total_downloads': total_downloads,
        'total_users': User.objects.count(),
        'mean_quality': round(mean_quality, 2),
        'domains_count': active_domains,
        'avg_downloads': round(total_downloads / total_datasets, 1) if total_datasets else 0,
        'datasets_this_month': Dataset.objects.filter(status='live', created_at__date__gte=today.replace(day=1)).count(),
        'active_domains': active_domains,
    }
    return render(request, 'catalogue/analytics.html', context)


def browse_catalogue(request):
    live_datasets = Dataset.objects.filter(status='live').select_related('domain', 'researcher')
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
    dataset = get_object_or_404(Dataset, id=dataset_id, status='live')
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


@login_required
def register_dataset(request):
    if request.method == 'POST':
        form = DatasetRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            dataset = form.save(commit=False)
            if hasattr(dataset, 'researcher'):
                dataset.researcher = request.user
            dataset.save()
            return redirect('browse_catalogue')
    else:
        form = DatasetRegistrationForm()
        
    return render(request, 'catalogue/register_dataset.html', {'form': form})


def is_steward(user):
    return user.is_staff or user.groups.filter(name='Catalog Stewards').exists()


@user_passes_test(is_steward)
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
    }
    return render(request, 'analytics.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_profile_view(request):
    user = request.user
    saved = False
    error = None

    if request.method == 'POST':
        form = AdminProfileForm(request.POST)
        if form.is_valid():
            if not user.check_password(form.cleaned_data['current_password']):
                error = 'Current password is incorrect.'
            else:
                user.username = form.cleaned_data['username']
                new_password = form.cleaned_data.get('new_password', '').strip()
                if new_password:
                    user.set_password(new_password)
                user.save()
                saved = True
    else:
        form = AdminProfileForm(initial={'username': user.username})

    context = {
        'form': form,
        'saved': saved,
        'error': error,
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
            return redirect('home')
    else:
        form = SignupForm()
    return render(request, 'registration/signup.html', {'form': form})


def governance_policy_view(request):
    return render(request, 'governance_policy.html')


def dataset_download(request, pk):
    dataset = get_object_or_404(Dataset, pk=pk, status='live')
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
    messages.warning(request, 'No data file attached to this dataset.')
    return redirect('home')


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')
