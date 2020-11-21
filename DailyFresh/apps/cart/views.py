from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic.base import View
from django_redis import get_redis_connection

from DailyFresh.apps.cart.models import GoodsSKU

# get /cart/
class CartInfoView(View):
    """购物车页面显示"""

    def get(self, request):
        """页面展示"""
        user = request.user

        # 从redis中获取用户的购物车记录信息
        conn = get_redis_connection('default')
        # 拼接key
        cart_key = 'cart_%d'% user.id
        # hgetall()返回一个字典,字典键是商品id,值是添加的数目
        cart_dict = conn.hgetall(cart_key)

        total_count = 0
        total_amount = 0
        skus = []
        for sku_id, count in cart_dict.items():
            sku = GoodsSKU.objects.get(id=sku_id)
            amount = sku.price * int(count)
            sku.count = count
            sku.amount = amount
            skus.append(sku)

            total_count += int(count)
            total_amount += amount

        context = {
            'total_count': total_count,
            'total_amount': total_amount,
            'skus': skus,
        }
        return render(request, 'cart.html', context)


# 前端传递的参数: 商品id(sku_id) 商品数量(count)
# /cart/add
class CartAddView(View):
    """添加购物车记录"""

    def post(self, request):
        user = request.user
        # 判断用户登录情况
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'error_msg': '请登录'})

        sku_id = request.POST.get('sku_id', '')
        count = request.POST.get('count', '')
        # 校验参数
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'error_msg': '参数不完整'})

        # 校验商品id
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'error_msg': '商品信息错误'})

        # 检验商品数量
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 3, 'error_msg': '商品数量必须为数字'})

        # 义务处理:添加购物车记录
        # 获取redis连接
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        # hget(key, field)
        cart_count = conn.hget(cart_key, sku_id)

        # 如果用户购物车中已经添加过sku_id商品,购物车中对应商品的数目需要进行累加
        if cart_count:
            count += int(cart_count)

        # 校验商品库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'error_msg': '商品库存不足'})

        # 设置用户购车中sku_id商品的数量
        # hset(key, field, value) 存在就修改,不存在就新增
        conn.hset(cart_key, sku_id, count)

        # 获取用户购物车中商品的条目数
        cart_count = conn.hlen(cart_key)
        return JsonResponse({'res': 5, 'cart_count': cart_count, 'error_msg': '添加购物车记录成功'})


class CartUpdateView(View):
    """更新购物车记录"""

    def post(self, request):
        user = request.user
        # 判断用户是否登录
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'error_msg': '请登录'})

        # 获取参数
        sku_id = request.POST.get('sku_id', '')
        count = request.POST.get('count', '')

        # 校验参数
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'error_msg': '参数不完整'})

        # 校验商品id
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'error_msg': '商品信息错误'})

        # 校验商品数量count
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 3, 'error_msg': '商品数量必须为有效数字'})

        # 连接redis
        conn = get_redis_connection('default')
        # 拼接key
        cart_key = 'cart_%d' % user.id

        # 校验商品的库存量
        if count > sku.stock:
            return JsonResponse({'res': 4, 'error_msg': '商品库存不足'})

        # 更新用户购物车中商品数量
        conn.hset(cart_key, sku_id, count)
        return JsonResponse({'res': 5, 'error_msg': '更新购物车记录成功'})


# 前端传递的数据:商品id(sku_id)
# /cart/delete
class CartDeleteView(View):
    """购物车记录删除"""

    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'error_msg': '请登录'})

        sku_id = request.POST.get('sku_id', '')
        if not all([sku_id]):
            return JsonResponse({'res': 1, 'error_msg': '参数不完整'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'error_msg': '商品信息错误'})

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        # 删除记录
        # hdel(key, field)
        conn.hdel(cart_key, sku_id)

        return JsonResponse({'res': 3, 'error_msg': '删除购物车记录成功'})















