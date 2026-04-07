#!/bin/bash
# Test common legacy job URLs to see if they exist and redirect properly

echo "🔍 Testing Legacy Job URLs (1-20)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

found_redirects=()
found_404s=()
found_200s=()
found_errors=()

for i in {1..20}; do
  url="https://careerguidance.me/job/$i"
  
  # Get status code and location header
  response=$(curl -s -I "$url" 2>&1)
  status=$(echo "$response" | grep -i "^HTTP" | tail -1 | awk '{print $2}')
  location=$(echo "$response" | grep -i "^location:" | awk '{print $2}' | tr -d '\r')
  
  if [ "$status" = "301" ] || [ "$status" = "302" ]; then
    echo "✅ /job/$i → Redirects ($status) to: $location"
    found_redirects+=("$i")
  elif [ "$status" = "404" ]; then
    echo "❌ /job/$i → Not found (404)"
    found_404s+=("$i")
  elif [ "$status" = "200" ]; then
    echo "⚠️  /job/$i → Returns 200 (should redirect!)"
    found_200s+=("$i")
  else
    echo "❓ /job/$i → Status: $status"
    found_errors+=("$i")
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Summary:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Redirecting properly: ${#found_redirects[@]} URLs"
echo "❌ Not found (404): ${#found_404s[@]} URLs"
echo "⚠️  Returning 200: ${#found_200s[@]} URLs"
echo "❓ Errors: ${#found_errors[@]} URLs"
echo ""

if [ ${#found_redirects[@]} -gt 0 ]; then
  echo "🎯 URLs to request removal in GSC:"
  for i in "${found_redirects[@]}"; do
    echo "   https://careerguidance.me/job/$i"
  done
  echo ""
  echo "📝 Then request indexing of canonical versions:"
  for i in "${found_redirects[@]}"; do
    echo "   https://careerguidance.me/job/main/$i"
  done
fi

echo ""
echo "✅ Test complete!"
