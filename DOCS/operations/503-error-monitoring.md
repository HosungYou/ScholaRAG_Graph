# 503 Error Monitoring Guide

> **PERF-004**: 503 에러 모니터링 설정 가이드
> **Last Updated**: 2026-01-20

## Overview

이 문서는 ScholaRAG_Graph 백엔드의 503 에러 모니터링 시스템 설정 방법을 설명합니다.

### 503 에러의 일반적인 원인

1. **Database Connection Pool Exhaustion**: DB 연결 풀이 고갈된 경우
2. **Service Unavailable**: 배포 중이거나 서비스 재시작 중
3. **Resource Limits Exceeded**: 메모리/CPU 한도 초과
4. **Cold Start Issues**: 서버리스 환경에서의 콜드 스타트

---

## Error Metrics API Endpoints

### 1. General Error Metrics

```bash
GET /api/system/metrics/errors
```

**Response**:
```json
{
  "total_errors": 42,
  "error_counts": {"503": 5, "500": 3, "404": 34},
  "errors_by_path": {"/api/chat": 3, "/api/graph/123": 2},
  "avg_response_time_ms": 245.5,
  "last_error_time": "2026-01-20T10:30:00Z",
  "alert_triggered": false
}
```

### 2. Error Rate (Time Window)

```bash
GET /api/system/metrics/error-rate?window=300
```

**Parameters**:
- `window`: Time window in seconds (60-3600, default: 300)

**Response**:
```json
{
  "window_seconds": 300,
  "total_errors_in_window": 3,
  "error_counts": {"503": 2, "500": 1},
  "errors_per_minute": 0.6,
  "count_503": 2,
  "count_5xx": 3,
  "count_4xx": 0
}
```

### 3. 503 Error Analysis

```bash
GET /api/system/metrics/503
```

**Response**:
```json
{
  "total_503_errors": 5,
  "recent_503_count": 2,
  "rate_per_minute_5min": 0.4,
  "last_503_time": "2026-01-20T10:25:00Z",
  "seconds_since_last_503": 300.5,
  "paths_affected": ["/api/chat", "/api/graph/visualization/123"],
  "uptime_seconds": 86400.0,
  "alert_triggered": false
}
```

### 4. Recent Errors

```bash
GET /api/system/metrics/recent-errors?limit=20
```

**Response**:
```json
{
  "count": 3,
  "errors": [
    {
      "timestamp": "2026-01-20T10:30:00Z",
      "status_code": 503,
      "method": "GET",
      "path": "/api/chat",
      "response_time_ms": 30045.5,
      "error_detail": "Service temporarily unavailable"
    }
  ]
}
```

---

## Render Log Monitoring

### Log Pattern for 503 Errors

503 에러가 발생하면 다음 형식으로 로그가 기록됩니다:

```
[503_ERROR] path=/api/chat method=POST response_time_ms=30045.50 detail=Service temporarily unavailable
```

### Render Dashboard에서 로그 검색

1. **Render Dashboard** → **scholarag-graph-docker** → **Logs**
2. 검색창에 `503_ERROR` 입력
3. 시간 범위 선택 (Last 1 hour, Last 24 hours 등)

### Log Stream Filter

```bash
# Render CLI를 사용한 로그 스트리밍
render logs --service scholarag-graph-docker --filter "503_ERROR"
```

---

## Render Alert Configuration

### Step 1: Alert Rules 생성

1. **Render Dashboard** → **Settings** → **Notifications**
2. **Create Alert Rule** 클릭

### Step 2: Log-based Alert 설정

| Setting | Value |
|---------|-------|
| Alert Name | `503 Error Spike Alert` |
| Type | Log Pattern |
| Pattern | `503_ERROR` |
| Threshold | 5 occurrences |
| Time Window | 5 minutes |
| Notification | Email / Slack |

### Step 3: Health Check Alert 설정

| Setting | Value |
|---------|-------|
| Alert Name | `Backend Health Check Failed` |
| Type | Health Check |
| Endpoint | `/health` |
| Expected Status | 200 |
| Interval | 30 seconds |
| Failures Before Alert | 3 |

