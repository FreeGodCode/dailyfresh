from django.core.cache import cache
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic.base import View
from django_redis import get_redis_connection

from DailyFresh.apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner, \
    GoodsSKU
from DailyFresh.apps.order.models import OrderGoods


class IndexView(View):
    """首页"""

    def get(self, request):
        """展示页面"""
        # 尝试从缓存中获取数据
        context = cache.get('index_page_data')
        if context is None:
            # 获取商品的分类信息
            types = GoodsType.objects.all()
            # 获取首页的轮播商品信息
            index_banner = IndexGoodsBanner.objects.all().order_by('index')
            # 获取首页促销活动的信息
            promotion_banner = IndexPromotionBanner.objects.all().order_by('index')
            # 获取首页分类商品的展示信息
            for category in types:
                image_banner = IndexTypeGoodsBanner.objects.filter(category=category, display_type=1)
                title_banner = IndexTypeGoodsBanner.objects.filter(category=category, display_type=0)
                category.title_banner = title_banner
                category.image_banner = image_banner

            context = {
                'type': types,
                'index_banner': index_banner,
                'promotion_banner': promotion_banner,
                'cart_count': 0,
            }
            # 缓存数据
            # cache.set('缓存名称', '缓存数据', '缓存有效时间')
            cache.set('index_page_data', context, 3600)

        # 判断用户是否已登录
        cart_count = 0
        if request.user.is_authenticated():
            # 连接redis
            conn = get_redis_connection('default')
            cart_key = 'cart_%s' % request.user.id

            # hlen(key)-> 返回属性的数目
            cart_count = conn.hlen(cart_key)

        context.update(cart_count=cart_count)
        return render(request, 'index.html', context)


# 商品详情页
# 前端传递的参数:商品id(sku_id)
# url地址:/goods/商品id
class DetailView(View):
    """商品详情页"""

    def get(self, request, sku_id):
        """展示"""
        # 获取商品的详细信息
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在直接跳回首页
            return redirect(reverse('goods:index'))

        # 获取商品的分类信息
        types = GoodsType.objects.all()
        # 获取商品的评论信息
        order_skus = OrderGoods.objects.filter(sku=sku).exclude(comment='').order_by('-update_time')
        # 获取同一SPU的其他规格商品
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=sku_id)
        # 获取同一种类的新品信息
        new_skus = GoodsSKU.objects.filter(category=sku.category).order_by('-created_time')[:2]

        # 若用户登录,获取购物车中的商品的条目数
        cart_count = 0
        if request.user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % request.user.id
            # hlen(key)->返回属性的数量
            cart_count = conn.hlen(cart_key)

            # 添加用户的历史浏览记录
            # 拼接key
            history_key = 'history_%d' % request.user.id

            # 先从redis对应列表中移除sku_id
            # lrem(key, count, value) -> 如果key存在就移除,不存在不做任何操作
            # count = 0表示移除所有值为value的元素
            conn.lrem(history_key, 0, sku_id)

            # 把sku_id添加到redis对应的列表左侧
            # lpush(key, *args)
            conn.lpush(history_key, sku_id)

            # 只保存用户最新浏览的5个商品的id
            # ltrim(key, start, stop)
            conn.ltrim(history_key, 0, 4)

        context = {
            'sku': sku,
            'types': types,
            'order_skus': order_skus,
            'same_spu_skus': same_spu_skus,
            'new_skus': new_skus,
            'cart_count': cart_count,
        }
        return render(request, 'detail.html', context)


# 前端传递过来的参数:种类id(type_id) 页码(page) 排列方式(sort)
# url地址:/list/种类id/页码?sort=排列方式
class ListView(View):
    """商品列表页"""

    # def get(self, request):
    def get(self, request, type_id, page):
        """页面数据展示"""
        # 获取参数
        # type_id = request.GET.get('type_id', '')
        # page = request.GET.get('page', '')
        # sort = request.GET.get('sort', '')
        # 获取种类id对应的商品种类信息,判断是否合法存在
        try:
            category = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return redirect(reverse('goods: index'))

        # 获取所有种类
        types = GoodsType.objects.all()

        # 获取排列顺序
        # 排列顺序:
        # 1.sort=price:按照商品的价格排序(从低到高)
        # 2.sort=sales:按照商品的销量排序(从高到低)
        # 3.sort=default:按照默认排序方式(id)排序(从高到低)
        sort = request.GET.get('sort', '')

        # 按照种类获取商品信息的排列结果集
        if sort == 'price':
            skus = GoodsSKU.objects.filter(category=category).order_by('price')
        elif sort == 'sales':
            skus = GoodsSKU.objects.filter(category=category).order_by('-sales')
        else:
            sort = 'default'
            skus = GoodsSKU.objects.filter(category=category).order_by('-id')

        # 将结果集按照每页显示5条数据进行分页操作
        paginator = Paginator(skus, 5)

        # 处理页码
        page = int(page)
        if page > paginator.num_pages:
            page = 1

        # 获取第page页内容,返回Page类的实例对象
        skus_page = paginator.page(page)

        # 页码处理
        num_pages = paginator.num_pages
        if num_pages < 5:
            # 1-num_pages
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            # num_pages-4, num_pages
            pages = range(num_pages - 4, num_pages + 1)
        else:
            # page-2, page+2
            pages = range(page - 2, page + 3)

        # 获取type种类的2个新品信息
        new_skus = GoodsSKU.objects.filter(category=category).order_by('-created_time')[:2]

        # 如果用户登录,获取用户购物车中商品的条目数
        cart_count = 0
        if request.user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = 'cart_%s' % request.user.id
            cart_count = conn.lhen(cart_key)

        context = {
            'type': category,
            'types': types,
            'skus_page': skus_page,
            'new_skus': new_skus,
            'cart_count': cart_count,
            'sort': sort,
            'pages': pages,
        }

        return render(request, 'list.html', context)
