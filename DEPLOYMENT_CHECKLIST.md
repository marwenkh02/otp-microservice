# Deployment Checklist

## ✅ Completed Preparations

### Backend Configuration
- [x] Created `backend/.env.example` with production configuration
- [x] Updated `backend/app/main.py` for configurable CORS from environment variables
- [x] Updated `backend/app/auth.py` to load SECRET_KEY from environment
- [x] Updated `backend/Dockerfile` for production (Python 3.11, non-root user, optimized)

### Frontend Configuration
- [x] Created `frontend/.env.local.example` with production configuration
- [x] Updated `frontend/next.config.ts` for standalone output and production settings
- [x] Updated `frontend/Dockerfile` for production (multi-stage build, optimized)
- [x] Replaced all hardcoded `localhost:8000` URLs with `NEXT_PUBLIC_BACKEND_URL` environment variable
- [x] Updated all API calls to use environment variable:
  - `dashboard/page.tsx`
  - `admin/page.tsx`
  - `audit/page.tsx`
  - `otp/configs/page.tsx`
  - `otp/generate/[id]/page.tsx`
  - `otp/validate/[id]/page.tsx`
  - `api/auth/route.ts`

### Documentation
- [x] Created `RENDER_DEPLOYMENT_GUIDE.md` with step-by-step instructions

## 📋 Pre-Deployment Checklist

### Before Deploying to Render

1. **Generate Secrets**
   ```bash
   # Generate ENCRYPTION_KEY
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   
   # Generate SECRET_KEY
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Test Locally**
   - [ ] Test backend with production environment variables
   - [ ] Test frontend with production backend URL
   - [ ] Verify all API calls work
   - [ ] Test CORS configuration

3. **Database Setup**
   - [ ] Create PostgreSQL database on Render
   - [ ] Copy Internal Database URL
   - [ ] Test database connection

4. **Environment Variables Ready**
   - [ ] Backend: DATABASE_URL, ENCRYPTION_KEY, SECRET_KEY, CORS_ORIGINS, BACKEND_URL
   - [ ] Frontend: NEXT_PUBLIC_BACKEND_URL

## 🚀 Deployment Steps

1. **Deploy PostgreSQL** (Render)
   - Create PostgreSQL service
   - Copy Internal Database URL

2. **Deploy Backend** (Render)
   - Connect GitHub repository
   - Set root directory to `backend`
   - Use Docker environment
   - Add all environment variables
   - Deploy

3. **Run Migrations**
   - Use Render Shell to run: `alembic upgrade head`

4. **Deploy Frontend** (Render or Vercel)
   - Connect GitHub repository
   - Set root directory to `frontend`
   - Use Docker environment (Render) or Next.js preset (Vercel)
   - Add environment variables
   - Deploy

5. **Update CORS**
   - Update backend CORS_ORIGINS with frontend URL
   - Redeploy backend

6. **Create Admin User**
   - Use signup endpoint
   - Update database to set is_admin = true

## 🔍 Post-Deployment Verification

- [ ] Backend health check: `https://your-backend.onrender.com/health`
- [ ] API docs accessible: `https://your-backend.onrender.com/docs`
- [ ] Frontend loads correctly
- [ ] Can login/signup
- [ ] Can create OTP configs
- [ ] Can generate OTPs
- [ ] Can validate OTPs
- [ ] Admin panel accessible (if admin user created)
- [ ] CORS working (no errors in browser console)

## 📝 Files Modified

### Backend
- `backend/.env.example` (created)
- `backend/app/main.py` (CORS configuration)
- `backend/app/auth.py` (SECRET_KEY from env)
- `backend/Dockerfile` (production optimized)

### Frontend
- `frontend/.env.local.example` (created)
- `frontend/next.config.ts` (standalone output)
- `frontend/Dockerfile` (multi-stage production build)
- `frontend/src/app/dashboard/page.tsx` (env variable)
- `frontend/src/app/admin/page.tsx` (env variable)
- `frontend/src/app/audit/page.tsx` (env variable)
- `frontend/src/app/otp/configs/page.tsx` (env variable)
- `frontend/src/app/otp/generate/[id]/page.tsx` (env variable)
- `frontend/src/app/otp/validate/[id]/page.tsx` (env variable)
- `frontend/src/app/api/auth/route.ts` (env variable)

### Documentation
- `RENDER_DEPLOYMENT_GUIDE.md` (created)
- `DEPLOYMENT_CHECKLIST.md` (this file)

## ⚠️ Important Notes

1. **Never commit `.env` files** - They're in `.gitignore`
2. **Use Internal Database URL** on Render (not External)
3. **Update CORS_ORIGINS** after frontend deployment
4. **Generate new secrets** for production (don't use examples)
5. **Test thoroughly** before going live
6. **Monitor logs** after deployment

## 🎯 Next Steps

1. Follow `RENDER_DEPLOYMENT_GUIDE.md` for detailed instructions
2. Deploy services one by one
3. Test each service after deployment
4. Update documentation with your actual URLs
5. Set up monitoring and alerts

Good luck with your deployment! 🚀

