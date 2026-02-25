
================================================================================
STEP-BY-STEP: DEPLOY TO GITHUB + STREAMLIT CLOUD
================================================================================

PART 1: PUSH TO GITHUB (5 minutes)
────────────────────────────────────────────────────────────────────────────

1. Create GitHub Repository:
   • Go to: https://github.com/new
   • Repository name: heritage-shops-forecasting
   • Description: "Inventory forecasting system for Heritage Shops"
   • Choose: Public (required for free Streamlit Cloud)
   • DON'T initialize with README (you already have one)
   • Click "Create repository"

2. Open Terminal/Command Prompt in your project folder:

   cd /path/to/your/project

3. Initialize Git (if not already):

   git init

4. Add all files:

   git add .

5. Commit:

   git commit -m "Initial commit - Heritage Shops forecasting system"

6. Connect to GitHub (replace YOUR_USERNAME):

   git remote add origin https://github.com/YOUR_USERNAME/heritage-shops-forecasting.git

7. Push to GitHub:

   git push -u origin main

   (If it says 'master' instead of 'main', use: git branch -M main)

✅ Your code is now on GitHub!

================================================================================
PART 2: DEPLOY TO STREAMLIT CLOUD (3 minutes)
────────────────────────────────────────────────────────────────────────────

1. Go to: https://streamlit.io/cloud
   • Click "Sign in" → "Continue with GitHub"
   • Authorize Streamlit

2. Click "New app" button

3. Fill in deployment settings:
   • Repository: YOUR_USERNAME/heritage-shops-forecasting
   • Branch: main
   • Main file path: app.py
   • App URL: heritage-shops-forecasting (or customize)

4. Click "Deploy!"

5. Wait 2-3 minutes for deployment...

6. Your app is LIVE! 🎉
   URL will be: https://heritage-shops-forecasting.streamlit.app
   (or your custom name)

✅ Your dashboard is now accessible from anywhere!

================================================================================
PART 3: ADD SAMPLE DATA (So app works immediately)
────────────────────────────────────────────────────────────────────────────

OPTION A: Use GitHub interface (easiest)
1. Go to your GitHub repo
2. Click "Add file" → "Upload files"
3. Upload: current_forecasts.csv (the sample data)
4. Commit changes
5. Streamlit Cloud will auto-redeploy in 1 minute

OPTION B: From terminal

   git add current_forecasts.csv
   git commit -m "Add sample forecast data"
   git push


✅ Dashboard now shows real data!

================================================================================
TROUBLESHOOTING
────────────────────────────────────────────────────────────────────────────

Problem: "File not found: current_forecasts.csv"
Solution: Upload the CSV file to GitHub (see Part 3)

Problem: "Module not found"
Solution: Make sure requirements.txt is in your repo

Problem: "App won't start"
Solution: Check Streamlit Cloud logs (click "Manage app" → "Logs")

Problem: "Private repo but want free hosting"
Solution: Make repo public OR pay for Streamlit Cloud ($10/mo)

================================================================================
UPDATING YOUR APP
────────────────────────────────────────────────────────────────────────────

Whenever you make changes:

1. Edit your files locally
2. Test locally: streamlit run app.py
3. Commit changes:

   git add .
   git commit -m "Description of changes"
   git push


4. Streamlit Cloud auto-deploys in ~1 minute!

No manual deployment needed! 🚀

================================================================================
MAKING IT PRIVATE (Optional - $10/month)
────────────────────────────────────────────────────────────────────────────

If you want to restrict access:

1. Keep GitHub repo private
2. Upgrade Streamlit Cloud: https://streamlit.io/cloud/pricing
3. Add password protection in app.py (I can show you how)

Or use Heroku/Render with authentication from the start.

================================================================================
NEXT STEPS AFTER DEPLOYMENT
────────────────────────────────────────────────────────────────────────────

1. Share URL with your team
2. Test with real users
3. Gather feedback
4. Add monthly sales data when ready
5. Watch it improve predictions!

Your system is now:
✅ Version controlled (GitHub)
✅ Deployed online (Streamlit Cloud)
✅ Automatically updated (push to deploy)
✅ Accessible from anywhere
✅ Free!
