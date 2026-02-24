from datetime import date, timedelta
from decimal import Decimal
import json

from django.db.models import Sum
from django.urls import reverse_lazy
from django.utils.dateparse import parse_date
from django.utils import timezone

from .models import Category, Transaction


def format_rp(value):
    if value is None:
        value = Decimal("0")
    sign = "-" if value < 0 else ""
    value = abs(value)
    formatted = f"{value:,.2f}"
    formatted = formatted.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{sign}Rp {formatted}"


def _month_range(value):
    first_day = value.replace(day=1)
    if value.month == 12:
        next_month = value.replace(year=value.year + 1, month=1, day=1)
    else:
        next_month = value.replace(month=value.month + 1, day=1)
    last_day = next_month - timedelta(days=1)
    return first_day, last_day


def _daterange(start_date, end_date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def dashboard_callback(request, context):
    today = timezone.localdate()
    default_start, default_end = _month_range(today)
    last_month_end = default_start - timedelta(days=1)
    last_month_start, last_month_end = _month_range(last_month_end)
    ytd_start = date(today.year, 1, 1)
    last_7_start = today - timedelta(days=6)
    last_30_start = today - timedelta(days=29)
    last_90_start = today - timedelta(days=89)

    start_param = request.GET.get("start")
    end_param = request.GET.get("end")
    start_date = parse_date(start_param) if start_param else None
    end_date = parse_date(end_param) if end_param else None

    if not start_date or not end_date:
        start_date, end_date = default_start, default_end
    elif start_date > end_date:
        start_date, end_date = end_date, start_date

    day_keys = list(_daterange(start_date, end_date))
    labels = [value.strftime("%d %b") for value in day_keys]
    range_days = len(day_keys)

    range_queryset = Transaction.objects.filter(date__range=(start_date, end_date))
    income_total = (
        range_queryset.filter(category__type="income").aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )
    expense_total = (
        range_queryset.filter(category__type="expense").aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )
    net_total = income_total - expense_total
    recent_transactions = range_queryset.select_related("category").order_by(
        "-date",
        "-created_at",
    )[:8]

    daily_totals = (
        range_queryset.values("date", "category__type").annotate(total=Sum("amount"))
    )
    totals_map = {}
    for row in daily_totals:
        totals_map[(row["date"], row["category__type"])] = row["total"] or Decimal("0")

    income_series = [
        float(totals_map.get((day, "income"), Decimal("0"))) for day in day_keys
    ]
    expense_series = [
        float(totals_map.get((day, "expense"), Decimal("0"))) for day in day_keys
    ]

    recent_rows = [
        [
            transaction.category.name,
            format_rp(transaction.amount),
            transaction.date.strftime("%Y-%m-%d"),
            transaction.category.type.title(),
        ]
        for transaction in recent_transactions
    ]

    active_categories = Category.objects.filter(
        transaction__date__range=(start_date, end_date)
    ).distinct()

    expense_ratio = Decimal("0")
    if income_total > 0:
        expense_ratio = min(Decimal("100"), (expense_total / income_total) * Decimal("100"))

    top_expense_categories = (
        range_queryset.filter(category__type="expense")
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:5]
    )
    category_palette = [
        ("bg-orange-500", "var(--color-orange-500)"),
        ("bg-blue-500", "var(--color-blue-500)"),
        ("bg-green-500", "var(--color-green-500)"),
        ("bg-red-500", "var(--color-red-500)"),
        ("bg-primary-600", "var(--color-primary-600)"),
    ]
    top_categories = []
    category_labels = []
    category_values = []
    category_colors = []
    for index, row in enumerate(top_expense_categories):
        total = row["total"] or Decimal("0")
        percent = Decimal("0")
        if expense_total > 0:
            percent = min(Decimal("100"), (total / expense_total) * Decimal("100"))
        color_class, color_value = category_palette[index % len(category_palette)]
        top_categories.append(
            {
                "name": row["category__name"],
                "total_display": format_rp(total),
                "percent": float(percent),
                "percent_display": f"{percent:.0f}%",
                "color_class": color_class,
            }
        )
        category_labels.append(row["category__name"])
        category_values.append(float(total))
        category_colors.append(color_value)

    max_ticks = 8
    if range_days <= 6:
        max_ticks = range_days
    elif range_days <= 14:
        max_ticks = 7
    elif range_days <= 31:
        max_ticks = 8
    else:
        max_ticks = 10

    context.update(
        {
            "stats": {
                "categories": active_categories.count(),
                "transactions": range_queryset.count(),
                "income_total": income_total,
                "expense_total": expense_total,
                "net_total": net_total,
            },
            "stats_display": {
                "income_total": format_rp(income_total),
                "expense_total": format_rp(expense_total),
                "net_total": format_rp(net_total),
            },
            "recent_table": {
                "headers": ["Category", "Amount", "Date", "Type"],
                "rows": recent_rows,
            },
            "chart_data": json.dumps(
                {
                    "labels": labels,
                    "datasets": [
                        {
                            "label": "Income",
                            "data": income_series,
                            "backgroundColor": "var(--color-green-500)",
                            "borderColor": "var(--color-green-600)",
                            "displayYAxis": True,
                            "maxTicksXLimit": max_ticks,
                        },
                        {
                            "label": "Expense",
                            "data": expense_series,
                            "backgroundColor": "var(--color-red-500)",
                            "borderColor": "var(--color-red-600)",
                            "displayYAxis": True,
                        },
                    ],
                }
            ),
            "category_chart_data": json.dumps(
                {
                    "labels": category_labels,
                    "datasets": [
                        {
                            "label": "Top Expenses",
                            "data": category_values,
                            "backgroundColor": category_colors,
                            "borderWidth": 0,
                        }
                    ],
                }
            ),
            "date_filter": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "label": f"{start_date.strftime('%d %b %Y')} \u2013 {end_date.strftime('%d %b %Y')}",
            },
            "quick_ranges": {
                "this_month": {
                    "start": default_start.isoformat(),
                    "end": default_end.isoformat(),
                },
                "last_month": {
                    "start": last_month_start.isoformat(),
                    "end": last_month_end.isoformat(),
                },
                "ytd": {
                    "start": ytd_start.isoformat(),
                    "end": today.isoformat(),
                },
                "last_7": {
                    "start": last_7_start.isoformat(),
                    "end": today.isoformat(),
                },
                "last_30": {
                    "start": last_30_start.isoformat(),
                    "end": today.isoformat(),
                },
                "last_90": {
                    "start": last_90_start.isoformat(),
                    "end": today.isoformat(),
                },
            },
            "expense_ratio": float(expense_ratio),
            "top_categories": top_categories,
            "links": {
                "new_transaction": reverse_lazy("admin:transactions_transaction_add"),
                "new_category": reverse_lazy("admin:transactions_category_add"),
            },
        }
    )
    return context
