# Sachet Microservices - Render Deployment Guide

## Overview

The Sachet Missing Child Alert System has been decomposed into a **6-service microservices architecture**:

1. **Gateway Service** (Port 5000) - Main web service, orchestration layer
2. **Case Service** (Port 5001) - CRUD operations for cases and sightings
3. **Media Service** (Port 5002) - Photo/audio uploads, poster generation
4. **Notification Service** (Port 5003) - Telegram/Discord/SMS alerts
5. **Geocoding Service** (Port 5004) - Location to coordinates conversion
6. **Analytics Service** (Port 5005) - Risk zones, demographics, insights

All services communicate via **secure REST APIs** with API key authentication.

---

## Prerequisites

### 1. Render.com Account
- Create a free account at https://render.com
- Connect your GitHub repository

### 2. Required API Keys
You'll need to configure these API keys in Render:

- **Cloudinary** (for media uploads)
  - `CLOUDINARY_URL`
  - `CLOUDINARY_CLOUD_NAME`
  - `CLOUDINARY_API_KEY`
  - `CLOUDINARY_API_SECRET`

- **Google Maps API** (for geocoding)
  - `GOOGLE_MAPS_API_KEY`

- **Telegram Bot** (for alerts)
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`

- **Discord Webhook** (optional, for alerts)
  - `DISCORD_WEBHOOK_URL`

- **Twilio** (optional, for SMS alerts)
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_PHONE_NUMBER`

---

## Deployment Steps

### Method 1: Deploy via render.yaml (RECOMMENDED)

The `render.yaml` file is pre-configured to deploy all 6 services + PostgreSQL database.

#### Step 1: Push code to GitHub
```bash
git add .
git commit -m "Microservices architecture ready for deployment"
git push origin main
```

#### Step 2: Create a new Blueprint in Render

1. Go to Render Dashboard → **Blueprints**
2. Click **"New Blueprint Instance"**
3. Connect your GitHub repository
4. Select the branch (e.g., `main`)
5. Render will automatically detect `render.yaml`

#### Step 3: Configure Environment Variables

Render will create all 6 services. For each service, you need to configure the environment variables:

##### Gateway Service (`sachet-gateway`)
- `SERVICE_API_KEY` - **CRITICAL**: Copy this value from Render's auto-generated value
- `CLOUDINARY_URL`, `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
- `GOOGLE_MAPS_API_KEY`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- `DISCORD_WEBHOOK_URL` (optional)
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` (optional)

##### All Backend Services
- `SERVICE_API_KEY` - **MUST MATCH** the value from Gateway Service

**Important**: The `SERVICE_API_KEY` must be **identical** across all services for inter-service authentication to work.

#### Step 4: Deploy

Click **"Apply"** and Render will:
1. Create the PostgreSQL database
2. Deploy all 6 services
3. Link services to the database
4. Configure internal networking

This will take **10-15 minutes** for the initial deployment.

---

### Method 2: Manual Service Creation

If you prefer to create services manually:

#### 1. Create PostgreSQL Database

1. Render Dashboard → **New** → **PostgreSQL**
2. Name: `missing-children-db`
3. Database: `sachet_db`
4. User: `sachet_user`
5. Plan: Free
6. Region: Oregon
7. Click **"Create Database"**

#### 2. Create Gateway Service

1. Render Dashboard → **New** → **Web Service**
2. Connect GitHub repo
3. Configuration:
   - Name: `sachet-gateway`
   - Runtime: Python 3
   - Region: Oregon
   - Branch: `main`
   - Build Command: `cd gateway && pip install -r requirements.txt`
   - Start Command: `cd gateway && gunicorn app:app --bind 0.0.0.0:$PORT`
4. Environment Variables: (Add all from Gateway Service section above)
5. Click **"Create Web Service"**

#### 3. Create Backend Services

Repeat for each service (Case, Media, Notification, Geocoding, Analytics):

**Case Service:**
- Build: `pip install -r requirements-shared.txt && cd services/case-service && pip install -r requirements.txt`
- Start: `cd services/case-service && gunicorn app:app --bind 0.0.0.0:$PORT`
- Env: `DATABASE_URL`, `SERVICE_API_KEY`

