# Microservices Architecture Progress

## Overview
Converting Sachet Missing Child Alert System from monolithic architecture to microservices.

**Plan Document**: `/Users/harshilbuch/.claude/plans/flickering-toasting-rainbow.md`

---

## Architecture Summary

### 6 Services Design:
1. **Gateway Service** (Port 5000) - Frontend, templates, orchestration ✅ COMPLETED
2. **Case Service** (Port 5001) - CRUD for cases/sightings ⏳ PENDING
3. **Media Service** (Port 5002) - Photo/audio uploads, poster generation, face comparison ⏳ PENDING
4. **Notification Service** (Port 5003) - Telegram/Discord/SMS alerts ✅ COMPLETED
5. **Geocoding Service** (Port 5004) - Location to coordinates ✅ COMPLETED
6. **Analytics Service** (Port 5005) - Risk zones, demographics ⏳ PENDING

---

## Completed Work (50% Done)

### ✅ Phase 1: Shared Infrastructure (100%)
Created shared code used by all services:

**Files Created:**
- `shared/__init__.py` - Package initialization
- `shared/config.py` - Configuration with service URLs and API key
- `shared/models.py` - All SQLAlchemy models (MissingChild, Sighting, User, RiskZone, Analytics)
- `shared/database.py` - Database initialization helpers
- `shared/auth.py` - Inter-service API key authentication
- `requirements-shared.txt` - Shared dependencies

**Key Features:**
- `@require_service_api_key` decorator for inter-service auth
- `get_service_headers()` helper for API calls
- All models have `to_dict()` methods for JSON serialization
- SERVICE_API_KEY environment variable for secure communication

---

### ✅ Phase 2: Geocoding Service (100%)

**Location**: `services/geocoding-service/`

**Files Created:**
- `app.py` - Complete Flask application with geocoding logic
- `requirements.txt` - Dependencies (requests, gunicorn)

**API Endpoints:**
- `GET /health` - Health check
- `GET /api/geocode?location=<name>` - Geocode single location
- `POST /api/geocode/batch` - Batch geocode multiple locations

**Features:**
- LRU cache (100 locations)
- Google Maps API (primary)
- Nominatim/OpenStreetMap (fallback)
- Rate limiting for Nominatim (1 req/sec)
- Retry logic with exponential backoff
- All endpoints protected with API key authentication

---

### ✅ Phase 2: Notification Service (100%)

**Location**: `services/notification-service/`

**Files Created:**
- `app.py` - Complete Flask application with notification routing
- `requirements.txt` - Dependencies (python-telegram-bot, twilio, requests)
- `utils/messaging.py` - Copied from root utils/

**API Endpoints:**
- `GET /health` - Health check
- `POST /api/notifications/telegram` - Send Telegram alert
- `POST /api/notifications/discord` - Send Discord webhook
- `POST /api/notifications/sms` - Send SMS (currently mocked)
- `POST /api/notifications/broadcast` - Broadcast to all channels

**Features:**
- Async Telegram bot integration
- Discord webhook support
- SMS support (Twilio) - currently in debug mode
- Multi-channel broadcasting
- All endpoints protected with API key authentication

---

### ✅ Phase 3: Gateway Service (100%) - MOST CRITICAL

**Location**: `gateway/`

**Files Created:**
- `app.py` - Main Flask application (600+ lines)
- `routes/__init__.py` - Routes package
- `routes/api_proxy.py` - API proxy helper (400+ lines)
- `requirements.txt` - Dependencies (Flask-Login, requests)

**Public Routes:**
- `GET /` - Homepage with recent cases
- `GET/POST /report` - Report missing child form
- `GET/POST /found/<report_id>` - Report sighting
- `GET /case/<report_id>` - Public case detail
- `GET /poster/<report_id>` - Download missing poster

**Admin Routes:**
- `GET/POST /admin/login` - Admin authentication (brute-force protection)
- `GET /admin/dashboard` - Admin dashboard with all cases
- `GET /admin/case/<report_id>` - Admin case detail
- `GET /admin/update_status/<report_id>/<status>` - Update case status
- `POST /admin/delete_case/<report_id>` - Delete case
- `GET /admin/logout` - Admin logout
- `GET /admin/analytics` - Analytics dashboard
- `GET /admin/risk-zones` - Risk zones map
- `POST /api/analytics/update` - Trigger analytics recalculation

**API Proxy Functions** (in `routes/api_proxy.py`):

