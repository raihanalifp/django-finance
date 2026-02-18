from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from datetime import date, datetime, timedelta
from .models import Transaction, Category
import json
import calendar


def landing(request):
    """Landing page — accessible by anyone."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'transactions/landing.html')


@login_required(login_url='/admin/login/')
def dashboard(request):
    today = date.today()

    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    # Default ke bulan berjalan
    if not from_date and not to_date:
        first_day = today.replace(day=1)
        last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        from_date = first_day
        to_date = last_day
    else:
        from_date = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_date = datetime.strptime(to_date, "%Y-%m-%d").date()

    transactions = Transaction.objects.filter(
        date__range=[from_date, to_date],
        category__type='expense'
    )

    # Generate tanggal 1–akhir bulan
    num_days = (to_date - from_date).days + 1

    chart_labels = []
    chart_data = []
    background_colors = []
    tooltip_details = []

    for i in range(num_days):
        current_date = from_date + timedelta(days=i)
        chart_labels.append(current_date.strftime("%d"))

        daily_transactions = transactions.filter(date=current_date)

        total = daily_transactions.aggregate(
            total=Sum('amount')
        )['total'] or 0

        chart_data.append(float(total))

        # Highlight hari ini
        if current_date == today:
            background_colors.append('rgba(239, 68, 68, 0.8)')
        else:
            background_colors.append('rgba(59, 130, 246, 0.6)')

        # Tooltip detail kategori
        categories_today = daily_transactions \
            .values('category__name') \
            .annotate(total=Sum('amount'))

        detail_text = []
        for c in categories_today:
            detail_text.append(f"{c['category__name']}: {c['total']}")

        tooltip_details.append(
            ", ".join(detail_text) if detail_text else "Tidak ada pengeluaran"
        )

    # Income & Expense mengikuti filter
    filtered_transactions = Transaction.objects.filter(
        date__range=[from_date, to_date]
    )

    total_income = filtered_transactions.filter(
        category__type='income'
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_expense = filtered_transactions.filter(
        category__type='expense'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Balance realtime (semua waktu)
    all_transactions = Transaction.objects.all()

    all_income = all_transactions.filter(
        category__type='income'
    ).aggregate(total=Sum('amount'))['total'] or 0

    all_expense = all_transactions.filter(
        category__type='expense'
    ).aggregate(total=Sum('amount'))['total'] or 0

    balance = all_income - all_expense

    context = {
        'transactions': filtered_transactions.order_by('-date'),

        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,

        'chart_labels_json': json.dumps(chart_labels),
        'chart_data_json': json.dumps(chart_data),
        'background_colors_json': json.dumps(background_colors),

        'from_date': from_date.strftime("%Y-%m-%d"),
        'to_date': to_date.strftime("%Y-%m-%d"),

        'tooltip_details_json': json.dumps(tooltip_details),
    }

    return render(request, 'transactions/dashboard.html', context)


@login_required(login_url='/admin/login/')
def add_transaction(request):
    if request.method == 'POST':
        category_id = request.POST.get('category')
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        date = request.POST.get('date')

        Transaction.objects.create(
            category_id=category_id,
            amount=amount,
            description=description,
            date=date
        )

        return redirect('dashboard')

    categories = Category.objects.all()

    return render(request, 'transactions/add_transaction.html', {
        'categories': categories
    })