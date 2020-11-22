from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View


# 提交订单页面
# url地址: /order/place/
from django_redis import get_redis_connection

from DailyFresh.apps.goods.models import GoodsSKU
from DailyFresh.apps.order.models import OrderInfo, OrderGoods
from DailyFresh.apps.user.models import Address
from DailyFresh.apps.user.views import LoginRequiredMixin


class OrderPlaceView(View):
    """订单提交页面"""
    # pass
    def post(self, request):
        # 获取用户
        user = request.user

        sku_ids = request.POST.getlist('sku_ids', '')
        if len(sku_ids) == 0:
            return redirect(reverse('goods: index'))

        # 根据用户获取用户地址
        addrs = Address.objects.filter(user=user)
        cart_key = 'cart_%d' % user.id
        conn = get_redis_connection('default')

        # 便利sku_ids获取用户所购买的商品的信息
        skus = []
        total_count = 0
        total_amount = 0
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=sku_id)
            # 从redis中获取用户所购买的商品的数量
            count = conn.hget(cart_key, sku_id)
            # 商品小计
            amount = sku.price * int(count)
            # 给sku增加count和amount属性,分别用来保存用户要购买的商品数量和小计
            sku.count = count
            sku.amount = amount

            # 追加到商品列表
            skus.append(sku)
            # 累加计算用户购买的商品的总件数和总金额
            total_count += int(count)
            total_amount += amount

        # 运费
        transport_price = 10
        # 付款总额
        total_pay = total_amount + transport_price

        context = {
            'addrs': addrs,
            'skus': skus,
            'total_count': total_count,
            'total_amount': total_amount,
            'transport_price': transport_price,
            'total_pay': total_pay,
            'sku_ids': ','.join(sku_ids),
        }
        return render(request, 'place_order.html', context)


# 订单创建
# 前端传递的参数:收货地址id(addr_id) 支付方式(pay_method) 用户所要购买的全部商品的id(sku_ids)
# url地址: /order/commit/
"""
订单创建流程:
1.接受参数
2.参数校验
3.组织订单信息
4.todo:向df_order_info中添加一条记录
5.todo:订单中包含几个商品需要向df_order_goods中添加几条记录
    将sku_ids分割成一个列表
    遍历sku_ids,向df_order_goods中添加记录
        根据id获取商品信息
        从redis中获取用户要购买的商品的数量
        向df_order_goods中添加一条记录
        减少商品库存,增加销量
        累加计算订单中商品的总数量和总价格
6.更新订单信息中的商品的总数量和总价格
7.删除购物车中对应的记录
"""
# 未处理订单并发问题
class OrderCommitView(View):
    """创建订单"""
    # pass
    def post(self, request):
        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'error_msg': '用户未登录'})

        # 接受参数
        addr_id = request.POST.get('addr_id', '')
        pay_method = request.POST.get('pay_method', '')
        sku_ids = request.POST.get('sku_ids', '')

        # 校验参数
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'error_msg': '参数不完整'})

        # 校验地址id
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 2, 'error_msg': '地址信息错误'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 3, 'error_msg': '非法的支付方式'})

        # 组织订单信息
        # 订单id:当前时间+用户id
        from datetime import datetime
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)

        transport_price = 10
        total_count = 0
        total_price = 0
        # todo: 向df_order_info中添加一条记录
        order = OrderInfo.objects.create(
            order_id=order_id,
            user=user,
            addr=addr,
            pay_method=pay_method,
            total_count=total_price,
            total_price=total_price,
            transport_price=transport_price,
        )
        # todo:订单中包含几个商品需要向df_order_goods中添加几条记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        sku_ids = sku_ids.split(',')
        for sku_id in sku_ids:
            try:
                sku = GoodsSKU.objects.get(id=sku_id)
            except GoodsSKU.DoesNotExist:
                return JsonResponse({'res': 4, 'error_msg': '商品信息错误'})

            count = conn.hget(cart_key, sku_id)

            import time
            time.sleep(10)

            OrderGoods.objects.create(
                order=order,
                sku=sku,
                count=count,
                price=sku.price,
            )

            # 减少商品库存,增加销量
            sku.stock -= int(count)
            sku.sales += int(count)
            sku.save()

            # 累计计算订单中商品的总数量和总价格
            total_count += int(count)
            total_price += sku.price * int(count)

        # todo:更新订单信息中商品的总数量和总价格
        order.total_count = total_count
        order.total_price = total_price
        order.save()

        # todo: 删除购物车中对应的记录
        #     hdel(key, *args)
        conn.hdel(cart_key, *sku_ids)
        return JsonResponse({'res': 5, 'error_msg': '订单创建成功'})


