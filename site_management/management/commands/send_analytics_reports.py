"""
Management command to send scheduled analytics email reports
Run this as a cron job: python manage.py send_analytics_reports
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta
from site_management.models import EmailReport, RequestAnalytics, ThreatAlert


class Command(BaseCommand):
    help = 'Send scheduled analytics email reports'

    def handle(self, *args, **options):
        now = timezone.now()

        # Get reports that are due to be sent
        due_reports = EmailReport.objects.filter(
            is_active=True,
            next_send__lte=now
        )

        for report in due_reports:
            self.stdout.write(f"Sending report to {report.recipient_email} for {report.site.host}")

            try:
                # Calculate date range based on frequency
                if report.frequency == 'daily':
                    start_date = now - timedelta(days=1)
                    period = 'Daily'
                elif report.frequency == 'weekly':
                    start_date = now - timedelta(weeks=1)
                    period = 'Weekly'
                else:  # monthly
                    start_date = now - timedelta(days=30)
                    period = 'Monthly'

                # Gather analytics data
                analytics = RequestAnalytics.objects.filter(
                    site=report.site,
                    timestamp__gte=start_date
                )

                total_requests = analytics.count()
                blocked_requests = analytics.filter(action_taken='blocked').count()
                unique_ips = analytics.values('ip_address').distinct().count()
                unique_countries = analytics.values('country_code').distinct().count()
                avg_response = analytics.aggregate(Avg('response_time'))['response_time__avg'] or 0

                # Build email content
                email_body = f"""
{period} Analytics Report for {report.site.host}
{'=' * 60}

SUMMARY
-------
Total Requests: {total_requests}
Blocked Requests: {blocked_requests} ({(blocked_requests/total_requests*100 if total_requests > 0 else 0):.1f}%)
Unique IPs: {unique_ips}
Unique Countries: {unique_countries}
Avg Response Time: {avg_response:.2f}ms

"""

                # Add geographic breakdown if requested
                if report.include_geographic:
                    top_countries = analytics.values('country', 'country_code').annotate(
                        count=Count('id')
                    ).order_by('-count')[:10]

                    email_body += """
GEOGRAPHIC BREAKDOWN (Top 10 Countries)
---------------------------------------
"""
                    for country in top_countries:
                        email_body += f"{country['country'] or 'Unknown'} ({country['country_code'] or 'XX'}): {country['count']} requests\n"
                    email_body += "\n"

                # Add threat summary if requested
                if report.include_threats:
                    threats = ThreatAlert.objects.filter(
                        site=report.site,
                        timestamp__gte=start_date
                    )

                    critical_threats = threats.filter(severity='critical').count()
                    high_threats = threats.filter(severity='high').count()

                    email_body += f"""
THREAT SUMMARY
--------------
Critical Threats: {critical_threats}
High Threats: {high_threats}
Total Alerts: {threats.count()}

"""

                # Add top IPs if requested
                if report.include_top_ips:
                    top_ips = analytics.values('ip_address', 'country').annotate(
                        count=Count('id'),
                        blocked=Count('id', filter=Q(action_taken='blocked'))
                    ).order_by('-count')[:10]

                    email_body += """
TOP REQUESTING IPs
------------------
"""
                    for ip in top_ips:
                        email_body += f"{ip['ip_address']} ({ip['country'] or 'Unknown'}): {ip['count']} requests, {ip['blocked']} blocked\n"
                    email_body += "\n"

                email_body += f"""
---
This is an automated {period.lower()} report.
Generated at: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}
"""

                # Send email
                send_mail(
                    subject=f"{period} Analytics Report - {report.site.host}",
                    message=email_body,
                    from_email='noreply@waf-analytics.com',  # Configure in settings
                    recipient_list=[report.recipient_email],
                    fail_silently=False,
                )

                # Update report record
                report.last_sent = now
                report.next_send = report.calculate_next_send()
                report.save()

                self.stdout.write(self.style.SUCCESS(f"✓ Report sent to {report.recipient_email}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Failed to send report to {report.recipient_email}: {e}"))

        if not due_reports:
            self.stdout.write("No reports due to be sent.")