**Media Service:**
- Build: `pip install -r requirements-shared.txt && cd services/media-service && pip install -r requirements.txt`
- Start: `cd services/media-service && gunicorn app:app --bind 0.0.0.0:$PORT`
- Env: `SERVICE_API_KEY`, Cloudinary keys

**Notification Service:**
- Build: `pip install -r requirements-shared.txt && cd services/notification-service && pip install -r requirements.txt`
- Start: `cd services/notification-service && gunicorn app:app --bind 0.0.0.0:$PORT`
- Env: `SERVICE_API_KEY`, Telegram/Discord keys

**Geocoding Service:**
- Build: `pip install -r requirements-shared.txt && cd services/geocoding-service && pip install -r requirements.txt`
- Start: `cd services/geocoding-service && gunicorn app:app --bind 0.0.0.0:$PORT`
- Env: `SERVICE_API_KEY`, `GOOGLE_MAPS_API_KEY`

**Analytics Service:**
- Build: `pip install -r requirements-shared.txt && cd services/analytics-service && pip install -r requirements.txt`
- Start: `cd services/analytics-service && gunicorn app:app --bind 0.0.0.0:$PORT`
- Env: `DATABASE_URL`, `SERVICE_API_KEY`

---

## Post-Deployment Configuration

### 1. Update Backend Service URLs in Gateway

After all services are deployed, update the Gateway service environment variables with the actual Render URLs:

- `CASE_SERVICE_URL` = `https://sachet-case-service.onrender.com`
- `MEDIA_SERVICE_URL` = `https://sachet-media-service.onrender.com`
- `NOTIFICATION_SERVICE_URL` = `https://sachet-notification-service.onrender.com`
- `GEOCODING_SERVICE_URL` = `https://sachet-geocoding-service.onrender.com`
- `ANALYTICS_SERVICE_URL` = `https://sachet-analytics-service.onrender.com`

### 2. Sync SERVICE_API_KEY Across All Services

**CRITICAL**: Ensure `SERVICE_API_KEY` is identical across all 6 services.

1. Copy the auto-generated `SERVICE_API_KEY` from Gateway Service
2. Update `SERVICE_API_KEY` in all 5 backend services to match

### 3. Initialize Database

The database schema will be automatically created when the Case Service and Analytics Service first start (they call `db.create_all()`).

To verify:
1. Check Case Service logs: `Starting Case Service on port 5001...`
2. Check Analytics Service logs: `Starting Analytics Service on port 5005...`

---

## Verification

### Health Checks

Test each service endpoint:

```bash
# Gateway Service
curl https://sachet-gateway.onrender.com/

# Case Service
curl -H "X-Service-API-Key: YOUR_KEY" https://sachet-case-service.onrender.com/health

# Media Service
curl -H "X-Service-API-Key: YOUR_KEY" https://sachet-media-service.onrender.com/health

# Notification Service
curl -H "X-Service-API-Key: YOUR_KEY" https://sachet-notification-service.onrender.com/health

# Geocoding Service
curl -H "X-Service-API-Key: YOUR_KEY" https://sachet-geocoding-service.onrender.com/health

# Analytics Service
curl -H "X-Service-API-Key: YOUR_KEY" https://sachet-analytics-service.onrender.com/health
```

All should return `{"status": "healthy"}`.

### End-to-End Test

1. **Access homepage**: https://sachet-gateway.onrender.com/
2. **Report missing child**: Fill form and submit
3. **Check notifications**: Verify Telegram/Discord alerts
4. **Admin login**: https://sachet-gateway.onrender.com/admin/login
5. **View dashboard**: Check cases are displayed
6. **View analytics**: Check risk zones are calculated

---

## Troubleshooting

### Issue: "Unauthorized" errors between services

**Cause**: `SERVICE_API_KEY` mismatch

**Fix**:
1. Copy `SERVICE_API_KEY` from Gateway Service
2. Update all 5 backend services to use the same key
3. Redeploy affected services

### Issue: Database connection errors

**Cause**: `DATABASE_URL` not configured

