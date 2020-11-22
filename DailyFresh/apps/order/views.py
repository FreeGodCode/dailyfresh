from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View


# 提交订单页面
# url地址: /order/place/
from django_redis import get_redis_connection

from DailyFresh.apps.goods.models import GoodsSKU
from DailyFresh.apps.order.models import OrderInfo, OrderGoods
from DailyFresh.apps.user.models import Address


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


class OrderPayView(View):
    """订单支付"""
    pass


class OrderCheckView(View):
    """订单签收"""
    pass


class OrderCommentView(View):
    """订单评论"""
    pass