*Case Service:*
- `create_case(case_data)` - Create missing child case
- `get_all_cases(filters)` - List all cases
- `get_case(report_id)` - Get case details
- `update_case(report_id, data)` - Update case
- `delete_case(report_id)` - Delete case
- `create_sighting(data)` - Create sighting
- `get_sightings(report_id)` - Get sightings for case

*Media Service:*
- `upload_photo(file, filename)` - Upload and optimize photo
- `upload_audio(file, filename)` - Upload audio file
- `generate_poster(case_data)` - Generate PDF poster
- `compare_faces(url1, url2)` - Face comparison

*Notification Service:*
- `send_telegram_notification(message, photo_url)` - Telegram alert
- `send_discord_notification(message, photo_url)` - Discord alert
- `broadcast_notification(message, photo_url)` - Multi-channel broadcast

*Geocoding Service:*
- `geocode_location(location)` - Geocode location name

*Analytics Service:*
- `get_risk_zones()` - Get all risk zones
- `update_risk_zones()` - Recalculate risk zones
- `get_demographics()` - Get demographic patterns
- `get_insights()` - Get predictive insights

**Security Features:**
- Flask-Login for admin session management
- Brute-force protection (5 attempts, 15min lockout)
- API key authentication for all backend calls
- Auto-logout on public pages
- 404 response for unauthorized admin access (hides admin routes)

**Orchestration Examples:**

*Report Missing Child Flow:*
1. User submits form → Gateway receives
2. Gateway calls Geocoding Service → Get coordinates
3. Gateway calls Media Service → Upload photo/audio
4. Gateway calls Case Service → Create case record
5. Gateway calls Notification Service → Send Telegram alert
6. Gateway returns success to user

*Report Sighting Flow:*
1. User submits sighting → Gateway receives
2. Gateway calls Geocoding Service → Get coordinates
3. Gateway calls Media Service → Upload sighting photo
4. Gateway calls Media Service → Compare faces (if both photos available)
5. Gateway calls Case Service → Create sighting record
6. Gateway calls Notification Service → Send alert
7. Gateway returns success to user

---

## Remaining Work (50% Pending)

### ⏳ Phase 2: Media Service (NOT STARTED)

**Location**: `services/media-service/` (directory exists, utilities copied)

**Files to Create:**
- `app.py` - Main Flask application
- `requirements.txt` - Dependencies (Pillow, cloudinary, face-recognition, qrcode, reportlab)

**Utilities Already Available:**
- `utils/poster_generator.py` - Copied from root
- `utils/face_comparison.py` - Copied from root

**API Endpoints to Implement:**
- `GET /health` - Health check
- `POST /api/media/upload-photo` - Upload and optimize photo (resize to 800x800, JPEG)
- `POST /api/media/upload-audio` - Upload audio to Cloudinary
- `POST /api/media/generate-poster` - Generate A4 PDF poster with QR code
- `POST /api/media/compare-faces` - Compare two face photos, return match score 0-100
- `DELETE /api/media/delete-file` - Delete file from Cloudinary

**Logic to Extract from app.py:**
- Lines 291-377: File upload functions (upload_to_cloudinary, upload_audio_to_cloudinary, save_file_locally)
- Use existing utils/poster_generator.py
- Use existing utils/face_comparison.py

---

### ⏳ Phase 2: Case Service (NOT STARTED)

**Location**: `services/case-service/` (directory does not exist)

**Files to Create:**
- `app.py` - Main Flask application
- `requirements.txt` - Dependencies (SQLAlchemy, psycopg2)

**API Endpoints to Implement:**
- `GET /health` - Health check
- `POST /api/cases` - Create missing child case
- `GET /api/cases` - List all cases (with filters: status, limit, offset)
- `GET /api/cases/<report_id>` - Get case details
- `PUT /api/cases/<report_id>` - Update case
- `DELETE /api/cases/<report_id>` - Delete case and associated sightings
- `POST /api/cases/bulk-delete` - Bulk delete cases
- `POST /api/sightings` - Create sighting
- `GET /api/sightings/<report_id>` - Get all sightings for a case
- `PUT /api/cases/<report_id>/status` - Update case status

**Database Access:**
- Direct PostgreSQL connection using shared/models.py
- CRUD operations on MissingChild and Sighting models

---

### ⏳ Phase 2: Analytics Service (NOT STARTED)

**Location**: `services/analytics-service/` (directory does not exist)

**Files to Create:**
- `app.py` - Main Flask application
- `requirements.txt` - Dependencies (SQLAlchemy, psycopg2)

