import json

from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from SaveNLoad.views.custom_decorators import get_current_user


@ensure_csrf_cookie
def login_page(request):
    if get_current_user(request):
        return redirect('/dashboard')
    return render(request, 'SaveNLoad/pages/login.html', {
        'props': json.dumps({})
    })


@ensure_csrf_cookie
def home_page(request):
    return redirect('/login')


@ensure_csrf_cookie
def settings_page(request):
    return render(request, 'SaveNLoad/pages/settings.html', {
        'props': json.dumps({})
    })


@ensure_csrf_cookie
def dashboard_page(request):
    return render(request, 'SaveNLoad/pages/dashboard.html', {
        'props': json.dumps({})
    })


@ensure_csrf_cookie
def game_detail_page(request, game_id: int):
    return render(request, 'SaveNLoad/pages/game_detail.html', {
        'props': json.dumps({'gameId': game_id})
    })


@ensure_csrf_cookie
def register_page(request):
    return render(request, 'SaveNLoad/pages/register.html', {
        'props': json.dumps({})
    })


@ensure_csrf_cookie
def forgot_password_page(request):
    return render(request, 'SaveNLoad/pages/forgot_password.html', {
        'props': json.dumps({})
    })


@ensure_csrf_cookie
def verify_otp_page(request):
    return render(request, 'SaveNLoad/pages/verify_otp.html', {
        'props': json.dumps({})
    })


@ensure_csrf_cookie
def reset_password_page(request):
    return render(request, 'SaveNLoad/pages/reset_password.html', {
        'props': json.dumps({})
    })


@ensure_csrf_cookie
def worker_required_page(request):
    return render(request, 'SaveNLoad/pages/worker_required.html', {
        'props': json.dumps({})
    })
