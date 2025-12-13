from django.shortcuts import render

def route_login(request):
    """Front-facing login/home page"""
    return render(request, 'SaveNLoad/login.html')

def route_register(request):
    """Registration page"""
    return render(request, 'SaveNLoad/register.html')