**API Endpoints to Implement:**
- `GET /health` - Health check
- `GET /api/analytics/risk-zones` - Get all risk zones
- `POST /api/analytics/risk-zones/update` - Recalculate risk zones (clustering algorithm)
- `GET /api/analytics/demographics` - Get demographic patterns (age, gender, time, location)
- `GET /api/analytics/insights` - Get predictive insights

**Logic to Extract from app.py:**
- Lines 532-551: calculate_distance() function
- Lines 552-615: analyze_risk_zones() function
- Lines 617-654: calculate_risk_score() function
- Lines 656-720: analyze_demographic_patterns() function
- Lines 722-768: generate_predictive_insights() function

**Database Access:**
- Read from MissingChild table
- Write to RiskZone table
- Write to Analytics table

---

### ⏳ Phase 4: Move Frontend Assets (NOT STARTED)

**Tasks:**
1. Move `templates/` directory to `gateway/templates/`
2. Move `static/` directory to `gateway/static/`
3. Move `init_db.py` to `scripts/init_db.py`
4. Move `migrate_db.py` to `scripts/migrate_db.py`

**Commands:**
```bash
mv templates gateway/
mv static gateway/
mkdir -p scripts
mv init_db.py scripts/
mv migrate_db.py scripts/
```

---

### ⏳ Phase 5: Create Dockerfiles (NOT STARTED)

**Files to Create:**

1. `gateway/Dockerfile`
2. `services/case-service/Dockerfile`
3. `services/media-service/Dockerfile`
4. `services/notification-service/Dockerfile`
5. `services/geocoding-service/Dockerfile`
6. `services/analytics-service/Dockerfile`
7. `.dockerignore` (root)

**Standard Dockerfile Template:**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE <PORT>

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:<PORT>", "--workers", "2", "--timeout", "120", "app:app"]
```

---

### ⏳ Phase 6: Create docker-compose.yml (NOT STARTED)

**Location**: Root directory

**Services to Define:**
- postgres (PostgreSQL 15)
- gateway (port 5000)
- case-service (port 5001)
- media-service (port 5002)
- notification-service (port 5003)
- geocoding-service (port 5004)
- analytics-service (port 5005)

**Environment Variables:**
- DATABASE_URL (for services with DB access)
- SERVICE_API_KEY (for inter-service auth)
- All service URLs (CASE_SERVICE_URL, MEDIA_SERVICE_URL, etc.)
- Cloudinary credentials
- Telegram/Discord credentials
- Admin credentials

**Template in Plan**: See `/Users/harshilbuch/.claude/plans/flickering-toasting-rainbow.md` lines 369-443

---

### ⏳ Phase 7: Update render.yaml (NOT STARTED)

**File**: `render.yaml` (root)

**Services to Define:**
- PostgreSQL database (sachet-postgres)
- Gateway service (sachet-gateway)
- Case service (sachet-case-service)
- Media service (sachet-media-service)
- Notification service (sachet-notification-service)
- Geocoding service (sachet-geocoding-service)
- Analytics service (sachet-analytics-service)

**Key Configuration:**
- All services use Docker (dockerfilePath)
- Shared DATABASE_URL from postgres service
- Shared SERVICE_API_KEY across all services
- Service URLs point to Render internal URLs (https://sachet-*-service.onrender.com)
- Free tier plan for all services

**Template in Plan**: See plan document lines 451-526

---

## Environment Variables

### New Variables Added:
```bash
SERVICE_API_KEY=<generate-random-key>  # For inter-service authentication

# Service URLs (defaults for Docker Compose)
CASE_SERVICE_URL=http://case-service:5001
MEDIA_SERVICE_URL=http://media-service:5002
NOTIFICATION_SERVICE_URL=http://notification-service:5003
GEOCODING_SERVICE_URL=http://geocoding-service:5004
ANALYTICS_SERVICE_URL=http://analytics-service:5005
```

### Existing Variables (unchanged):
- DATABASE_URL
- CLOUDINARY_URL / CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET
- TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID
- DISCORD_WEBHOOK_URL
- GOOGLE_MAPS_API_KEY
- TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_PHONE_NUMBER
- ADMIN_USERNAME / ADMIN_PASSWORD / ADMIN_ACCESS_TOKEN
- SECRET_KEY

---

## Testing Strategy

### Local Development (Docker Compose):
1. Start all services: `docker-compose up --build`
2. Gateway accessible at: `http://localhost:5000`
3. Service URLs use internal Docker network names

### Production (Render.com):
1. Deploy all services via `render.yaml`
2. Gateway accessible at: `https://sachet-gateway.onrender.com`
3. Service URLs use Render internal URLs

