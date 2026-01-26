from django.shortcuts import render, redirect
from django.db.models import Sum, Count, F, Avg
from django.utils import timezone
from jobs.models import Job
from candidates.models import Application

def home(request):
    # Client dashboard
    if request.user.is_authenticated and request.user.role == 'Client':
        return redirect('web_test:client_dashboard')

    if request.user.is_authenticated:
        
        #CANDIDATE DASHBOARD 
        if request.user.role == 'Candidate':
            my_apps = Application.objects.filter(candidate=request.user).select_related('job').order_by('-created_at')
            view_type = request.GET.get('view', 'applications')
            
            if view_type == 'offers': #view offers e shudhu "offer" ebong "Hired" dekhabe
                my_apps = my_apps.filter(status__in=['OFFER', 'HIRED'])

            context = {
                'is_dashboard': True,
                'my_applications': my_apps,
                'view_type': view_type,
            }
            return render(request, 'home.html', context)

        # HR / ADMIN DASHBOARD 
        elif request.user.role in ['HR', 'Admin'] or request.user.is_superuser:
            
            active_jobs_count = Job.objects.filter(status='OPEN').count()
            total_candidates = Application.objects.count()
            
            # Revenue Calculation
            revenue_query = Application.objects.filter(status__in=['HIRED', 'OFFER']).aggregate(
                total_commission=Sum(F('job__salary_budget') * F('job__commission_rate') / 100)
            )
            raw_revenue = revenue_query['total_commission'] or 0
            formatted_revenue = "{:,.0f}".format(raw_revenue)

            #Pipeline Chart Data
            pipeline_data = list(Application.objects.values('status').annotate(count=Count('status')))
            chart_labels = []
            chart_values = []
            for item in pipeline_data:
                chart_labels.append(item['status'].replace('_', ' ').title())
                chart_values.append(item['count'])

            # Time to Hire (Average Days) 
            # Logic: For HIRED candidates, avg difference between updated_at (hired time) and created_at
            hired_apps = Application.objects.filter(status='HIRED')
            time_to_hire = 0
            if hired_apps.exists():
                total_days = 0
                for app in hired_apps:
                    delta = app.updated_at - app.created_at  
                    total_days += delta.days
                time_to_hire = round(total_days / hired_apps.count())

            # Pass Rate 
            # Logic: Candidates who are NOT Rejected / Total Candidates
            pass_rate = 0
            if total_candidates > 0:
                passed_count = Application.objects.exclude(status__in=['REJECTED', 'APPLIED']).count()
                pass_rate = round((passed_count / total_candidates) * 100)

            # 5. Recent Hires
            recent_hires = Application.objects.filter(status='HIRED').select_related('candidate', 'job').order_by('-updated_at')[:5]

            context = {
                'is_dashboard': True,
                'active_jobs_count': active_jobs_count,
                'total_candidates': total_candidates,
                'projected_revenue': formatted_revenue,
                'time_to_hire': time_to_hire,  
                'pass_rate': pass_rate,        
                'chart_labels': chart_labels,
                'chart_values': chart_values,
                'recent_hires': recent_hires
            }
            return render(request, 'home.html', context)

    # Guest View
    return render(request, 'home.html', {'is_dashboard': False})