"""
VS-9 Smart Alerts Ecosystem - Production integration adapters.

Adapters are intentionally lightweight and dependency-tolerant so the core alert
engine continues to run in local/test environments while production deployments
can enable real providers via environment variables.
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Any, Dict, List, Optional
from urllib import request
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)


@dataclass
class ProviderResult:
    """Normalized provider delivery result."""

    success: bool
    provider: str
    message_id: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PushProvider:
    """Firebase Cloud Messaging HTTP adapter.

    Production deployments should pass a valid bearer token or provide one through
    OPTIX_FCM_BEARER_TOKEN. This adapter uses the FCM v1 REST endpoint and avoids
    hard dependencies on Google SDK packages.
    """

    def __init__(self, project_id: Optional[str], bearer_token: Optional[str], timeout_seconds: int = 10):
        self.project_id = project_id
        self.bearer_token = bearer_token
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.project_id and self.bearer_token)

    def send(self, tokens: List[str], title: str, body: str, data: Dict[str, Any]) -> ProviderResult:
        if not tokens:
            return ProviderResult(False, "fcm", error="No push tokens supplied")
        if not self.configured:
            return ProviderResult(False, "fcm", error="FCM project/token not configured")

        endpoint = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        successes = 0
        failures: List[str] = []
        for token in tokens:
            payload = {
                "message": {
                    "token": token,
                    "notification": {"title": title, "body": body},
                    "data": {k: str(v) for k, v in data.items()},
                }
            }
            try:
                req = request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {self.bearer_token}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    if 200 <= resp.status < 300:
                        successes += 1
                    else:
                        failures.append(f"{token}: HTTP {resp.status}")
            except (HTTPError, URLError, TimeoutError) as exc:
                failures.append(f"{token}: {exc}")

        return ProviderResult(
            success=successes > 0 and successes == len(tokens),
            provider="fcm",
            metadata={"successes": successes, "failures": failures},
            error="; ".join(failures) if failures else None,
        )


class EmailProvider:
    """SMTP email adapter."""

    def __init__(
        self,
        host: Optional[str],
        port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: str = "OPTIX Alerts",
        use_tls: bool = True,
        timeout_seconds: int = 10,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.from_name = from_name
        self.use_tls = use_tls
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.host and self.from_email)

    def send(self, to_email: str, subject: str, body: str) -> ProviderResult:
        if not self.configured:
            return ProviderResult(False, "smtp", error="SMTP host/from_email not configured")
        if not to_email:
            return ProviderResult(False, "smtp", error="No recipient email supplied")

        msg = EmailMessage()
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout_seconds) as smtp:
                if self.use_tls:
                    smtp.starttls(context=ssl.create_default_context())
                if self.username and self.password:
                    smtp.login(self.username, self.password)
                smtp.send_message(msg)
            return ProviderResult(True, "smtp")
        except Exception as exc:  # pragma: no cover - provider/environment specific
            logger.exception("SMTP delivery failed")
            return ProviderResult(False, "smtp", error=str(exc))


class SMSProvider:
    """Twilio REST API adapter."""

    def __init__(self, account_sid: Optional[str], auth_token: Optional[str], from_number: Optional[str], timeout_seconds: int = 10):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.from_number)

    def send(self, to_number: str, message: str) -> ProviderResult:
        if not self.configured:
            return ProviderResult(False, "twilio", error="Twilio credentials/from_number not configured")
        if not to_number:
            return ProviderResult(False, "twilio", error="No recipient phone supplied")

        import base64
        from urllib import parse

        endpoint = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        form = parse.urlencode({"To": to_number, "From": self.from_number, "Body": message}).encode("utf-8")
        token = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode("utf-8")).decode("ascii")
        req = request.Request(
            endpoint,
            data=form,
            headers={"Authorization": f"Basic {token}", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                return ProviderResult(200 <= resp.status < 300, "twilio", message_id=payload.get("sid"), metadata=payload)
        except (HTTPError, URLError, TimeoutError) as exc:
            return ProviderResult(False, "twilio", error=str(exc))


class WebhookProvider:
    """HTTP webhook delivery adapter."""

    def __init__(self, timeout_seconds: int = 10, signing_secret: Optional[str] = None):
        self.timeout_seconds = timeout_seconds
        self.signing_secret = signing_secret

    def post(self, url: str, payload: Dict[str, Any]) -> ProviderResult:
        if not url:
            return ProviderResult(False, "webhook", error="Webhook URL missing")
        body = json.dumps(payload, default=str).encode("utf-8")
        headers = {"Content-Type": "application/json", "User-Agent": "OPTIX-Smart-Alerts/1.0"}
        req = request.Request(url, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                return ProviderResult(200 <= resp.status < 300, "webhook", metadata={"status": resp.status})
        except (HTTPError, URLError, TimeoutError) as exc:
            return ProviderResult(False, "webhook", error=str(exc))


class InAppNotificationStore:
    """In-memory in-app notification store.

    This gives the API a working notification center immediately. Production can
    replace this with the SQLAlchemy repository in `persistence.py`.
    """

    def __init__(self):
        self.notifications: Dict[str, List[Dict[str, Any]]] = {}

    def create(self, user_id: str, notification: Dict[str, Any]) -> ProviderResult:
        self.notifications.setdefault(user_id, []).append(notification)
        return ProviderResult(True, "in_app", message_id=str(notification.get("alert_id")))

    def list_for_user(self, user_id: str, unread_only: bool = False) -> List[Dict[str, Any]]:
        items = self.notifications.get(user_id, [])
        if unread_only:
            items = [item for item in items if not item.get("read", False)]
        return list(reversed(items))


@dataclass
class NotificationIntegrations:
    push: PushProvider
    email: EmailProvider
    sms: SMSProvider
    webhook: WebhookProvider
    in_app: InAppNotificationStore
    allow_simulated_fallback: bool = True

    @classmethod
    def from_env(cls) -> "NotificationIntegrations":
        return cls(
            push=PushProvider(
                project_id=os.getenv("OPTIX_FCM_PROJECT_ID"),
                bearer_token=os.getenv("OPTIX_FCM_BEARER_TOKEN"),
            ),
            email=EmailProvider(
                host=os.getenv("OPTIX_SMTP_HOST"),
                port=int(os.getenv("OPTIX_SMTP_PORT", "587")),
                username=os.getenv("OPTIX_SMTP_USERNAME"),
                password=os.getenv("OPTIX_SMTP_PASSWORD"),
                from_email=os.getenv("OPTIX_ALERTS_FROM_EMAIL"),
                from_name=os.getenv("OPTIX_ALERTS_FROM_NAME", "OPTIX Alerts"),
                use_tls=os.getenv("OPTIX_SMTP_USE_TLS", "true").lower() == "true",
            ),
            sms=SMSProvider(
                account_sid=os.getenv("OPTIX_TWILIO_ACCOUNT_SID"),
                auth_token=os.getenv("OPTIX_TWILIO_AUTH_TOKEN"),
                from_number=os.getenv("OPTIX_TWILIO_FROM_NUMBER"),
            ),
            webhook=WebhookProvider(
                timeout_seconds=int(os.getenv("OPTIX_WEBHOOK_TIMEOUT_SECONDS", "10")),
                signing_secret=os.getenv("OPTIX_WEBHOOK_SIGNING_SECRET"),
            ),
            in_app=InAppNotificationStore(),
            allow_simulated_fallback=os.getenv("OPTIX_ALLOW_SIMULATED_DELIVERY", "true").lower() == "true",
        )
