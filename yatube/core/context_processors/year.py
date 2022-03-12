from datetime import datetime


def year(request):
    """Добавляет переменную с текущим годом."""
    current_yaer = datetime.now().year
    return {
        'year': current_yaer
    }
