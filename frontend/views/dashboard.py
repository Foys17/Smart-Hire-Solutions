from django.shortcuts import render, redirect
from django.db.models import Sum, Count, F
from jobs.models import Job
from candidates.models import Application

def home(request):
    #Redirect Clients immediately 
    if request.user.is_authenticated and request.user.role == 'Client':
        return redirect('web_test:client_dashboard')
    # 1. Define who gets to see the Dashboard
    is_dashboard_user = request.user.is_authenticated and (
        request.user.role in ['HR', 'Admin'] or request.user.is_superuser
    )

    # 2. If NOT a dashboard user (Guest or Candidate), show Landing Page
    if not is_dashboard_user:
        return render(request, 'home.html')

    # 3. If Dashboard User, Calculate Stats
    active_jobs_count = Job.objects.filter(status='OPEN').count()
    total_candidates = Application.objects.count()
    
    # Calculate Revenue
    revenue_query = Application.objects.filter(status__in=['HIRED', 'OFFER']).aggregate(
        total_commission=Sum(F('job__salary_budget') * F('job__commission_rate') / 100)
    )
    raw_revenue = revenue_query['total_commission'] or 0
    formatted_revenue = "{:,.0f}".format(raw_revenue)

    # Chart Data
    pipeline_data = list(Application.objects.values('status').annotate(count=Count('status')))
    chart_labels = []
    chart_values = []
    for item in pipeline_data:
        chart_labels.append(item['status'].capitalize())
        chart_values.append(item['count'])

    # Recent Hires
    recent_hires = Application.objects.filter(status='HIRED').select_related('candidate', 'job').order_by('-created_at')[:5]

    context = {
        'is_dashboard': True,
        'active_jobs_count': active_jobs_count,
        'total_candidates': total_candidates,
        'projected_revenue': formatted_revenue,
        'chart_labels': chart_labels,
        'chart_values': chart_values,
        'recent_hires': recent_hires
    }
    
    return render(request, 'home.html', context)