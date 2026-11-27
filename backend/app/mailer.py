"""官方邮件发送服务：注册/登录验证码 + 后台推送共用 SMTP 通道。

设计要点：
- smtplib 是阻塞 IO，统一在 async 路由里用 `run_in_threadpool` 调用，避免堵事件循环；
- dev_mode=1 时不连 SMTP，只把邮件正文（含验证码）打到 uvicorn 日志，方便本地开发；
- 发件失败抛 RuntimeError，由调用方决定是「返回 500」还是「记录失败回执」（推送场景后者）；
- 凭据只从 config.MAIL 读取，绝不进日志/响应。
"""
import logging
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from .config import MAIL

logger = logging.getLogger("uvicorn.error")


def build_code_email(code: str, purpose: str) -> tuple[str, str]:
    """生成验证码邮件（纯文本 + HTML 双份）。返回 (subject, html_body)。"""
    scene = "注册" if purpose == "register" else "登录"
    subject = f"【星穹旅驿】邮箱{scene}验证码"
    text = (
        f"您正在进行邮箱{scene}验证，验证码为：{code}\n"
        "验证码 5 分钟内有效，请勿转发给他人。\n"
        "若非本人操作，请忽略此邮件。"
    )
    html = f"""\
<div style="font-family:Arial,'Microsoft YaHei',sans-serif;max-width:560px;margin:auto">
  <h2 style="color:#43A047">星穹旅驿 · 邮箱{scene}验证</h2>
  <p>您正在进行邮箱{scene}验证，验证码为：</p>
  <div style="font-size:32px;font-weight:bold;letter-spacing:8px;color:#2E7D32;
              padding:12px 16px;border:2px dashed #7CB342;margin:16px 0">{code}</div>
  <p style="color:#666">验证码 <b>5 分钟</b>内有效，请勿转发给他人。若非本人操作，请忽略此邮件。</p>
</div>"""
    return subject, text, html


def send_mail(to: str, subject: str, text: str = "", html: str = "") -> None:
    """发送一封邮件（阻塞；调用方需在线程池中执行）。

    成功返回 None；任何失败抛 RuntimeError（消息已脱敏，不含凭据）。
    """
    if MAIL.dev_mode:
        logger.info("[MAIL-DEV] to=%s subject=%s body=%s", to, subject, text or html)
        return

    sender = MAIL.sender or MAIL.username
    if not (MAIL.host and sender and MAIL.port):
        raise RuntimeError("官方邮箱未配置（MAIL_HOST / MAIL_USERNAME / MAIL_SENDER）")

    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((str(Header(MAIL.sender_name, "utf-8")), sender))
    msg["To"] = to
    msg["Subject"] = Header(subject, "utf-8")
    if text:
        msg.attach(MIMEText(text, "plain", "utf-8"))
    if html:
        msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        if MAIL.use_tls:  # 465 隐式 SSL
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(MAIL.host, MAIL.port, timeout=MAIL.timeout, context=ctx) as smtp:
                if MAIL.username and MAIL.password:
                    smtp.login(MAIL.username, MAIL.password)
                smtp.sendmail(sender, [to], msg.as_string())
        else:  # 25/587 明文 + STARTTLS
            with smtplib.SMTP(MAIL.host, MAIL.port, timeout=MAIL.timeout) as smtp:
                smtp.ehlo()
                try:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                except smtplib.SMTPException:
                    pass  # 服务器不支持 STARTTLS 时按明文继续
                if MAIL.username and MAIL.password:
                    smtp.login(MAIL.username, MAIL.password)
                smtp.sendmail(sender, [to], msg.as_string())
    except Exception as e:
        logger.warning("邮件发送失败 to=%s: %s", to, type(e).__name__)
        raise RuntimeError(f"邮件发送失败：{type(e).__name__}") from None
