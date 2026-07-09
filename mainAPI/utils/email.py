"""
Email utility using Resend for transactional emails.
"""
import logging
import resend
from decouple import config

logger = logging.getLogger(__name__)

# Configure Resend API key from environment
resend.api_key = config('RESEND_API_KEY', default='')

RESEND_FROM_EMAIL = config('RESEND_FROM_EMAIL', default='noreply@example.com')


def send_password_reset_email(recipient_email: str, recipient_name: str, reset_token: str) -> bool:
    """
    Send a password reset email via Resend.

    Args:
        recipient_email: The user's email address.
        recipient_name: The user's full name (for personalisation).
        reset_token: The one-time reset token string.

    Returns:
        True if the email was dispatched successfully, False otherwise.
    """
    if not resend.api_key:
        logger.error("RESEND_API_KEY is not configured – cannot send reset email.")
        return False

    subject = "Yêu cầu đặt lại mật khẩu"
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: auto;">
        <h2 style="color: #2d6a9f;">Đặt lại mật khẩu của bạn</h2>
        <p>Xin chào <strong>{recipient_name}</strong>,</p>
        <p>Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn.</p>
        <p>Sử dụng <strong>mã 8 chữ số</strong> dưới đây để đặt lại mật khẩu. Mã này sẽ hết hạn sau <strong>15 phút</strong>.</p>
        <div style="background: #f4f4f4; border-radius: 8px; padding: 20px 24px; margin: 24px 0; text-align: center;">
          <span style="font-size: 36px; font-weight: bold; letter-spacing: 10px; color: #2d6a9f;">{reset_token}</span>
        </div>
        <p>Nếu bạn không yêu cầu đặt lại mật khẩu, hãy bỏ qua email này. Mật khẩu của bạn sẽ không thay đổi.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0;">
        <p style="font-size: 12px; color: #999;">Email này được gửi tự động, vui lòng không phản hồi.</p>
      </body>
    </html>
    """

    try:
        params: resend.Emails.SendParams = {
            "from": RESEND_FROM_EMAIL,
            "to": [recipient_email],
            "subject": subject,
            "html": html_body,
        }
        response = resend.Emails.send(params)
        logger.info("Password reset email sent to %s (id=%s)", recipient_email, response.get("id"))
        return True
    except Exception as exc:
        logger.error("Failed to send password reset email to %s: %s", recipient_email, exc)
        return False
