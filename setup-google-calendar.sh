#!/bin/bash
# Google Calendar Setup Helper for Bella V3

echo "🔧 Bella V3 - Google Calendar Integration Setup"
echo "=============================================="
echo

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    touch .env
fi

echo "📋 Current Configuration:"
echo "GOOGLE_CALENDAR_ENABLED=$(grep GOOGLE_CALENDAR_ENABLED .env 2>/dev/null || echo 'not set')"
echo "GOOGLE_SERVICE_ACCOUNT_JSON=$(grep GOOGLE_SERVICE_ACCOUNT_JSON .env 2>/dev/null | cut -d'=' -f1 || echo 'not set')"
echo "GOOGLE_CALENDAR_ID=$(grep GOOGLE_CALENDAR_ID .env 2>/dev/null || echo 'not set')"
echo "BUSINESS_EMAIL=$(grep BUSINESS_EMAIL .env 2>/dev/null || echo 'not set')"
echo

echo "🚀 Quick Setup Options:"
echo "1. Enable Google Calendar (set GOOGLE_CALENDAR_ENABLED=true)"
echo "2. Add Service Account JSON (requires Google Cloud setup)"
echo "3. Set Calendar ID (optional - defaults to 'primary')"
echo "4. Set Business Email"
echo "5. Test Integration"
echo "6. View Setup Instructions"
echo

read -p "Choose option (1-6): " choice

case $choice in
    1)
        echo "✅ Enabling Google Calendar..."
        # Remove existing line and add new one
        grep -v "GOOGLE_CALENDAR_ENABLED" .env > .env.tmp && mv .env.tmp .env
        echo "GOOGLE_CALENDAR_ENABLED=true" >> .env
        echo "✅ Google Calendar enabled in .env"
        ;;
    2)
        echo "📋 Service Account JSON Setup:"
        echo "1. Go to https://console.cloud.google.com/"
        echo "2. Create project: bella-voice-booking"
        echo "3. Enable Google Calendar API"
        echo "4. Create Service Account: bella-calendar"
        echo "5. Download JSON key"
        echo
        read -p "Paste your service account JSON (single line): " json_content
        if [ ! -z "$json_content" ]; then
            grep -v "GOOGLE_SERVICE_ACCOUNT_JSON" .env > .env.tmp && mv .env.tmp .env
            echo "GOOGLE_SERVICE_ACCOUNT_JSON='$json_content'" >> .env
            echo "✅ Service Account JSON added to .env"
        fi
        ;;
    3)
        read -p "Enter Calendar ID (or press Enter for 'primary'): " calendar_id
        calendar_id=${calendar_id:-primary}
        grep -v "GOOGLE_CALENDAR_ID" .env > .env.tmp && mv .env.tmp .env
        echo "GOOGLE_CALENDAR_ID=$calendar_id" >> .env
        echo "✅ Calendar ID set to: $calendar_id"
        ;;
    4)
        read -p "Enter your business email: " email
        if [ ! -z "$email" ]; then
            grep -v "BUSINESS_EMAIL" .env > .env.tmp && mv .env.tmp .env
            echo "BUSINESS_EMAIL=$email" >> .env
            echo "✅ Business email set to: $email"
        fi
        ;;
    5)
        echo "🧪 Testing Google Calendar Integration..."
        python test_google_calendar.py
        ;;
    6)
        python google-calendar-setup.py
        ;;
    *)
        echo "❌ Invalid option"
        ;;
esac

echo
echo "📁 Current .env configuration:"
grep -E "(GOOGLE_|BUSINESS_)" .env 2>/dev/null || echo "No Google Calendar settings found"
echo
echo "🔄 Restart your Bella service to apply changes:"
echo "   uvicorn app.main:app --reload"