from django.db import transaction
# 使用悲观锁处理创建订单
class OrderCommitView(View):
    """创建订单"""

    @transaction.atomic
    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'error_msg': '用户未登录'})

        addr_id = request.POST.get('addr_id', '')
        pay_method = request.POST.get('pay_method', '')
        sku_ids = request.POST.get('sku_ids', '')
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'error_msg': '参数不完整'})

        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 2, 'error_msg': '地址信息错误'})

        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 3, 'error_msg': '非法的支付方式'})

        from datetime import datetime
        order_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(user.id)

        transpost_price = 10

        total_count = 0
        total_price = 0
        # 设置事务保护点
        sid = transaction.savepoint()
        try:
            # 向df_order_info中添加一条记录
            order = OrderInfo.objects.create(
                order_id=order_id,
                user=user,
                addr=addr,
                pay_method=pay_method,
                total_count=total_count,
                total_price=total_price,
                transpost_price=transpost_price,
            )

            # 订单中包含几个商品就需要向df_order_goods中添加几条记录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id

            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                try:
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    # 回滚事务到sid保护点
                    transaction.savepoint_rollback(sid)
                    return JsonResponse({'res': 4, 'error_msg': '商品信息错误'})

                # 从redis中获取用户要购买的商品的数量
                count = conn.hget(cart_key, sku_id)
                # 判断商品的库存
                if int(count) > sku.stock:
                    transaction.savepoint_rollback(sid)
                    return JsonResponse({'res': 6, 'error_msg': '商品库存不足'})

                # 模拟订单并发问题
                import time
                time.sleep(10)

                # 向df_order_goods中添加一条记录
                OrderGoods.objects.create(
                    order=order,
                    sku=sku,
                    count=count,
                    price=sku.price,
                )

                # 减少商品库存,增加销量
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()

                # 累计计算订单中商品的总数量和总价格
                total_count += int(count)
                total_price += sku.price * int(count)

            # 更新订单信息中的商品的总数量和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(sid)
            return JsonResponse({'res': 7, 'error_msg': '下单失败'})

        # 删除购物车中对应的记录
        # hdel(key, *args)
        conn.hdel(cart_key, *sku_ids)
        return JsonResponse({'res': 5, 'error': '订单创建成功'})


# 使用乐观锁处理创建订单
class OrderCommitView(View):
    """创建订单"""

    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'error_msg': '用户未登录'})

        addr_id = request.POST.get('addr_id', '')
        pay_method = request.POST.get('pay_method', '')
        sku_ids = request.POST.get('sku_ids', '')
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'error_msg': '参数不完整'})

        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 2, 'error_msg': '地址信息错误'})

        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 3, 'error_msg': '非法的支付方式'})

        # 组织订单信息
        from datetime import datetime
        order_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(user.id)

        transpost_price = 10

        total_count = 0
        total_price = 0
        # 设置事务保护点
        sid = transaction.savepoint()
        try:
            # 向df_order_info中添加一条记录
            order = OrderInfo.objects.create(
                order_id=order_id,
                user=user,
                addr=addr,
                pay_method=pay_method,
                total_count=total_count,
                total_price=total_price,
                transpost_price=transpost_price,
            )

            # 订单中包含几个商品就需要向df_order_goods中添加几条记录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id

            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                for i in range(3):
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except GoodsSKU.DoesNotExist:
                        transaction.savepoint_rollbask(sid)
                        return JsonResponse({'res': 4, 'error_msg': '商品信息错误'})

                    count = conn.hget(cart_key, sku_id)

                    if int(count) > sku.stock:
                        transaction.savepoint_rollback(sid)
                        return JsonResponse({'res': 6, 'error_msg': '商品库存不足'})

                    origin_stock = sku.stock
                    new_stock = origin_stock - int(count)
                    new_sales = sku.sales + int(count)

                    # update df_goods_sku set stock="new_stock", sales='new_sales' where id=sku_id and stock=origin_stock;
                    # update方法返回更新的行数
                    res = GoodsSKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock, sales=new_sales)
                    if res == 0:
                        # 连续尝试3次,仍然下单失败,下单失败
                        if i == 2:
                            transaction.savepoint_rollback(sid)
                            return JsonResponse({'res': 7, 'error_msg': '下单失败2'})
                        continue

                    # 向df_order_goods中添加一条记录
                    OrderGoods.objects.create(
                        order=order,
                        sku=sku,
                        count=count,
                        price=sku.price,
                    )

                    # 累计计算订单中商品的总数量和总价格
                    total_count += int(count)
                    total_price += sku.price * int(count)
                    # 更新成功,跳出循环
                    break

            # 更新订单信息中商品的总数量和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(sid)
            return JsonResponse({'res': 7, 'error_msg': '下单失败1'})

        # 删除购物车中对应的记录
        # conn.hdel(key, *args)
        conn.hdel(cart_key, *sku_ids)
        return JsonResponse({'res': 5, 'error_msg': '订单创建成功'})


