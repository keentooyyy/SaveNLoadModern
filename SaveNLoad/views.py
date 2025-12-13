from django.shortcuts import render

def route_login(request):
    """Front-facing login/home page"""
    return render(request, 'SaveNLoad/login.html')
