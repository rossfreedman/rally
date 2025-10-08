#!/bin/bash
set -e

echo "🔧 Installing Python requirements with retry logic..."

# Upgrade pip first
pip install --upgrade pip setuptools wheel

# Install psycopg2-binary with retries
echo "📦 Installing psycopg2-binary..."
for i in {1..3}; do
    if pip install --no-cache-dir --timeout=300 psycopg2-binary; then
        echo "✅ psycopg2-binary installed successfully"
        break
    else
        echo "❌ Attempt $i failed, retrying..."
        if [ $i -eq 3 ]; then
            echo "💥 Failed to install psycopg2-binary after 3 attempts"
            exit 1
        fi
        sleep 5
    fi
done

# Install remaining requirements with retries
echo "📦 Installing remaining requirements..."
for i in {1..3}; do
    if pip install --no-cache-dir --timeout=300 -r requirements.txt; then
        echo "✅ All requirements installed successfully"
        break
    else
        echo "❌ Attempt $i failed, retrying..."
        if [ $i -eq 3 ]; then
            echo "💥 Failed to install requirements after 3 attempts"
            exit 1
        fi
        sleep 5
    fi
done

echo "🎉 Installation complete!"
