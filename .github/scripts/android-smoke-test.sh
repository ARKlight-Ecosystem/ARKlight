#!/usr/bin/env bash
# Installs the debug APK on the emulator started by
# reactivecircus/android-emulator-runner, launches MainActivity, and
# fails the job if the process isn't still running a few seconds
# later (i.e. it crashed on startup). See this file's own generator,
# `_android_smoke_test_sh` in arklight/backend/android/runtime.py, for
# why this logic lives in its own script rather than inline in
# android-build.yml's `script:` block.
set -euo pipefail

APK="$(find apk -name '*.apk' | head -n 1)"
if [ -z "$APK" ]; then
  echo "::error::No .apk file found under apk/ -- listing what's actually there:"
  find apk -type f
  exit 1
fi

echo "Installing $APK"
adb install -r "$APK"
adb shell am start -n com.arklight.app/com.arklight.app.MainActivity
sleep 5

if ! adb shell pidof com.arklight.app; then
  echo "::error::App process not found a few seconds after launch -- it likely crashed on startup. See logcat below."
  adb logcat -d "*:E"
  exit 1
fi

echo "App launched and is still running -- smoke test passed."
