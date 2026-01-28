# Reserve at Ease - Django Backend API

A comprehensive Django REST API backend for the Reserve at Ease accommodation booking platform.

## Features

- **User Authentication**: JWT-based authentication with email verification
- **Property Management**: Complete CRUD operations for properties and rooms
- **Reservation System**: Booking management with payment tracking
- **Review System**: Property reviews with ratings and responses
- **Messaging**: Real-time messaging between users and property owners
- **Search & Filtering**: Advanced property search with filters
- **Dashboard Analytics**: Comprehensive analytics for users and owners
- **File Upload**: Image management for properties and reviews

## Tech Stack

- **Backend**: Django 5.2.8 with Django REST Framework
- **Database**: PostgreSQL (production), SQLite (development)
- **Authentication**: JWT (JSON Web Tokens)
- **File Storage**: Django Storages (AWS S3 support)
- **Background Tasks**: Celery with Redis
- **API Documentation**: Django REST Framework browsable API

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL (for production)
- Redis (for Celery)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd reserve-at-ease-backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment variables**
   Create a `.env` file in the project root:
   ```env
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   DB_NAME=reserve_at_ease
   DB_USER=postgres
   DB_PASSWORD=password
   DB_HOST=localhost
   DB_PORT=5432
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   FRONTEND_URL=http://localhost:3000
   ```

5. **Database setup**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

## API Endpoints

### Authentication (`/api/auth/`)
- `POST /register/` - User registration
- `POST /login/` - User login
- `POST /logout/` - User logout
- `POST /token/refresh/` - Refresh JWT token
- `GET /profile/` - Get user profile
- `PUT /profile/` - Update user profile
- `POST /change-password/` - Change password
- `POST /request-password-reset/` - Request password reset
- `POST /reset-password/<token>/` - Reset password with token
- `GET /verify-email/<token>/` - Verify email address
- `POST /resend-verification/` - Resend verification email

### Properties (`/api/properties/`)
- `GET /` - List properties (with filtering and search)
- `POST /` - Create property (owner only)
- `GET /<id>/` - Get property details
- `PUT /<id>/` - Update property (owner only)
- `DELETE /<id>/` - Delete property (owner only)
- `GET /search/` - Advanced property search
- `GET /my-properties/` - Get user's properties (owner only)
- `GET /<id>/rooms/` - List property rooms
- `POST /<id>/rooms/` - Create room (owner only)
- `GET /rooms/<id>/` - Get room details
- `PUT /rooms/<id>/` - Update room (owner only)
- `DELETE /rooms/<id>/` - Delete room (owner only)
- `GET /<id>/availability/` - Get property availability
- `POST /<id>/upload-image/` - Upload property image (owner only)

### Reservations (`/api/reservations/`)
- `GET /` - List user reservations
- `POST /` - Create reservation
- `GET /<id>/` - Get reservation details
- `PUT /<id>/` - Update reservation
- `POST /create/` - Create reservation with validation
- `GET /owner/` - Get owner's property reservations
- `GET /stats/` - Get reservation statistics
- `GET /calendar/` - Get calendar view
- `POST /<id>/cancel/` - Cancel reservation
- `POST /<id>/confirm/` - Confirm reservation (owner only)
- `POST /<id>/check-in/` - Check in guest (owner only)
- `POST /<id>/check-out/` - Check out guest (owner only)
- `POST /<id>/payment/` - Add payment

### Reviews (`/api/reviews/`)
- `GET /property/<id>/` - List property reviews
- `POST /property/<id>/create/` - Create review
- `GET /<id>/` - Get review details
- `PUT /<id>/update/` - Update review
- `POST /<id>/respond/` - Respond to review (owner only)
- `POST /<id>/images/` - Upload review image
- `POST /<id>/helpful/` - Mark review as helpful
- `POST /<id>/report/` - Report review

### Messaging (`/api/messaging/`)
- `GET /conversations/` - List conversations
- `POST /conversations/` - Create conversation
- `GET /conversations/<id>/` - Get conversation details
- `GET /conversations/<id>/messages/` - List messages
- `POST