---

## External Monitoring (Optional)

### UptimeRobot 설정

1. **New Monitor** 생성
2. **Monitor Type**: HTTP(s)
3. **URL**: `https://scholarag-graph-docker.onrender.com/api/system/metrics/503`
4. **Monitoring Interval**: 5 minutes
5. **Alert Contacts**: Email 추가

### Custom Alert Script

```python
#!/usr/bin/env python3
"""
503 Error Alert Script
Run via cron every 5 minutes
"""
import requests
import smtplib
from email.message import EmailMessage

API_URL = "https://scholarag-graph-docker.onrender.com/api/system/metrics/503"
ALERT_THRESHOLD = 5  # Alert if 5+ 503 errors in 5 minutes

def check_503_errors():
    response = requests.get(API_URL, timeout=30)
    data = response.json()

    if data["recent_503_count"] >= ALERT_THRESHOLD:
        send_alert(data)

def send_alert(data):
    msg = EmailMessage()
    msg["Subject"] = f"[ALERT] ScholaRAG 503 Errors: {data['recent_503_count']} in 5min"
    msg["From"] = "alerts@yourdomain.com"
    msg["To"] = "admin@yourdomain.com"
    msg.set_content(f"""
503 Error Alert Triggered!

Total 503 Errors: {data['total_503_errors']}
Recent Count (5min): {data['recent_503_count']}
Rate: {data['rate_per_minute_5min']}/min
Last Error: {data['last_503_time']}
Affected Paths: {', '.join(data['paths_affected'])}
    """)

    # Send email (configure SMTP settings)
    # with smtplib.SMTP("smtp.example.com") as smtp:
    #     smtp.send_message(msg)
    print(f"ALERT: {msg['Subject']}")

if __name__ == "__main__":
    check_503_errors()
```

---

## Grafana/Prometheus Integration (Advanced)

### Prometheus Metrics Endpoint

향후 `/metrics` 엔드포인트 추가 시:

```
# HELP http_errors_total Total HTTP errors by status code
# TYPE http_errors_total counter
http_errors_total{status_code="503"} 5
http_errors_total{status_code="500"} 3

# HELP http_error_rate_per_minute HTTP errors per minute
# TYPE http_error_rate_per_minute gauge
http_error_rate_per_minute{status_code="503"} 0.4
```

### Grafana Alert Rule

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - /etc/prometheus/alert.rules.yml

# alert.rules.yml
groups:
  - name: scholarag
    rules:
      - alert: High503ErrorRate
        expr: http_error_rate_per_minute{status_code="503"} > 1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High 503 error rate detected"
          description: "503 error rate is {{ $value }}/min"
```

---

## Troubleshooting 503 Errors

### Database Connection Issues

```bash
# Check DB connection pool status
curl https://scholarag-graph-docker.onrender.com/health | jq '.database'

# Expected: "connected"
# If "disconnected", check:
# 1. DATABASE_URL environment variable
# 2. Supabase service status
# 3. Connection pool settings
```

### Memory/CPU Issues

Render Dashboard에서 확인:
1. **Metrics** 탭 → **Memory Usage**
2. **Metrics** 탭 → **CPU Usage**

80% 이상이면 플랜 업그레이드 고려

### Cold Start Issues

Render free tier는 15분 비활동 후 sleep 상태로 전환됩니다.

**해결방법**:
1. Paid plan 업그레이드 (sleep 없음)
2. UptimeRobot으로 5분마다 health check ping

---

## Quick Reference

| Endpoint | Purpose |
|----------|---------|
| `/api/system/metrics/errors` | 전체 에러 요약 |
| `/api/system/metrics/error-rate` | 시간 윈도우별 에러율 |
| `/api/system/metrics/503` | 503 에러 상세 분석 |
| `/api/system/metrics/recent-errors` | 최근 에러 목록 |
| `/health` | 기본 헬스 체크 |

| Log Pattern | Meaning |
|-------------|---------|
| `[503_ERROR]` | 503 Service Unavailable |
| `[500_ERROR]` | Internal Server Error |
| `[5XX_ERROR]` | Any 5xx error |
