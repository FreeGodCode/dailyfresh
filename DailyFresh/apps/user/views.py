import re

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic.base import View
from django_redis import get_redis_connection

from DailyFresh.DailyFresh import settings
from DailyFresh.apps.user.models import User, Address

from DailyFresh.apps.order.models import OrderInfo, OrderGoods


class RegisterView(View):
    """注册"""
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        # 获取表单数据
        username = request.POST.get('user_name', '')
        password = request.POST.get('password', '')
        email = request.POST.get('email')

        # 参数校验(校验数据的完整性)
        if not all([username, password, email]):
            return render(request, 'register.html', {'error_msg': '数据不完整'})

        # 邮箱校验
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'error_msg': '邮箱格式不正确'})

        # 校验用户名是否已注册
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None

        # 校验邮箱是否已注册
        # try:
        #     email = User.objects.get(email=email)
        # except User.DoesNotExist:
        #     user = None

        if user is not None:
            return render(request, 'register.html', {'error_msg': '用户名已存在'})

        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()

        # 注册->邮件激活->邮件包含激活链接
        # 激活链接: /user/active/加密后的token
        # 对用户身份信息进行加密,生成激活token信息
        serializer = Serializer(settings.SECRET_KEY, 3600 * 7) #from itsdangerous import TimedJSONWebSignatureSerizlizer as Serializer
        info = {'confirm': user.id}
        token = serializer.dumps(info)

        # str
        token = token.decode()

        # 组织邮件
        subject = ''
        message = ''
        sender = settings.EMAIL_FROM
        receiver = [email]
        html_message = """
        <h1>%s, 欢迎您注册会员!</h1>
        请点击下方链接激活您的帐号(7小时内有效)<br/>
        <a href='http://127.0.0.1:8000/user/active/%s'>http://127.0.0.1:8000/user/active/%s</a>
        """%(username, token, token)

        # 发送邮件
        # send_mail(subject='邮件标题', message='邮件正文', from_email='发件人', recipient_list='收件人列表')
        # send_mail(subject, message, sender, receiver, html_message)
        # 定义异步执行任务
        tasks.send_register_active_email.delay(email, username, token) #from celery_tasks import tasks

        # 返回跳转到首页
        return redirect(reverse('goods: index'))


class ActiveView(View):
    """激活"""
    def get(self, request, token):
        serializer = Serializer(settings.SECRET_KEY, 3600 * 7)
        try:
            # 解密
            info = serializer.loads(token)
            # 获取待激活用户id
            user_id = info['confirm']
            # 激活用户
            user = User.objects.get(id = user_id)
            user.is_active = 1
            user.save()
            # 跳转页面
            return redirect(reverse('user: login'))
        except SignatureExpired as e:
            # 激活链接失效
            # 实际开发中,返回页面,再次点击链接发送激活邮件
            return HttpResponse('激活链接已失效')


class LoginView(View):
    """登录"""

    def get(self, request):
        """显示"""
        # 判断用户是否记住用户名
        username = request.COOKIES.get('username')
        checked = 'checked'
        if username is None:
            # 没有记住用户名
            username = ''
            checked = ''
            return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        """登录校验"""
        # 接受参数
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        remember = request.POST.get('remember', '')

        # 参数校验
        if not all([username, password]):
            return render(request, 'login.html', {'error_msg': '参数不完整'})
        # 业务处理
        user = authenticate(username = username, password = password)
        if user is not None:
            # 用户名和密码正确
            if user.is_active:
                # 用户已激活,记住用户的登录状态
                login(request, user)
                # 获取用户登录之前访问的url地址,默认跳转到首页
                next_url = request.GET.get('next', reverse('goods: index'))
                response = redirect(next_url)

                # 判断是否需要记住用户名
                if remember == 'on':
                    # 设置cookie
                    response.set_cookie('username', username, max_age=7*24*3600)
                else:
                    # 删除cookie
                    response.delete_cookie('username')
                return response

            else:
                # 用户未激活
                return render(request, 'login.html', {'error_msg': '用户未激活'})
        else:
            # 用户名或密码错误
            return render(request, 'login.html', {'error_msg': '用户名或者密码错误'})


class LogoutView(View):
    """退出"""

    def get(self, request):
        """退出"""
        # 清除用户登录状态,内置的logout函数会自动清除当前session
        logout(request)
        # 跳转到登录
        return redirect(reverse('user.login'))


