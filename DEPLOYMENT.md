# Missing Child Alert System - Deployment Guide

## 🚀 Quick Deployment Options

### Option 1: Render (Recommended - Free Tier Available)

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/missing-child-alert.git
   git push -u origin main
   ```

2. **Deploy on Render**:
   - Go to [render.com](https://render.com)
   - Connect your GitHub repository
   - Select "Web Service"
   - Use these settings:
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app`
     - **Python Version**: 3.12.0

3. **Create PostgreSQL Database** (for persistent data):
   - In Render dashboard, click "New +"
   - Select "PostgreSQL"
   - Choose "Free" plan
   - Name it "missing-children-db"
   - Note the connection string

4. **Environment Variables** (in Render dashboard):
   - `SECRET_KEY`: Generate a secure random key
   - `ADMIN_USERNAME`: Set your admin username
   - `ADMIN_PASSWORD`: Set a secure password
   - `FLASK_ENV`: `production`
   - `DEBUG`: `false`
   - `DATABASE_URL`: Copy from your PostgreSQL database

5. **Automatic Database Setup**:
   - The app will automatically create tables and admin user on first run
   - Your data will persist across deployments!

### Option 2: Heroku

1. **Install Heroku CLI** and login
2. **Create Heroku app**:
   ```bash
   heroku create your-app-name
   ```

3. **Set environment variables**:
   ```bash
   heroku config:set SECRET_KEY=your-secret-key
   heroku config:set ADMIN_USERNAME=admin
   heroku config:set ADMIN_PASSWORD=your-password
   heroku config:set FLASK_ENV=production
   ```

4. **Deploy**:
   ```bash
   git push heroku main
   ```

### Option 3: Railway

1. **Connect GitHub** to [railway.app](https://railway.app)
2. **Select your repository**
3. **Railway will auto-detect** Python and use the Procfile
4. **Set environment variables** in Railway dashboard

### Option 4: Docker Deployment

1. **Build Docker image**:
   ```bash
   docker build -t missing-child-alert .
   ```

2. **Run container**:
   ```bash
   docker run -p 5000:5000 \
     -e SECRET_KEY=your-secret-key \
     -e ADMIN_USERNAME=admin \
     -e ADMIN_PASSWORD=your-password \
     missing-child-alert
   ```

3. **Deploy to cloud**:
   - Push to Docker Hub
   - Deploy on any cloud provider (AWS, GCP, Azure, DigitalOcean)

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SECRET_KEY` | Flask secret key | Yes | Generated |
| `ADMIN_USERNAME` | Admin login username | Yes | admin |
| `ADMIN_PASSWORD` | Admin login password | Yes | Generated |
| `FLASK_ENV` | Flask environment | No | production |
| `DEBUG` | Debug mode | No | false |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name | No | - |
| `CLOUDINARY_API_KEY` | Cloudinary API key | No | - |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret | No | - |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | No | - |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | No | - |
| `TWILIO_PHONE_NUMBER` | Twilio phone number | No | - |

### File Storage

- **Local Storage**: Files stored in `static/uploads/` (default)
- **Cloudinary**: Optional cloud storage for production
- **Database**: SQLite (file-based, no setup required)

## 📁 Project Structure

```
missing-child-alert/
├── app.py                 # Main application
├── config.py             # Configuration
├── requirements.txt      # Python dependencies
├── Procfile             # Heroku/Railway deployment
├── Dockerfile           # Docker deployment
├── render.yaml          # Render deployment config
├── runtime.txt          # Python version
├── static/              # Static files
│   ├── css/
│   ├── js/
│   └── uploads/         # File uploads
├── templates/           # HTML templates
│   ├── admin/
│   └── errors/
└── missing_children.db  # SQLite database
```

## 🛡️ Security Considerations

1. **Change default credentials**:
   - Update `ADMIN_USERNAME` and `ADMIN_PASSWORD`
   - Generate a strong `SECRET_KEY`

2. **File uploads**:
   - Files are validated for type and size
   - Images are automatically optimized
   - Consider using Cloudinary for production

3. **Database**:
   - SQLite is suitable for small to medium deployments
   - For high-traffic, consider PostgreSQL

## 📊 Monitoring

- **Health Check**: Available at `/health`
- **Logs**: Check platform-specific logging
- **Database**: SQLite file is included in deployment

## 🔄 Updates

To update the deployed application:

1. **Make changes** to your code
2. **Commit and push** to your repository
3. **Platform will auto-deploy** (if configured)
4. **Database persists** across deployments

## 🆘 Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure port 5000 is available
2. **Missing dependencies**: Check `requirements.txt`
3. **Database errors**: Verify SQLite file permissions
4. **Static files**: Check file paths in templates

### Debug Mode

For local debugging, set:
```bash
export FLASK_ENV=development
export DEBUG=true
```

## 📞 Support

- **Documentation**: Check this file and code comments
- **Issues**: Create GitHub issues for bugs
- **Features**: Submit pull requests for improvements

---

**Ready to deploy!** 🚀 Choose your preferred platform and follow the steps above.
