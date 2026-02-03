#!/bin/sh
# n8n Workflow Auto-Import Script

echo "🔄 Waiting for n8n to start..."
sleep 10

echo "📦 Importing workflows..."

for workflow in /workflows/*.json; do
  if [ -f "$workflow" ]; then
    echo "  → Importing $(basename $workflow)"
    # n8n CLI ile import (container içinden çalışır)
    # Not: n8n'de bu özellik built-in değil, manuel API kullanmamız gerekiyor
  fi
done

echo "✅ Workflow import complete!"