# 继承View来复写as_view()方法
class LoginRequiredView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        # view = super(LoginRequiredView, self).as_view(**initkwargs)
        view = super().as_view(**initkwargs)
        # 调用login_required装饰器函数
        return login_required(view)


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, **initkwargs ):
        # view = super(LoginRequiredMixin, self).as_view(**initkwargs)
        view = super().as_view(**initkwargs)
        return login_required(view)


class UserInfoView(LoginRequiredMixin, View):
    """用户中心-信息页"""

    def get(self, request):
        """显示页面"""
        user = request.user
        # 获取用户的默认收货地址
        address = Address.objects.get_default_address(user)

        # 获取用户最近浏览商品信息
        # 使用redis的第三方包进行交互
        # from redis import StrictRedis
        # conn = StrictRedis(host='127.0.0.1', port=6379, db=5)
        # 返回StrictRedis类对象

        # 使用django-redis
        conn = get_redis_connection('default')
        # 拼接KEY
        history_key = 'history_%d'% user.id
        # lrange(key, start, stop) 返回列表
        # 获取用户最新浏览的5个商品
        sku_ids = conn.lrange(history_key, 0, 4)

        skus = []
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id = sku_id) #goods.models GoodsSKU
            skus.append(sku)

        # 组织模板上下文
        data = {
            'address': address,
            'skus': skus,
            'page': 'user'
        }
        return render(request, 'user_center_info.html', data)

class UserOrderView(LoginRequiredMixin, View):
    """用户中心-订单页"""

    def get(self, request):
        """显示页面"""
        user = request.user
        # 查询订单情况,若有订单则为1
        info_msg = 1
        try:
            # 查询结果按照创建时间倒序排列
            order_infos = OrderInfo.objects.filter(user = user).order_by('-created_time')
        except OrderInfo.DoesNotExist:
            info_msg = 0

        if len(order_infos) == 0:
            info_msg = 0
        context = {
            'page': 'order',
            'info_msg': info_msg,
        }
        if info_msg == 1:
            for order_info in order_infos:
                order_goods = OrderGoods.objects.filter(order=order_info)
                for order_good in order_goods:
                    amout = order_good.price * order_good.count
                    order_good.amout = amout
                order_info.order_goods = order_goods
                order_info.status = OrderInfo.ORDER_STATUS[order_info.order_status]

            # 分页
            from django.core.paginator import Paginator
            paginator = Paginator(order_infos, 3)

            page = int(page)
            if page > paginator.num_pages:
                # 默认获取第一页的内容
                page  = 1

            # 获取第page页的内容,返回Page类的实例对象
            order_infos_page = paginator.page(page)

            # 页码处理
            num_pages = paginator.num_pages
            if num_pages < 5:
                pages = range(1, num_pages + 1)
            elif page <= 3:
                pages = range(1, 6)
            elif num_pages - page <=2:
                pages = range(num_pages - 4, num_pages + 1)
            else:
                pages = range(page - 2, page + 3)

            context = {
                'page': 'order',
                'order_infos': order_infos,
                'info_msg': info_msg,
                'pages': pages,
                'order_infos_page': order_infos_page
            }
        return render(request, 'user_center_order.html', context)


class AddressView(LoginRequiredMixin, View):
    """用户中心-地址页"""

    def get(self, request):
        """显示页面"""
        user = request.user
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     address = None
        default_address = Address.objects.get_default_address(user)
        all_address = Address.objects.get_all_address(user)
        context = {
            'address': default_address,
            'all_address': all_address,
            'page': 'address',
        }
        return render(request, 'user_center_site.html', context)

    def post(self, request):
        """新增地址"""
        # 获取参数
        receiver = request.POST.get('receiver', '')
        addr = request.POST.get('address', '')
        post_code = request.POST.get('post_code', '')
        phone = request.POST.get('phone_number', '')

        # 校验参数
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'error_msg': '参数不完整'})

        # 业务处理:添加收货地址,如果用户已有默认地址,新添加的地址作为非默认地址
        # 获取登录用户
        user = request.user
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     address = None

        address = Address.objects.get_default_address(user)
        is_default = True
        if address is not None:
            is_default = False

        # 添加收货地址
        Address.objects.create(
            user=user,
            receiver=receiver,
            post_code=post_code,
            phone=phone,
            is_default=is_default
        )
        # 返回,刷新地址页面
        return redirect(reverse('user:address'))
