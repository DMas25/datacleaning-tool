# ColtraDataAi - Deployment Guide

## 🚀 Local Deployment Checklist

### Pre-Deployment Verification

- [ ] Python 3.8+ installed (`python --version`)
- [ ] Git installed (optional, for version control)
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] App runs locally without errors (`streamlit run app.py`)
- [ ] Test with sample data file
- [ ] Verify all visualizations load correctly
- [ ] Test all export formats (Excel, CSV)

### Step 1: Environment Setup

```bash
# Create project directory
mkdir coltradata-app
cd coltradata-app

# Create virtual environment
python -m venv venv

# Activate environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configuration

Create `.streamlit/config.toml` for customization:

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"

[server]
port = 8501
headless = true
runOnSave = true

[logger]
level = "info"

[client]
showErrorDetails = true
```

### Step 3: Local Testing

```bash
# Run the app
streamlit run app.py

# App will open at: http://localhost:8501
```

Test with these data types:
- ✅ CSV files (UTF-8, CP1252)
- ✅ Excel files (.xlsx)
- ✅ Large files (>10MB)
- ✅ Files with missing values
- ✅ Trade compliance data

### Step 4: Production Deployment

#### Option A: Windows Application

1. **Create batch launcher (coltradata.bat):**
```batch
@echo off
cd /d "%~dp0"
call venv\Scripts\activate
streamlit run app.py
pause
```

2. **Create desktop shortcut** pointing to `coltradata.bat`

#### Option B: Server Deployment

```bash
# Install gunicorn (optional for production)
pip install gunicorn streamlit

# Run with custom port
streamlit run app.py --server.port=8501 --server.address=0.0.0.0

# For background operation (Linux/macOS)
nohup streamlit run app.py > coltradata.log 2>&1 &
```

#### Option C: Docker Containerization

1. **Create Dockerfile:**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

2. **Build and run:**
```bash
# Build image
docker build -t coltradata:latest .

# Run container
docker run -p 8501:8501 coltradata:latest
```

## 🔒 Security Hardening

### Local Network Only
```bash
streamlit run app.py --server.address=127.0.0.1
```

### File Size Limits
Add to app.py:
```python
MAX_FILE_SIZE_MB = 100

if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
    st.error(f"File exceeds {MAX_FILE_SIZE_MB}MB limit")
```

### Rate Limiting (Server)
```bash
# Install rate limiting middleware
pip install slowapi
```

### HTTPS (Production)
Use nginx reverse proxy:
```nginx
server {
    listen 443 ssl;
    server_name coltradata.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8501;
    }
}
```

## 📊 Monitoring & Logging

### Enable Logging
```python
# Already configured in app.py
import logging
logger = logging.getLogger(__name__)
```

### Monitor Performance
```bash
# View system usage
# Windows:
tasklist | findstr python

# Linux/macOS:
ps aux | grep streamlit
```

### Log Rotation
Create `setup_logging.py`:
```python
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'coltradata.log',
    maxBytes=10_000_000,  # 10MB
    backupCount=5
)
```

## 🧪 Testing Procedures

### Unit Testing
```python
# Create test_app.py
import pytest
from app import clean_text_values, detect_anomalies

def test_clean_text():
    df = pd.DataFrame({'col': ['  test  ', 'data']})
    result = clean_text_values(df)
    assert result['col'][0] == 'test'

# Run tests
pytest test_app.py
```

### Integration Testing
```bash
# Test with sample files in /tests/sample_data/
# Verify outputs match expected results
```

## 🔄 Backup & Recovery

### Backup Strategy
```bash
# Backup configuration
cp -r .streamlit/ .streamlit.backup/

# Backup requirements
cp requirements.txt requirements.backup.txt

# Version control
git init
git add .
git commit -m "Initial commit"
```

### Recovery Procedure
```bash
# Restore from backup
cp -r .streamlit.backup/ .streamlit/
pip install -r requirements.backup.txt
```

## 🌐 Multi-User Deployment

### Shared Server Setup
```bash
# Install for all users
pip install --upgrade --system-site-packages -r requirements.txt

# Create shared data directory
mkdir /shared/coltradata-uploads
chmod 777 /shared/coltradata-uploads
```

### Load Balancing (Advanced)
Use behind nginx/Apache:
```nginx
upstream streamlit {
    server 127.0.0.1:8501;
    server 127.0.0.1:8502;
    server 127.0.0.1:8503;
}

server {
    listen 80;
    location / {
        proxy_pass http://streamlit;
    }
}
```

## 📈 Performance Optimization

### For Large Files (>50MB)
```python
# In app.py, add chunking:
CHUNK_SIZE = 10000  # rows per chunk
chunks = pd.read_csv('large_file.csv', chunksize=CHUNK_SIZE)
```

### Caching
```python
@st.cache_data
def load_and_clean_data(uploaded_file):
    return clean_data(load_data(uploaded_file))
```

### Resource Limits
```bash
# Limit memory usage (Linux)
ulimit -v 4000000  # 4GB

# Monitor with:
free -h
df -h
```

## ✅ Post-Deployment Validation

- [ ] App loads within 5 seconds
- [ ] Sample data processes correctly
- [ ] All charts render smoothly
- [ ] Export downloads work
- [ ] No console errors
- [ ] File uploads work
- [ ] Error handling is graceful
- [ ] Performance acceptable

## 📞 Troubleshooting Deployment

### Port Already in Use
```bash
# Find process using port 8501
# Windows:
netstat -ano | findstr :8501

# Kill process:
taskkill /PID <PID> /F

# Or use different port:
streamlit run app.py --server.port=8502
```

### Memory Issues
```bash
# Reduce max file size in code
# or increase system RAM/swap

# Check usage:
streamlit run app.py --logger.level=debug
```

### Slow Performance
- Check file size
- Reduce number of visualizations
- Use data sampling for preview
- Upgrade hardware or optimize code

## 📋 Maintenance Schedule

### Weekly
- [ ] Check for updates: `pip list --outdated`
- [ ] Review error logs
- [ ] Test with new sample data

### Monthly
- [ ] Update dependencies: `pip install --upgrade -r requirements.txt`
- [ ] Review performance metrics
- [ ] Backup data and configurations

### Quarterly
- [ ] Security audit
- [ ] Performance optimization
- [ ] User feedback review
- [ ] Version updates

## 🎓 Training Materials

Create for end-users:

1. **Quick Start Guide** - 5 min overview
2. **Data Preparation** - How to format input files
3. **Results Interpretation** - Understanding KPIs and alerts
4. **Troubleshooting** - Common issues and fixes

---

**Ready to deploy?** Follow this guide step-by-step for a smooth production launch!
