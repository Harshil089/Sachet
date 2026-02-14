# Sachet Microservices - Local Development Guide

## Overview

This guide covers running all 6 microservices locally for development and testing.

---

## Quick Start (Without Docker)

### Prerequisites

- Python 3.9+
- PostgreSQL 15+
- Virtual environment

### Step 1: Setup Database

```bash
# Create database
createdb sachet_db

# Or using psql
psql postgres
CREATE DATABASE sachet_db;
\q
```

### Step 2: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=postgresql://localhost:5432/sachet_db

# Inter-service authentication
SERVICE_API_KEY=dev-service-key-change-in-production

# Service URLs (local)
CASE_SERVICE_URL=http://localhost:5001
MEDIA_SERVICE_URL=http://localhost:5002
NOTIFICATION_SERVICE_URL=http://localhost:5003
GEOCODING_SERVICE_URL=http://localhost:5004
ANALYTICS_SERVICE_URL=http://localhost:5005

# Admin credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
SECRET_KEY=dev-secret-key

# Cloudinary (for media uploads)
CLOUDINARY_URL=cloudinary://your-cloudinary-url
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Google Maps API
GOOGLE_MAPS_API_KEY=your-google-maps-api-key

# Telegram Bot
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id

# Discord Webhook (optional)
DISCORD_WEBHOOK_URL=your-discord-webhook-url

# Twilio (optional)
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=your-twilio-phone
```

### Step 3: Install Dependencies

```bash
# Install shared dependencies
pip install -r requirements-shared.txt

# Install service-specific dependencies
cd gateway && pip install -r requirements.txt && cd ..
cd services/case-service && pip install -r requirements.txt && cd ../..
cd services/media-service && pip install -r requirements.txt && cd ../..
cd services/notification-service && pip install -r requirements.txt && cd ../..
cd services/geocoding-service && pip install -r requirements.txt && cd ../..
cd services/analytics-service && pip install -r requirements.txt && cd ../..
```

### Step 4: Initialize Database

The database schema will be automatically created when you first run the Case Service or Analytics Service.

### Step 5: Start All Services

Open **6 terminal windows** and run each service:

#### Terminal 1: Case Service (Port 5001)
```bash
cd services/case-service
python app.py
```

#### Terminal 2: Media Service (Port 5002)
```bash
cd services/media-service
python app.py
```

#### Terminal 3: Notification Service (Port 5003)
```bash
cd services/notification-service
python app.py
```

#### Terminal 4: Geocoding Service (Port 5004)
```bash
cd services/geocoding-service
python app.py
```

#### Terminal 5: Analytics Service (Port 5005)
```bash
cd services/analytics-service
python app.py
```

#### Terminal 6: Gateway Service (Port 5000)
```bash
cd gateway
python app.py
```

### Step 6: Access the Application

Open your browser:
- **Homepage**: http://localhost:5000/
- **Admin Login**: http://localhost:5000/admin/login
- **Report Missing**: http://localhost:5000/report

---

## Using a Process Manager (Recommended)

Instead of managing 6 terminals, use a process manager like `honcho` or `foreman`.

### Install honcho

```bash
pip install honcho
```

### Create Procfile

Create a file named `Procfile.dev` in the project root:

```
case: cd services/case-service && python app.py
media: cd services/media-service && python app.py
notification: cd services/notification-service && python app.py
geocoding: cd services/geocoding-service && python app.py
analytics: cd services/analytics-service && python app.py
gateway: cd gateway && python app.py
```

### Start all services

```bash
honcho -f Procfile.dev start
```

This will start all 6 services in a single terminal with color-coded output.

---

## Testing Individual Services

### Health Checks

```bash
# Case Service
curl -H "X-Service-API-Key: dev-service-key-change-in-production" http://localhost:5001/health

# Media Service
curl -H "X-Service-API-Key: dev-service-key-change-in-production" http://localhost:5002/health

# Notification Service
curl -H "X-Service-API-Key: dev-service-key-change-in-production" http://localhost:5003/health

# Geocoding Service
curl -H "X-Service-API-Key: dev-service-key-change-in-production" http://localhost:5004/health

# Analytics Service
curl -H "X-Service-API-Key: dev-service-key-change-in-production" http://localhost:5005/health
```

### API Endpoints

#### Case Service (Port 5001)

```bash
# Get all cases
curl -H "X-Service-API-Key: dev-service-key-change-in-production" \
  http://localhost:5001/api/cases

# Get case stats
curl -H "X-Service-API-Key: dev-service-key-change-in-production" \
  http://localhost:5001/api/stats
