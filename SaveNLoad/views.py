from django.shortcuts import render

def login(request):
    """Login page"""
    return render(request, 'SaveNLoad/login.html')

def register(request):
    """Registration page"""
    return render(request, 'SaveNLoad/register.html')

def forgot_password(request):
    """Forgot password page"""
    return render(request, 'SaveNLoad/forgot_password.html')
