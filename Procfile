web: gunicorn clrproj.wsgi --log-file -
release: python manage.py collectstatic --noinput && python manage.py migrate --noinput
