from celery.task import task
from django.core.mail import send_mail

# from DailyFresh import settings
from DailyFresh.DailyFresh import settings


@task
def send_register_active_email(to_email, username, token):
    """发送激活邮件"""

    # 组织邮件内容
    subject = ""
    message = ""
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    html_message = """
    <h1>%s, 欢迎您注册每日生鲜的会员</h1>
    请点击下方链接激活您的账户<br/>
    <a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>
    """ % (username, token, token)

    # 发送激活邮件
    send_mail(subject, message, sender, receiver, html_message=html_message)