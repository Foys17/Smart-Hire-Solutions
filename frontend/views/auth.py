from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from frontend.forms import UserLoginForm, UserRegistrationForm

def register_view(request):
    if request.user.is_authenticated:
        if request.user.role == 'Client':
            return redirect('web_test:client_dashboard')
        return redirect('web_test:job_list')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # --- FIX: Specify the backend before logging in ---
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            # --------------------------------------------------
            
            login(request, user)
            messages.success(request, f"Welcome, {user.full_name}!")
            
            # Redirect based on role
            if user.role == 'Client':
                return redirect('web_test:client_dashboard')
            return redirect('web_test:job_list')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'auth/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        # Redirect based on role if already logged in
        if request.user.role == 'Client':
            return redirect('web_test:client_dashboard')
        return redirect('web_test:job_list')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            remember_me = request.POST.get('remember-me')
            if not remember_me:
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(1209600) 

            # --- NEW REDIRECT LOGIC ---
            if user.role == 'Client':
                return redirect('web_test:client_dashboard')
            # --------------------------

            return redirect('web_test:job_list')
    else:
        form = UserLoginForm()

    return render(request, 'auth/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('web_test:login')