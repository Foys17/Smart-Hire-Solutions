# users/context_processors.py
from .models import Notification

def notifications(request):
    if request.user.is_authenticated:
        # Get the 5 most recent notifications
        recent_notifications = Notification.objects.filter(user=request.user)[:5]
        # Count only unread ones
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        
        return {
            'nav_notifications': recent_notifications,
            'unread_count': unread_count
        }
    return {}