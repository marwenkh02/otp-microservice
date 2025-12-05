# Render Deployment Guide for OTP Project

This guide will help you deploy your OTP Project to Render (Free Tier).

## Prerequisites

1. A GitHub account
2. A Render account (sign up at https://render.com)
3. Your project pushed to a GitHub repository

## Step 1: Prepare Your Repository

### 1.1 Push Your Code to GitHub

```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### 1.2 Verify Required Files

Make sure these files exist:
- `backend/.env.example`
- `backend/Dockerfile`
- `frontend/.env.local.example`
- `frontend/Dockerfile`
- `frontend/next.config.ts`

## Step 2: Deploy PostgreSQL Database on Render

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"PostgreSQL"**
3. Configure:
   - **Name**: `otp-project-db` (or your preferred name)
   - **Database**: `otp_project`
   - **User**: `openpam` (or your preferred user)
   - **Region**: Choose closest to you
   - **PostgreSQL Version**: 15
   - **Plan**: Free (or paid if needed)
4. Click **"Create Database"**
5. **IMPORTANT**: Copy the **Internal Database URL** - you'll need this!

## Step 3: Deploy Backend on Render

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `otp-project-backend`
   - **Region**: Same as database
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Environment**: `Docker`
   - **Dockerfile Path**: `Dockerfile` (should auto-detect)
   - **Docker Context**: `backend`
   - **Start Command**: (leave empty, Dockerfile handles this)

5. **Environment Variables** - Add these:
   ```
   DATABASE_URL=<paste-internal-database-url-from-step-2>
   ENCRYPTION_KEY=<generate-using-python-command-below>
   SECRET_KEY=<generate-a-random-secret-key>
   ENVIRONMENT=production
   CORS_ORIGINS=https://your-frontend.onrender.com,https://your-frontend.vercel.app
   BACKEND_URL=https://otp-project-backend.onrender.com
   ```

   **Generate ENCRYPTION_KEY:**
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   **Generate SECRET_KEY:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

6. Click **"Create Web Service"**

7. **Wait for deployment** - First deployment takes 5-10 minutes

8. **Copy the service URL** - You'll need this for frontend (e.g., `https://otp-project-backend.onrender.com`)

## Step 4: Run Database Migrations

After backend is deployed:

1. Go to your backend service on Render
2. Click **"Shell"** tab
3. Run migrations:
   ```bash
   alembic upgrade head
   ```

## Step 5: Deploy Frontend on Render (or Vercel)

### Option A: Deploy on Render

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `otp-project-frontend`
   - **Region**: Same as backend
   - **Branch**: `main`
   - **Root Directory**: `frontend`
   - **Environment**: `Docker`
   - **Dockerfile Path**: `Dockerfile`
   - **Docker Context**: `frontend`

5. **Environment Variables**:
   ```
   NEXT_PUBLIC_BACKEND_URL=https://otp-project-backend.onrender.com
   NODE_ENV=production
   ```

6. Click **"Create Web Service"**

### Option B: Deploy on Vercel (Recommended for Next.js)

1. Go to https://vercel.com
2. Import your GitHub repository
3. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`

4. **Environment Variables**:
   ```
   NEXT_PUBLIC_BACKEND_URL=https://otp-project-backend.onrender.com
   NODE_ENV=production
   ```

5. Click **"Deploy"**

6. **Update CORS in Backend**: After getting frontend URL, update backend CORS_ORIGINS:
   ```
   CORS_ORIGINS=https://your-frontend.vercel.app,https://your-frontend.onrender.com
   ```

## Step 6: Update Backend CORS After Frontend Deployment

1. Go to your backend service on Render
2. Go to **"Environment"** tab
3. Update `CORS_ORIGINS` to include your frontend URL:
   ```
   CORS_ORIGINS=https://your-frontend-url.vercel.app,https://your-frontend-url.onrender.com,http://localhost:3000
   ```
4. Click **"Save Changes"** - This will trigger a redeploy

## Step 7: Create Admin User

After everything is deployed:

1. Use the signup endpoint to create a user:
   ```bash
   curl -X POST https://otp-project-backend.onrender.com/users/ \
     -H "Content-Type: application/json" \
     -d '{
       "username": "admin",
       "email": "admin@example.com",
       "password": "SecurePass123!@#",
       "department": "IT",
       "job_title": "Administrator"
     }'
   ```

2. Connect to database and make user admin:
   - Go to Render dashboard → Your PostgreSQL service
   - Click **"Connect"** → **"psql"**
   - Run:
     ```sql
     UPDATE users SET is_admin = true WHERE username = 'admin';
     ```

## Troubleshooting

### Backend Won't Start

1. Check logs in Render dashboard
2. Verify all environment variables are set
3. Check DATABASE_URL is correct (use Internal Database URL)
4. Ensure migrations have run

### Frontend Can't Connect to Backend

1. Verify `NEXT_PUBLIC_BACKEND_URL` is set correctly
2. Check CORS_ORIGINS includes your frontend URL
3. Check browser console for CORS errors
4. Verify backend is running (check health endpoint)

### Database Connection Errors

1. Use **Internal Database URL** (not External)
2. Verify database is running
3. Check DATABASE_URL format is correct
4. Ensure database user has proper permissions

### Build Failures

1. Check Dockerfile syntax
2. Verify all dependencies in requirements.txt/package.json
3. Check build logs for specific errors
4. Ensure Node.js/Python versions match Dockerfile

## Render Free Tier Limitations

- **Spins down after 15 minutes** of inactivity
- **Cold start** takes 30-60 seconds
- **Limited to 750 hours/month** (enough for always-on if single service)
- **512MB RAM** per service

## Production Recommendations

1. **Use paid tier** for production (stays always-on)
2. **Set up monitoring** and alerts
3. **Use environment-specific secrets**
4. **Enable HTTPS** (automatic on Render)
5. **Set up database backups**
6. **Use CDN** for frontend static assets
7. **Implement rate limiting** (already in code)
8. **Set up logging** aggregation

## Environment Variables Summary

### Backend (.env on Render)
```
DATABASE_URL=<render-postgres-internal-url>
ENCRYPTION_KEY=<fernet-key>
SECRET_KEY=<jwt-secret>
ENVIRONMENT=production
CORS_ORIGINS=<frontend-urls>
BACKEND_URL=<backend-url>
```

### Frontend (.env.local on Render/Vercel)
```
NEXT_PUBLIC_BACKEND_URL=<backend-url>
NODE_ENV=production
```

## Quick Reference URLs

After deployment, you'll have:
- **Backend API**: `https://otp-project-backend.onrender.com`
- **Frontend**: `https://otp-project-frontend.onrender.com` or `https://your-app.vercel.app`
- **API Docs**: `https://otp-project-backend.onrender.com/docs`
- **Health Check**: `https://otp-project-backend.onrender.com/health`

## Next Steps

1. Test all endpoints
2. Create admin user
3. Set up monitoring
4. Configure custom domain (optional)
5. Set up CI/CD for automatic deployments

Good luck with your deployment! 🚀

