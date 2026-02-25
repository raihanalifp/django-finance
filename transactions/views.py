from django.shortcuts import render, redirect


def landing(request):
    """Landing page — accessible by anyone."""
    if request.user.is_authenticated:
        return redirect("admin:index")
    return render(request, "transactions/landing.html")
