# DEPLOYMENT GUIDE - RAILWAY

## Prerequisites

1. **Railway Account**: Sign up at https://railway.app
2. **GitHub Repository**: Push your code to GitHub
3. **Python 3.12**: Ensure runtime compatibility

---

## Quick Deploy to Railway

### Method 1: GitHub Integration (Recommended)

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit - Multi-Sport Prediction Platform"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin master
   ```

2. **Connect to Railway**:
   - Go to https://railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Railway will auto-detect Python and deploy

3. **Configure Environment**:
   - Railway will automatically use `railway.json` configuration
   - Set environment variables if needed (none required for basic setup)

4. **Deploy**:
   - Railway will automatically build and deploy
   - You'll get a public URL like: `your-app.up.railway.app`

### Method 2: Railway CLI

1. **Install Railway CLI**:
   ```bash
   npm install -g @railway/cli
   ```

2. **Login**:
   ```bash
   railway login
   ```

3. **Initialize Project**:
   ```bash
   railway init
   ```

4. **Deploy**:
   ```bash
   railway up
   ```

5. **Open Deployment**:
   ```bash
   railway open
   ```

---

## Configuration Files

### `railway.json`
- Defines build and deployment settings
- Specifies start command: `python api/unified_api.py`
- Configured for automatic restarts on failure

### `Procfile`
- Backup configuration for web process
- Railway uses this if `railway.json` not found

### `runtime.txt`
- Specifies Python version (3.12.0)

### `.railway-ignore`
- Excludes large data files from deployment
- Keeps deployment size small

---

## Environment Variables (Optional)

If needed, set these in Railway dashboard:

```
PORT=5000
FLASK_ENV=production
FLASK_DEBUG=False
```

Railway automatically sets `PORT` - your app will use it.

---

## Post-Deployment Steps

### 1. Verify Deployment

Visit your Railway URL and check:
- Homepage loads: `https://your-app.up.railway.app/`
- API status: `https://your-app.up.railway.app/api/status`
- Sports list: `https://your-app.up.railway.app/api/sports`

### 2. Upload Models (Optional)

If you have trained models:

```bash
railway link
railway volume create
railway volume attach /app/models
# Upload models to volume
```

### 3. Enable Data Scraping

For automatic data updates, set up:
- Cron job or Railway scheduled task
- Run `python scrape_all_data.py` daily/weekly

### 4. Monitor

Railway dashboard shows:
- Deployment logs
- Resource usage
- Request metrics

---

## Updating Deployment

### Automatic (GitHub)
- Push to GitHub
- Railway auto-deploys on push

### Manual (CLI)
```bash
railway up
```

---

## Scaling

Railway offers automatic scaling. For high traffic:

1. Go to Railway dashboard
2. Select your project
3. Adjust resources:
   - Memory
   - CPU
   - Concurrent requests

---

## Troubleshooting

### Deployment Fails

Check Railway logs:
```bash
railway logs
```

Common issues:
- Missing dependencies → Check `requirements.txt`
- Port conflict → Railway auto-assigns port
- Import errors → Check file paths

### Models Not Loading

Models need to be trained locally first, then:
- Upload to Railway volume
- Or train on Railway (resource-intensive)

### Slow Response

- Enable Railway caching
- Optimize model loading
- Consider Redis for caching predictions

---

## Cost Optimization

Railway free tier includes:
- $5 free credits/month
- Auto-sleep after inactivity
- Wake on request

For production:
- Upgrade to paid plan (~$5-20/month)
- Add custom domain
- Enable auto-scaling

---

## Custom Domain (Optional)

1. Go to Railway dashboard
2. Select your service
3. Click "Settings" → "Domains"
4. Add your custom domain
5. Update DNS records (Railway provides instructions)

---

## Backup Strategy

Railway doesn't include backups. Set up:

1. **Code**: GitHub (already done)
2. **Models**: Download periodically or use Railway volumes
3. **Data**: External storage (AWS S3, Google Cloud Storage)

---

## Production Checklist

- [ ] Push code to GitHub
- [ ] Deploy to Railway
- [ ] Verify all endpoints work
- [ ] Test predictions (once models trained)
- [ ] Set up monitoring
- [ ] Configure custom domain (optional)
- [ ] Enable HTTPS (Railway does this automatically)
- [ ] Set up automated data updates
- [ ] Monitor costs
- [ ] Test error handling

---

## Support

- **Railway Docs**: https://docs.railway.app
- **Railway Discord**: https://discord.gg/railway
- **GitHub Issues**: Your repository issues

---

## Next Steps After Deployment

1. **Train Models**:
   - Run data scrapers locally
   - Train all sport models
   - Upload trained models to Railway

2. **Test System**:
   - Make test predictions
   - Verify accuracy
   - Check response times

3. **Go Live**:
   - Share your URL
   - Monitor usage
   - Iterate and improve

---

**Your multi-sport prediction platform is ready for the world!** 🚀
