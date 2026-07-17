from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings as django_settings
from catalogue.models import SystemSetting, Profile, Notification
import json


def get_general_setting(key, default=''):
    try:
        setting = SystemSetting.objects.filter(category='general', key=key).first()
        return setting.value if setting else default
    except Exception:
        return default


def send_email_notification(subject, message, recipient_list=None, html_message=None, from_email=None):
    if not django_settings.DEBUG:
        try:
            contact_email = get_general_setting('contact_email')
            if not contact_email:
                return False

            from_email = from_email or contact_email
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=from_email,
                to=recipient_list or [contact_email],
            )
            if html_message:
                email.content_subtype = 'html'
                email.body = html_message
            email.send(fail_silently=True)
            return True
        except Exception:
            return False
    return True


def create_notification(user, title, message, notification_type='info', send_email=True, send_sms=False):
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        sent_email=send_email,
        sent_sms=send_sms,
    )

    if send_email and user.profile.email_notifications:
        try:
            user_email = user.email
            contact_email = get_general_setting('contact_email')
            from_email = contact_email or django_settings.DEFAULT_FROM_EMAIL

            subject = title
            html_message = render_to_string('notifications/email_notification.html', {
                'notification': notification,
                'user': user,
            })

            send_email_notification(
                subject=subject,
                message=message,
                recipient_list=[user_email],
                html_message=html_message,
                from_email=from_email,
            )
            notification.sent_email = True
            notification.save(update_fields=['sent_email'])
        except Exception:
            pass

    return notification


def send_admin_notification_to_all_users(title, message, notification_type='info'):
    from django.contrib.auth.models import User
    users = User.objects.filter(is_active=True)
    notifications = []

    for user in users:
        try:
            profile = user.profile
            should_send = True
            if notification_type == 'dataset_approval' and not profile.dataset_approval_notifications:
                should_send = False
            elif notification_type == 'dataset_rejection' and not profile.dataset_rejection_notifications:
                should_send = False
            elif notification_type == 'new_dataset' and not profile.new_dataset_alerts:
                should_send = False
            elif notification_type == 'info' and not profile.email_notifications:
                should_send = False

            if should_send:
                notification = create_notification(
                    user=user,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    send_email=True,
                )
                notifications.append(notification)
        except Exception:
            continue

    return notifications


def get_unread_notifications_count(user):
    try:
        return Notification.objects.filter(user=user, is_read=False).count()
    except Exception:
        return 0


def get_recent_notifications(user, limit=10):
    try:
        return Notification.objects.filter(user=user).order_by('-created_at')[:limit]
    except Exception:
        return []
