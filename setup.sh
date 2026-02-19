#!/bin/bash

echo "======================================"
echo "TradeAI - Setup Script"
echo "======================================"
echo ""

# Check Python installation
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Found Python $PYTHON_VERSION"

# Check Node.js installation
echo "Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 14 or higher."
    exit 1
fi

NODE_VERSION=$(node --version)
echo "✓ Found Node.js $NODE_VERSION"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Python dependencies"
    exit 1
fi
echo "✓ Python dependencies installed"

# Install Frontend dependencies
echo ""
echo "Installing Frontend dependencies..."
cd frontend
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install frontend dependencies"
    exit 1
fi
cd ..
echo "✓ Frontend dependencies installed"

# Install Desktop dependencies
echo ""
echo "Installing Desktop (Electron) dependencies..."
cd ../desktop
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install desktop dependencies"
    exit 1
fi
cd ..
echo "✓ Desktop dependencies installed"

echo ""
echo "======================================"
echo "✓ Setup Complete!"
echo "======================================"
echo ""
echo "To start the application:"
echo ""
echo "1. Start as desktop app (recommended):"
echo "   npm run desktop"
echo ""
echo "2. Or start in dev mode (two terminals):"
echo "   Terminal 1: python backend/app.py"
echo "   Terminal 2: cd frontend && npm start"
echo "   Terminal 3: npm run desktop:dev"
echo ""
echo "The application will be available at:"
echo "   Backend API: http://127.0.0.1:5055"
echo ""