**Fix**:
1. Verify PostgreSQL database is running
2. In Case/Analytics services, ensure `DATABASE_URL` is linked to the database
3. Check database credentials in Render dashboard

### Issue: Cloudinary upload fails

**Cause**: Missing or invalid Cloudinary credentials

**Fix**:
1. Verify all 4 Cloudinary env vars are set in Gateway + Media services
2. Test Cloudinary credentials manually
3. Check Media Service logs for detailed error

### Issue: Geocoding fails

**Cause**: Google Maps API key invalid or quota exceeded

**Fix**:
1. Verify `GOOGLE_MAPS_API_KEY` in Gateway + Geocoding services
2. Check Google Cloud Console for API quota
3. Fallback to Nominatim (free, no API key needed)

### Issue: Telegram alerts not sending

**Cause**: Invalid bot token or chat ID

**Fix**:
1. Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
2. Test bot manually: send `/start` to your bot
3. Check Notification Service logs for errors

---

## Monitoring

### Render Dashboard

- **Logs**: Each service has real-time logs in Render dashboard
- **Metrics**: CPU, memory, request count per service
- **Uptime**: Monitor service health and uptime

### Key Metrics to Monitor

1. **Gateway Service**: Request latency, error rate
2. **Case Service**: Database query performance
3. **Media Service**: Upload success rate, Cloudinary errors
4. **Notification Service**: Alert delivery rate
5. **Geocoding Service**: API quota usage
6. **Analytics Service**: Risk zone calculation time

---

## Scaling

### Free Tier Limitations

Render free tier includes:
- **750 hours/month** per service
- Services **spin down after 15 minutes** of inactivity
- First request after spin-down takes **30-60 seconds**

### Upgrading for Production

For production use, upgrade to paid plans:
- **Starter Plan** ($7/month per service): Always-on, faster performance
- **Standard Plan** ($25/month per service): Auto-scaling, better resources

Recommended upgrades:
1. **Gateway Service** - Starter (always-on for fast response)
2. **Case Service** - Starter (frequent database access)
3. **Media Service** - Starter (heavy image processing)
4. **Other services** - Keep on free tier (less frequent access)

---

## Maintenance

### Database Backups

Render automatically backs up PostgreSQL databases daily (free tier: 7-day retention).

To create manual backup:
1. Render Dashboard → PostgreSQL → `missing-children-db`
2. Click **"Backups"**
3. Click **"Create Backup"**

### Updating Code

```bash
git add .
git commit -m "Update: description of changes"
git push origin main
```

Render will automatically detect changes and redeploy affected services.

### Rollback

If deployment fails:
1. Render Dashboard → Select service
2. Click **"Rollback"** to previous version

---

## Security Best Practices

1. **API Key Rotation**: Rotate `SERVICE_API_KEY` every 90 days
2. **Admin Password**: Use strong, unique password (auto-generated by Render)
3. **Database Access**: Never expose `DATABASE_URL` publicly
4. **HTTPS**: All Render services use HTTPS by default
5. **Environment Variables**: Use Render's encrypted environment variables (never commit to Git)

---

## Cost Estimate

### Free Tier (Current Configuration)

- 6 web services × $0 = **$0/month**
- 1 PostgreSQL database (256 MB) × $0 = **$0/month**
- **Total**: $0/month

### Production Tier (Recommended)

- Gateway Service (Starter) = $7/month
- Case Service (Starter) = $7/month
- Media Service (Starter) = $7/month
- Other 3 services (Free) = $0/month
- PostgreSQL (Starter 1GB) = $7/month
- **Total**: $28/month

---

## Support

- **Render Documentation**: https://render.com/docs
- **Render Community**: https://community.render.com
- **GitHub Issues**: https://github.com/your-repo/issues

---

## Summary

✅ **6 microservices** deployed independently
✅ **Secure API key authentication** between services
✅ **PostgreSQL database** shared across services
✅ **Auto-scaling** and health monitoring
✅ **Zero-downtime deployments** via Git push
✅ **Free tier compatible** for testing

Your Sachet Missing Child Alert System is now running as a scalable, production-ready microservices architecture on Render! 🎉
