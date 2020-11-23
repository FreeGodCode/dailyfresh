from django.contrib import admin
from django.core.cache import cache

from DailyFresh.apps.goods.models import GoodsType, IndexGoodsBanner, IndexTypeGoodsBanner, IndexPromotionBanner


class BaseModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        """新增或更新时调用"""
        # 调用ModelAdmin中save_model来实现更新或新增
        super(BaseModelAdmin, self).save_model(request, obj, form, change)

        # 附加操作,发出生成静态首页的任务
        from DailyFresh.celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        # 清除首页缓存
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        """删除数据时调用"""
        # 调用ModelAdmin中的delete_model来实现删除操作
        super(BaseModelAdmin, self).delete_model(request, obj)

        from DailyFresh.celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        cache.delete('index_page_data')


class GoodsTypeAdmin(BaseModelAdmin):
    """商品种类模型Admin管理类"""
    pass


class IndexGoodsBannerAdmin(BaseModelAdmin):
    """首页轮播商品模型admin管理类"""
    pass


class IndexTypeGoodsBannerAdmin(BaseModelAdmin):
    """首页分类商品展示模型admin管理类"""
    pass


class IndexPromotionBannerAdmin(BaseModelAdmin):
    """首页促销活动admin管理类"""
    pass

admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