```

#### Geocoding Service (Port 5004)

```bash
# Geocode a location
curl -H "X-Service-API-Key: dev-service-key-change-in-production" \
  "http://localhost:5004/api/geocode?location=Magarpatta%20Pune"
```

#### Analytics Service (Port 5005)

```bash
# Get risk zones
curl -H "X-Service-API-Key: dev-service-key-change-in-production" \
  http://localhost:5005/api/analytics/risk-zones

# Get demographics
curl -H "X-Service-API-Key: dev-service-key-change-in-production" \
  http://localhost:5005/api/analytics/demographics

# Get insights
curl -H "X-Service-API-Key: dev-service-key-change-in-production" \
  http://localhost:5005/api/analytics/insights
```

---

## Debugging

### Enable Debug Mode

In each service's `app.py`, change:

```python
app.run(host='0.0.0.0', port=port, debug=True)  # Enable debug mode
```

### View Logs

Each service outputs logs to the terminal:

```
[2024-02-14 19:30:00] INFO: Starting Case Service on port 5001...
[2024-02-14 19:30:01] INFO: Database connection established
[2024-02-14 19:30:02] INFO: Case Service ready
```

### Common Issues

#### Issue: "Connection refused" errors between services

**Cause**: Backend services not running

**Fix**: Ensure all 5 backend services are running before starting Gateway

#### Issue: Database errors

**Cause**: Database not initialized or connection string incorrect

**Fix**:
1. Verify PostgreSQL is running: `psql -l`
2. Check `DATABASE_URL` in `.env`
3. Delete and recreate database if schema is corrupted

#### Issue: Cloudinary upload fails

**Cause**: Invalid Cloudinary credentials

**Fix**: Verify all 4 Cloudinary env vars in `.env`

---

## Development Workflow

### Making Changes

1. Edit code in the relevant service
2. Restart that specific service
3. Test the changes via Gateway

### Adding New Features

1. **Update shared models** (if needed): `shared/models.py`
2. **Update backend service**: Add API endpoint in service's `app.py`
3. **Update API proxy**: Add proxy function in `gateway/routes/api_proxy.py`
4. **Update Gateway route**: Use proxy function in `gateway/app.py`
5. **Test end-to-end**

### Example: Adding a "Mark as Urgent" Feature

#### 1. Update Case Service

```python
# services/case-service/app.py

@app.route('/api/cases/<report_id>/urgent', methods=['POST'])
@require_api_key
def mark_urgent(report_id):
    case = db.session.execute(
        db.select(MissingChild).where(MissingChild.report_id == report_id)
    ).scalar_one_or_none()

    case.urgent = True
    db.session.commit()

    return jsonify({'success': True})
```

#### 2. Update API Proxy

```python
# gateway/routes/api_proxy.py

def mark_case_urgent(report_id):
    case_service_url = os.environ.get('CASE_SERVICE_URL', 'http://localhost:5001')
    response = requests.post(
        f'{case_service_url}/api/cases/{report_id}/urgent',
        headers=get_service_headers(),
        timeout=30
    )

    if response.status_code == 200:
        return True, None
    else:
        return False, 'Failed to mark as urgent'
```

#### 3. Update Gateway Route

```python
# gateway/app.py

@app.route('/admin/case/<report_id>/mark-urgent', methods=['POST'])
@login_required
def admin_mark_urgent(report_id):
    success, error = api_proxy.mark_case_urgent(report_id)

    if success:
        flash('Case marked as urgent', 'success')
    else:
        flash(f'Error: {error}', 'danger')

    return redirect(url_for('admin_case_detail', report_id=report_id))
```

---

## Performance Optimization

### Database Indexes

Add indexes for frequently queried fields:

```python
# shared/models.py

class MissingChild(db.Model):
    # ... existing fields ...

    __table_args__ = (
        db.Index('idx_status', 'status'),
        db.Index('idx_created_at', 'created_at'),
    )
```

### Caching

Add caching to frequently accessed data:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_risk_zones_cached():
    return get_risk_zones()
```

---

## Testing

### Unit Tests

Create test files in each service:

```bash
services/case-service/test_app.py
services/media-service/test_app.py
# ... etc
```

Example test:

```python
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'
```

Run tests:

```bash
cd services/case-service
pytest test_app.py
```

### Integration Tests

Test end-to-end workflows:

```python
def test_report_missing_child_flow():
    # 1. Geocode location
    # 2. Upload photo
    # 3. Create case
    # 4. Send notification
    # Assert all steps succeed
```

---

## Summary

✅ Run all 6 services locally without Docker
✅ Use `honcho` for simplified process management
✅ Test individual services via API endpoints
✅ Debug with detailed logs
✅ Follow development workflow for new features

Happy coding! 🚀
