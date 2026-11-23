#!/usr/bin/env bash
echo "=========================================================="
echo "Checking Fleet Control Tower Native Environment Status..."
echo "=========================================================="

echo -n "1. Checking Python 3..."
if command -v python3 &> /dev/null; then
    echo " OK ($(python3 --version))"
else
    echo " MISSING"
fi

echo -n "2. Checking Node.js..."
if command -v node &> /dev/null; then
    echo " OK ($(node --version))"
else
    echo " MISSING"
fi

echo -n "3. Checking PostgreSQL Linux Service (Port 5432)..."
if command -v pg_isready &> /dev/null; then
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        echo " ONLINE"
    else
        echo " SERVICE DOWN (PostgreSQL not listening on 5432)"
    fi
else
    echo " pg_isready tool not installed"
fi

echo -n "4. Checking Redis Linux Service (Port 6379)..."
if command -v redis-cli &> /dev/null; then
    if redis-cli -h localhost -p 6379 ping | grep PONG &> /dev/null; then
        echo " ONLINE"
    else
        echo " SERVICE DOWN (Redis not listening on 6379)"
    fi
else
    echo " redis-cli tool not installed"
fi

echo "=========================================================="
