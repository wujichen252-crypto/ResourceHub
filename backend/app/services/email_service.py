"""
邮件发送适配层

目前只有「密码重置验证码」一种邮件。发送走标准 SMTP Submission：
QQ 邮箱默认 smtp.qq.com:465 + SSL，密码栏填邮箱授权码而非登录密码。
替换发件服务商只需改环境变量，业务代码不感知。
"""

import asyncio
import html
import logging
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def is_configured(self) -> bool:
        """发件账号是否齐全；未配置时业务层应给出明确提示而不是假装已发送"""
        return settings.smtp_configured

    async def send_password_reset_code(
        self, to_email: str, username: str, code: str, ttl_minutes: int
    ) -> None:
        # smtplib 是阻塞 IO，放进线程池避免卡住事件循环
        await asyncio.to_thread(
            self._send_password_reset_code_sync, to_email, username, code, ttl_minutes
        )

    def _send_password_reset_code_sync(
        self, to_email: str, username: str, code: str, ttl_minutes: int
    ) -> None:
        safe_name = html.escape(username)
        text_body = (
            f"{username}，你好：\n\n"
            f"你正在重置 ResourceHub 的登录密码，验证码：{code}\n"
            f"验证码 {ttl_minutes} 分钟内有效，仅可使用一次。\n"
            f"如非本人操作，请忽略本邮件，你的密码不会被修改。\n"
        )
        html_body = f"""
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1f1f1f;line-height:1.7">
          <p>{safe_name}，你好：</p>
          <p>你正在重置 ResourceHub 的登录密码，验证码：</p>
          <p style="font-size:30px;font-weight:700;letter-spacing:8px;margin:16px 0">{code}</p>
          <p>验证码 {ttl_minutes} 分钟内有效，仅可使用一次。</p>
          <p style="color:#666">如非本人操作，请忽略本邮件，你的密码不会被修改。</p>
        </div>
        """

        message = MIMEMultipart("alternative")
        message["Subject"] = Header("【ResourceHub】密码重置验证码", "utf-8")
        message["From"] = formataddr((str(Header(settings.SMTP_FROM_NAME, "utf-8")), settings.SMTP_USER))
        message["To"] = to_email
        message.attach(MIMEText(text_body, "plain", "utf-8"))
        message.attach(MIMEText(html_body, "html", "utf-8"))

        if settings.SMTP_USE_SSL:
            client = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        else:
            client = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        with client as server:
            if not settings.SMTP_USE_SSL:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, [to_email], message.as_string())


email_service = EmailService()