# 订单支付
# 前端传递的参数:订单id(order_id)
# url地址:/order/pay/
class OrderPayView(View):
    """订单支付"""
    # pass
    def post(self, request):
        # 登录验证
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'error_msg': '用户未登录'})

        order_id = request.POST.get('order_id', '')
        if not all([order_id]):
            return JsonResponse({'res': 1, 'error_msg': '参数缺失'})

        try:
            order = OrderInfo.objects.get(
                order_id=order_id,
                user=user,
                order_status=1,#订单状态为待支付
                pay_method=3,#支付方式为支付宝支付
            )
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'error_msg': '无效订单id'})

        # 业务处理:调用支付宝python SDK中的api_alipay_trade_page_pay函数
        ali_pay = AliPay(
            appid=settings.ALIPAY_APP_ID, #应用APPID
            app_notify_url=settings.ALIPAY_APP_NOTIFY_URL, #默认回调url
            app_private_key_path=settings.APP_PRIVATE_KEY_PATH, #应用私钥文件路径
            alipay_public_key_path=settings.ALIPAY_PUBLIC_KEY_PATH, #支付宝的公钥文件,验证支付宝回传消息使用,不要使用自己的公钥
            sign_type='RSA2', #RSA或者RSA2
            debug = settings.ALIPAY_DEBUG, #默认False, 线上环境,True代表沙箱环境
        )

        # 电脑网站支付,需要跳转https://openapi.alipay.com/gateway.do? + order_string
        total_pay = order.total_price + order.transport_price
        order_string = ali_pay.api_alipay_trande_page_apy(
            out_trade_on=order_id, #订单id
            total_amount=str(total_pay), #订单实付款
            subject="dailyfresh%s" % order_id, #订单标题
            return_url='http://127.0.0.1:8000/order/check',
            notify_url=None #不填默认为notify_url
        )

        pay_url = settings.ALIPAY_GATEWAY_URL + order_string
        return JsonResponse({'res': 3, 'pay_url': pay_url, 'error_msg': 'OK'})


# url地址:/order/check/
class OrderCheckView(LoginRequiredMixin, View):
    """订单签收"""
    # pass
    def get(self, request):
        """订单支付结果查询"""
        user = request.user
        order_id = request.GET.get('out_trade_no')
        try:
            order = OrderInfo.objects.get(
                order_id=order_id,
                user=user,
                order_status=1,
                pay_method=3,
            )
        except OrderInfo.DoesNotExist:
            return HttpResponse("订单信息错误")

        # 业务处理:调用python SDK中的交易查询接口
        # 初始化
        ali_pay = AliPay(
            appid=settings.ALIPAY_APP_ID,
            app_notify_url=settings.ALIPAY_APP_NOTIFY_URL,
            app_private_key_path=settings.APP_PRIVATE_KEY_PATH,
            alipay_public_key_path=settings.APP_PUBLIC_KEY_PATH,
            sign_type='RSA2',
            debug=settings.ALIPAY_DEBUG,
        )
        """
        调用python SDK中api_alipay_trade_query参数说明:
        {
            'trade_no': '', #支付宝交易号
            'code': '10000', #网关返回码
            'invoice_amount': '20.00',
            'open_id': '',
            'fund_bill_list': [
                {
                    'amount': '20.00',
                    'fund_chanel': 'ALIPAYACCOUNT'
                }
            ],
            'buyer_login_id': '',
            'send_pay_date': '',
            'receipt_amount': '20.00',
            'out_trade_no': '',
            'buyer_pay_amount': '',
            'buyer_user_id': '',
            'msg': 'Success',
            'point_amount': '0.00',
            'trade_status': 'TRADE_SUCCESS', #支付状态
            'total_amount': '20.00',
        }
        """

        # 调用python SDK中api_alipay_trade_query查询结果
        response = ali_pay.api_alipay_trande_query(out_trade_no=order_id)
        # 获取支付宝网关的返回码
        res_code = response.get('code')
        if res_code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
            order.order_status = 4 #待评价
            order.trade_no = response.get('trade_no')
            order.save()
            return render(request, 'pay_result.html', {'pay_result': '支付成功'})
        else:
            return render(request, 'pay_result.html', {'pay_result': '支付失败'})


# 订单评论
# url地址: /order/comment/订单id
class OrderCommentView(LoginRequiredMixin, View):
    """订单评论"""
    # pass
    def get(self, request, order_id):
        """展示评论页面"""
        user = request.user
        if not order_id:
            return redirect(reverse('user: order', kwargs={'page: 1'}))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user: order', kwargs={'page': 1}))

        # 根据订单的状态获取订单的状态标题
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        # 获取订单的商品信息
        order_skus = OrderInfo.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            amount = order_sku.count * order_sku.price
            # 动态给order_sku增加属性amount,保存商品小计
            order_sku.amount = amount

        # 动态给order增加属性order_skus,保存订单商品信息
        order.order_skus = order_skus
        return render(request, 'order_comment.html', {'order': order})

    def post(self, request, order_id):
        """处理评论内容"""
        user = request.user
        if not order_id:
            return redirect(reverse('user: order', kwargs={'page': 1}))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user: order', kwargs={'page': 1}))

        # 获取评论条数
        total_count = request.POST.get('total_count')
        total_count = int(total_count)

        # 循环获取订单中商品的评论内容
        for i in range(1, total_count + 1):
            sku_id = request.POST.get('sku_%d' % i, '')
            content = request.POST.get('content_%d' % i, '')
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue
            order_goods.content = content
            order_goods.save()

        order.order_status = 5 #完成
        order.save()
        return redirect(reverse('user: order', kwargs={'page': 1}))
