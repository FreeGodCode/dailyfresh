import os
import sys

import django
from django.core.mail import send_mail
from django.template import loader

from DailyFresh.DailyFresh import settings
from DailyFresh.apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
from DailyFresh.celery_tasks.celery import app as app

# 设置django配置依赖的环境变量
sys.path.insert(0, './')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DailyFresh.settings')
django.setup()


# 定义任务函数
@app.task
def send_register_active_email(to_email, username, token):
    """发送激活邮件"""
    # 组织邮件
    subject = ''
    message = ''
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    html_message = ""
    # 发送激活邮件
    # send_mail(subject=邮件标题, message=邮件正文, from_email=发件人, recipient_list=收件人列表)
    send_mail(subject, message, sender, receiver, html_message=html_message)


@app.task
def generate_static_index_html():
    """使用celery生成静态首页文件"""
    # 获取商品的分类信息
    types = GoodsType.objects.all()
    # 获取首页轮播商品信息
    index_banner = IndexGoodsBanner.objects.all().order_by('index')
    # 获取首页促销活动的信息
    promotion_banner = IndexPromotionBanner.objects.all().order_by('index')
    # 获取首页分类商品的展示信息
    for category in types:
        # 获取type种类在首页展示的图片商品信息和文字商品信息
        image_banner = IndexTypeGoodsBanner.objects.filter(category=category, display_type=1)
        title_banner = IndexTypeGoodsBanner.objects.filter(category=category, display_type=0)

        # 给category对象增加title_banner, image_banner
        # 分别保存category种类在首页展示的文字商品和图片商品的信息
        category.title_banner = title_banner
        category.image_banner = image_banner

    cart_count = 0
    # 组织模板上下文
    context = {
        'types': types,
        'index_banner': index_banner,
        'promotion_banner': promotion_banner,
        'cart_count': cart_count,
    }

    # 加载模板
    temp = loader.get_template('static_index.html')
    # 渲染模板
    static_html = temp.render(context)
    # 生成静态首页文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w') as f:
        f.write(static_html)
