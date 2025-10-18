from django.shortcuts import redirect
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.views.generic import View, TemplateView
from django.conf import settings
import requests
import secrets


class GoogleLoginView(View):
    """Initiate Google OAuth login"""
    
    def get(self, request):
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state
        
        params = {
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
            'scope': 'openid email profile',
            'response_type': 'code',
            'state': state,
        }
        
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        return redirect(auth_url)


class GoogleCallbackView(View):
    """Handle Google OAuth callback"""
    
    def get(self, request):
        code = request.GET.get('code')
        state = request.GET.get('state')
        
        # Verify state
        if state != request.session.get('oauth_state'):
            return redirect('/auth/login/?error=invalid_state')
        
        # Exchange code for token
        token_data = {
            'code': code,
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
            'grant_type': 'authorization_code',
        }
        
        token_response = requests.post('https://oauth2.googleapis.com/token', data=token_data)
        token_json = token_response.json()
        
        if 'error' in token_json:
            return redirect('/auth/login/?error=token_failed')
        
        # Get user info
        access_token = token_json['access_token']
        user_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        user_info = user_response.json()
        
        # Get or create user
        email = user_info.get('email')
        user, created = User.objects.get_or_create(
            username=email,
            defaults={
                'email': email,
                'first_name': user_info.get('given_name', ''),
                'last_name': user_info.get('family_name', ''),
            }
        )
        
        # Login user
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        
        # Redirect to original destination or dashboard
        next_url = request.session.get('next', '/analytics/')
        return redirect(next_url)


class LogoutView(View):
    """Logout user"""
    
    def get(self, request):
        logout(request)
        return redirect('/auth/login/')


class LoginPageView(TemplateView):
    """Login page"""
    template_name = 'auth/login.html'
