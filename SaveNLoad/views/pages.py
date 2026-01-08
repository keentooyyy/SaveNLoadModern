import json

from django.shortcuts import redirect, render
from SaveNLoad.views.custom_decorators import get_current_user


def login_page(request):
    if get_current_user(request):
        return redirect('/dashboard')
    return render(request, 'SaveNLoad/pages/login.html', {
        'props': json.dumps({})
    })


def home_page(request):
    return redirect('/login')


def settings_page(request):
    return render(request, 'SaveNLoad/pages/settings.html', {
        'props': json.dumps({})
    })


def dashboard_page(request):
    return render(request, 'SaveNLoad/pages/dashboard.html', {
        'props': json.dumps({})
    })


def game_detail_page(request, game_id: int):
    return render(request, 'SaveNLoad/pages/game_detail.html', {
        'props': json.dumps({'gameId': game_id})
    })


def register_page(request):
    return render(request, 'SaveNLoad/pages/register.html', {
        'props': json.dumps({})
    })


def forgot_password_page(request):
    return render(request, 'SaveNLoad/pages/forgot_password.html', {
        'props': json.dumps({})
    })


def verify_otp_page(request):
    return render(request, 'SaveNLoad/pages/verify_otp.html', {
        'props': json.dumps({})
    })


def reset_password_page(request):
    return render(request, 'SaveNLoad/pages/reset_password.html', {
        'props': json.dumps({})
    })


def worker_required_page(request):
    return render(request, 'SaveNLoad/pages/worker_required.html', {
        'props': json.dumps({})
    })
