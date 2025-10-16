# 🚀 Production Deployment Guide

## Quick Start - Railway (Recommended)

### 1. Prepare Your Code
```bash
# Ensure all files are committed
git add .
git commit -m "Ready for production deployment"
```

### 2. Deploy to Railway
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway will automatically detect it's a Python app

### 3. Configure Environment Variables
In Railway dashboard, go to Variables tab and add:

```env
ULTRAMSG_API_URL=https://api.ultramsg.com/instance146348/
ULTRAMSG_INSTANCE_ID=instance146348
ULTRAMSG_TOKEN=your_actual_token
MY_PHONE_NUMBER=5530386114
OPENAI_API_KEY=your_openai_key
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json
EMAIL_DOMAIN_FILTER=@binara.pro
```

### 4. Upload Google API Files
- Upload `credentials.json` and `token.json` to Railway
- Or use Railway's file upload feature

### 5. Get Your Production URL
Railway will give you a URL like: `https://your-app-name.railway.app`

---

## Alternative: Heroku Deployment

### 1. Install Heroku CLI
```bash
# Install Heroku CLI from https://devcenter.heroku.com/articles/heroku-cli
```

### 2. Deploy
```bash
# Login to Heroku
heroku login

# Create app
heroku create your-whatsapp-assistant

# Set environment variables
heroku config:set ULTRAMSG_API_URL="https://api.ultramsg.com/instance146348/"
heroku config:set ULTRAMSG_INSTANCE_ID="instance146348"
heroku config:set ULTRAMSG_TOKEN="your_token"
heroku config:set MY_PHONE_NUMBER="5530386114"
heroku config:set OPENAI_API_KEY="your_key"

# Deploy
git push heroku main
```

---

## Alternative: DigitalOcean App Platform

### 1. Create App
1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click "Create App"
3. Connect your GitHub repository
4. Select "Web Service"

### 2. Configure
- **Build Command**: `pip install -r requirements.txt`
- **Run Command**: `python production.py`
- **HTTP Port**: `8000`

### 3. Environment Variables
Add all the same environment variables as above.

---

## Configure Webhooks

### 1. UltraMsg Webhook Configuration
1. Go to your UltraMsg dashboard
2. Set webhook URL to: `https://your-domain.com/whatsapp-webhook`
3. Enable webhook notifications

### 2. Gmail Push Notifications (Optional)
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Enable Gmail API
3. Set up push notifications to: `https://your-domain.com/gmail-webhook`

---

## Testing Production

### 1. Health Check
```bash
curl https://your-domain.com/health
```

### 2. Test WhatsApp Webhook
```bash
curl -X POST https://your-domain.com/whatsapp-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "id": "test_001",
      "from": "5530386114",
      "to": "5664087506",
      "body": "test message",
      "type": "text",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  }'
```

### 3. Test Email Flow
Send a WhatsApp message: "Envíame un correo a test@example.com preguntando si está disponible para una reunión mañana a las 2 p.m."

---

## Monitoring & Maintenance

### 1. Logs
- Railway: View logs in dashboard
- Heroku: `heroku logs --tail`
- DigitalOcean: View in app dashboard

### 2. Health Monitoring
- Set up uptime monitoring (UptimeRobot, Pingdom)
- Monitor the `/health` endpoint

### 3. Backup
- Google API tokens are stored in files
- Email tracking data is in `data/sent_emails.json`
- Regular backups recommended

---

## Security Considerations

### 1. Environment Variables
- Never commit `.env` files
- Use strong, unique tokens
- Rotate API keys regularly

### 2. Webhook Security
- Consider adding webhook signature verification
- Use HTTPS only
- Implement rate limiting

### 3. Data Privacy
- Email content is processed by OpenAI
- Consider data retention policies
- Implement user consent mechanisms

---

## Troubleshooting

### Common Issues

1. **Webhook not receiving messages**
   - Check UltraMsg webhook URL configuration
   - Verify HTTPS is working
   - Check server logs

2. **Gmail API errors**
   - Verify credentials.json and token.json are uploaded
   - Check Gmail API is enabled
   - Verify OAuth scopes

3. **OpenAI API errors**
   - Check API key is valid
   - Verify billing is set up
   - Check rate limits

### Debug Commands
```bash
# Check server status
curl https://your-domain.com/status

# View recent logs
# (Use your platform's log viewing method)
```

---

## Cost Estimation

### Railway
- **Hobby Plan**: $5/month
- **Pro Plan**: $20/month

### Heroku
- **Eco Plan**: $5/month
- **Basic Plan**: $7/month

### DigitalOcean
- **Basic Plan**: $5/month
- **Professional Plan**: $12/month

### Additional Costs
- **OpenAI API**: ~$5-20/month (depending on usage)
- **UltraMsg**: Based on message volume
- **Domain**: $10-15/year (optional)

---

## Next Steps

1. **Choose a platform** (Railway recommended for simplicity)
2. **Deploy your app**
3. **Configure webhooks**
4. **Test the complete flow**
5. **Set up monitoring**
6. **Go live!** 🎉
