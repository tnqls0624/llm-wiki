#!/bin/bash
# study-coach launchd 크론 설치/재설치 (멱등).
# 스케줄: 매일 08:07 (머신 로컬 타임존 — kb-sync 09:07·radar 09:17보다 이른 아침에 검토+브리핑).
#
# 멀티 머신: 학습하는 각 Mac에서 이 스크립트를 실행한다. 회사 Mac에서 무인 검토를
# 돌리고 싶지 않으면 그 Mac에서는 설치하지 말고 /study-coach review를 수동 실행하면 된다.
# (진도 state는 vault git으로 공유되므로 어느 Mac이 검토하든 결과는 양쪽에 반영됨.)
#
# 포터블: vault·홈 경로를 설치 시점에 계산해 plist를 생성한다 — 하드코딩 없음.
# 제거:
#   launchctl bootout "gui/$(id -u)/com.$(id -un).study-coach"
#   rm "$HOME/Library/LaunchAgents/com.$(id -un).study-coach.plist"

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT="$(dirname "$SCRIPT_DIR")"
WRAPPER="$VAULT/.claude/study-coach-cron.sh"
LOG="$VAULT/.claude/runtime/study-cron.log"
LABEL="com.$(id -un).study-coach"
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
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>8</integer>
    <key>Minute</key><integer>7</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>$LOG</string>
  <key>StandardErrorPath</key>
  <string>$LOG</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl list | grep -q "$LABEL" && echo "installed: $LABEL (daily 08:07 local) wrapper=$WRAPPER" || { echo "FAIL: not registered"; exit 1; }
