FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Apply migrations, then serve with gunicorn. $PORT lets hosts like Render pick the port.
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn SMS.wsgi:application --bind 0.0.0.0:${PORT} --workers 2 --access-logfile -"]
