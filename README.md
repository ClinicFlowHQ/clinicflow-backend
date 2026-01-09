# clinicflow-backend

## Overview

**ClinicFlow Backend** is the REST API powering **ClinicFlow**, a doctor-focused clinical management system designed for real-world medical practice.

The backend enables a **single doctor** to securely manage their own:

- Patients
- Consultations (visits)
- Prescriptions
- Appointments (agenda)
- Medical documents (PDF prescriptions)

The system is built with **Django REST Framework** and follows best practices for **security, auditability, and scalability**, with support for **English and French**.

---

## Architecture

ClinicFlow follows a **separation of concerns** architecture:

- **Backend**: Django + Django REST Framework (this repository)
- **Frontend**: Web UI (React) – separate repository

### Frontend Repository

👉 **clinicflow-frontend**  
https://github.com/ClinicFlowHQ/clinicflow-frontend

---

## Key Features

- Secure JWT-based authentication (doctor-only access)
- Patient records management
- Consultation tracking with vital signs  
  - Includes pediatric-specific parameters (e.g. weight, cranial perimeter)
- Prescription management with reusable prescription templates
- PDF generation for signed medical prescriptions
- Appointment scheduling (agenda)
- Internationalization (English 🇬🇧 / French 🇫🇷)
- API-first architecture (ready for web and mobile clients)

---

## Tech Stack

- **Python**
- **Django**
- **Django REST Framework**
- **JWT Authentication**
- **SQLite** (development)
- **PostgreSQL** (recommended for production)
- **RESTful API architecture**
- **Internationalization (i18n)**

---

## Project Structure

```text
clinicflow-backend/
├── accounts/                 # Authentication & doctor profile
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
│
├── patients/                 # Patient records
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
│
├── visits/                   # Consultations & vital signs
│   ├── models.py             # Consultation, VitalSign, etc.
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
│
├── prescriptions/            # Prescriptions & templates
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
│
├── appointments/             # Agenda / scheduling
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
│
├── config/                   # Project configuration
│   ├── settings.py           # Environment, i18n, DRF, JWT
│   ├── urls.py               # Global API routes
│   ├── asgi.py
│   └── wsgi.py
│
├── locale/                   # Translations (EN / FR)
│   └── fr/
│       └── LC_MESSAGES/
│           ├── django.po
│           └── django.mo
│
├── manage.py
├── requirements.txt
├── .env                      # Environment variables (not committed)
└── README.md
