# DDA Tutoring Website (Django)

A premium, conversion-focused marketing website for **DDA Tutoring**, built with Django, HTML, CSS, and vanilla JavaScript.

## 1) Project structure

```text
dda_tutoring/
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── website/
│   ├── templates/website/home.html
│   ├── static/website/css/styles.css
│   ├── static/website/js/main.js
│   ├── views.py
│   └── tests.py
├── manage.py
└── requirements.txt
```

## 2) Local setup and run instructions

```bash
cd dda_tutoring
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open: `http://127.0.0.1:8000/`

## 3) Static files

Development uses app static files automatically.

For production:

```bash
python manage.py collectstatic --noinput
```

Static files are collected into `staticfiles/`.

## 4) Google Form integration (no backend form required)

1. Go to [Google Forms](https://forms.google.com) and create a new form.
2. Add these fields exactly:
   - Parent Name
   - Student Name
   - Grade
   - Email
   - Phone
   - Goals/Concerns
   - Current resources
   - Why DDA Tutoring?
3. Click **Send** in Google Forms:
   - **Link mode:** copy the URL and replace `https://forms.gle/your-form-link` in `website/templates/website/home.html`.
   - **Embed mode:** copy iframe HTML and place it in the contact section if you want in-page embed.
4. Open the **Responses** tab in Google Forms and click the green Sheets icon to connect a spreadsheet.
5. New submissions will automatically sync to Google Sheets.

## 5) Deployment guide (Render / Railway)

### Environment variables

- `DJANGO_SECRET_KEY` (required in production)
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS=<your-domain>`
- Optional: `DJANGO_CSRF_TRUSTED_ORIGINS=https://<your-domain>`

### Render

1. Create a **Web Service** connected to this repo.
2. Set root directory to `dda_tutoring`.
3. Build command:
   ```bash
   pip install -r requirements.txt && python manage.py collectstatic --noinput
   ```
4. Start command:
   ```bash
   gunicorn config.wsgi:application
   ```
5. Set environment variables listed above.

### Railway

1. Create a new project from the repo.
2. Set root to `dda_tutoring`.
3. Add environment variables listed above.
4. Use start command:
   ```bash
   gunicorn config.wsgi:application
   ```
5. Ensure `collectstatic` runs during build (either via build command or post-deploy step).

---

The UI is intentionally premium and minimal, with balanced whitespace, strong typography hierarchy, subtle motion, and responsive sections optimized for parent trust and conversion.
