#!/bin/bash
# claude-radar launchd 크론 설치/재설치 (멱등).
# 스케줄: 매일 09:30 (머신 로컬 타임존).
#
# 포터블: vault·홈 경로를 설치 시점에 계산해 plist를 생성한다 — 하드코딩 없음.
# 다른 머신으로 vault를 옮기면 이 스크립트만 다시 실행하면 된다.
#
# 제거:
#   launchctl bootout "gui/$(id -u)/com.$(id -un).claude-radar"
#   rm "$HOME/Library/LaunchAgents/com.$(id -un).claude-radar.plist"

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT="$(dirname "$SCRIPT_DIR")"
WRAPPER="$VAULT/.claude/claude-radar-cron.sh"
LOG="$VAULT/.claude/runtime/radar-cron.log"
LABEL="com.$(id -un).claude-radar"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

[ -f "$WRAPPER" ] || { echo "FAIL: wrapper not found: $WRAPPER"; exit 1; }

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$WRAPPER</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <!-- 주 1회 수요일 09:33 (2026-08-23 일1회->주1회, 아키텍처 P0-5. 래퍼 SLOT_EPOCH과 일치 필수) -->
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>3</integer>
    <key>Hour</key><integer>9</integer>
    <key>Minute</key><integer>33</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>$LOG</string>
  <key>StandardErrorPath</key>
  <string>$LOG</string>
</dict>
</plist>
EOF

# 기존 등록이 있으면 내리고 다시 올린다 (재설치 멱등성)
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl list | grep -q "$LABEL" && echo "installed: $LABEL (weekly Wed 09:33 local) wrapper=$WRAPPER" || { echo "FAIL: not registered"; exit 1; }