### End-to-End Tests:
- [ ] Homepage loads with recent cases
- [ ] Report missing child (photo upload, geocoding, notification)
- [ ] Case detail page displays
- [ ] Report sighting (photo upload, face comparison, notification)
- [ ] Admin login (brute-force protection)
- [ ] Admin dashboard shows all cases
- [ ] Admin can update case status
- [ ] Admin can delete case
- [ ] Poster download works
- [ ] Analytics page loads
- [ ] All services respond to health checks

---

## File Structure Summary

```
/Users/harshilbuch/Sachet-1/
├── shared/                                 ✅ DONE
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── database.py
│   └── auth.py
├── gateway/                                ✅ DONE
│   ├── requirements.txt
│   ├── app.py
│   ├── routes/
│   │   ├── __init__.py
│   │   └── api_proxy.py
│   ├── templates/                          ⏳ PENDING (move from root)
│   └── static/                             ⏳ PENDING (move from root)
├── services/
│   ├── geocoding-service/                  ✅ DONE
│   │   ├── requirements.txt
│   │   └── app.py
│   ├── notification-service/               ✅ DONE
│   │   ├── requirements.txt
│   │   ├── app.py
│   │   └── utils/
│   │       └── messaging.py
│   ├── media-service/                      ⏳ PENDING
│   │   ├── requirements.txt (to create)
│   │   ├── app.py (to create)
│   │   └── utils/
│   │       ├── poster_generator.py (copied)
│   │       └── face_comparison.py (copied)
│   ├── case-service/                       ⏳ PENDING (create directory)
│   │   ├── requirements.txt
│   │   └── app.py
│   └── analytics-service/                  ⏳ PENDING (create directory)
│       ├── requirements.txt
│       └── app.py
├── requirements-shared.txt                 ✅ DONE
├── docker-compose.yml                      ⏳ PENDING
├── render.yaml                             ⏳ PENDING (update)
├── templates/                              📦 (move to gateway/)
├── static/                                 📦 (move to gateway/)
└── MICROSERVICES_PROGRESS.md               ✅ THIS FILE
```

---

## Quick Start Guide for Continuation

### To Continue Building:

1. **Next Priority: Case Service** (most critical backend service)
   ```bash
   mkdir -p services/case-service
   # Create app.py with CRUD endpoints
   # Create requirements.txt
   ```

2. **Then: Media Service** (utilities already copied)
   ```bash
   # Create services/media-service/app.py
   # Create services/media-service/requirements.txt
   ```

3. **Then: Analytics Service**
   ```bash
   mkdir -p services/analytics-service
   # Create app.py with analytics logic
   # Create requirements.txt
   ```

4. **Move Frontend Assets**
   ```bash
   mv templates gateway/
   mv static gateway/
   mkdir -p scripts
   mv init_db.py scripts/
   mv migrate_db.py scripts/
   ```

5. **Create Dockerfiles**
   - Use template from Phase 5 section above
   - Create one for each service

6. **Create docker-compose.yml**
   - Use template from plan document
   - Test locally

7. **Update render.yaml**
   - Use template from plan document
   - Deploy to Render

---

## Key Design Decisions

1. **Shared Database**: All services access the same PostgreSQL instance (pragmatic for this project size)
2. **API Key Authentication**: Simple X-Service-API-Key header for inter-service auth
3. **Gateway Pattern**: Gateway orchestrates all backend services, handles user sessions
4. **Service Discovery**: Environment variables for service URLs (Docker Compose vs Render)
5. **Stateless Services**: Media, Notification, Geocoding have no database dependencies
6. **Synchronous Communication**: REST APIs (no message queues for simplicity)

---

## Performance Benefits

- **Reduced Load**: Heavy operations (media processing, face comparison, geocoding, analytics) run in separate processes
- **Independent Scaling**: Each service can scale independently on Render
- **Fault Isolation**: If media service crashes, main site stays up
- **Easier Maintenance**: Each service has focused responsibilities

---

## Contacts & Resources

- **Plan Document**: `/Users/harshilbuch/.claude/plans/flickering-toasting-rainbow.md`
- **Original Monolithic App**: `app.py` (1,456 lines - DO NOT DELETE YET)
- **Original Config**: `config.py` (moved to shared/config.py)
- **Progress Tracking**: This file + `/tasks` command

---

**Last Updated**: 2026-02-14
**Progress**: 50% Complete (3 of 6 services + Gateway)
**Estimated Remaining**: 3-4 days of work
