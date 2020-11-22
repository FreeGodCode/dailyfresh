from django.db import models
from tinymce.models import HTMLField

from DailyFresh.db.base_model import BaseModel


class GoodsType(BaseModel):
    """商品种类模型类"""

    name = models.CharField(max_length=20, verbose_name='种类模型')
    logo = models.CharField(max_length=20, verbose_name='标识')
    image = models.ImageField(upload_to='type', verbose_name='商品类型图片')

    class Meta:
        db_table = 'df_goods_type'
        verbose_name = '商品种类'
        verbose_name_plural = '商品种类列表'

    def __str__(self):
        return self.name


class GoodsSKU(BaseModel):
    """商品SKU模型类"""

    status_choices = (
        (0, "下架"),
        (1, '上架'),
    )
    category = models.ForeignKey('GoodsType', verbose_name='商品种类', on_delete=models.CASCADE)
    goods = models.ForeignKey('Goods', verbose_name='商品SPU', on_delete=models.CASCADE)
    name = models.CharField(max_length=20, verbose_name='商品名称')
    desc = models.CharField(max_length=256, verbose_name='商品简介')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='商品价格')
    unite = models.CharField(max_length=20, verbose_name='商品单位')
    image = models.ImageField(upload_to='goods', verbose_name='商品图片')
    stock = models.IntegerField(default=1, verbose_name='商品库存')
    sales = models.IntegerField(default=0, verbose_name='商品销量')
    status = models.SmallIntegerField(default=1, choices=status_choices, verbose_name='商品状态')

    class Meta:
        db_table = 'df_goods_sku'
        verbose_name = '商品'
        verbose_name_plural = '商品列表'


class Goods(BaseModel):
    """商品SPU模型类"""

    name = models.CharField(max_length=20, verbose_name='商品SPU名称')
    detail = HTMLField(bland=True, verbose_name='商品详情')

    class Meta:
        db_table = 'df_goods'
        verbose_name = '商品SPU'
        verbose_name_plural = '商品SPU列表'


class GoodsImage(BaseModel):
    """商品图片模型类"""

    sku = models.ForeignKey('GoodsSKU', verbose_name='商品', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='goods', verbose_name='商品路径')

    class Meta:
        db_table = 'df_goods_image'
        verbose_name = '商品图片'
        verbose_name_plural = '商品图片列表'


class IndexGoodsBanner(BaseModel):
    """首页轮播商品展示模型类"""

    sku = models.ForeignKey('GoodsSKU', verbose_name='商品', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='banner', verbose_name='图片')
    index = models.SmallIntegerField(default=1, verbose_name='展示顺序')

    class Meta:
        db_table = 'df_index_banner'
        verbose_name = '首页轮播商品'
        verbose_name_plural = '首页商品轮播列表'


class IndexTypeGoodsBanner(BaseModel):
    """首页分类商品展示模型类"""

    DISPLAY_TYPE_CHOICE = (
        (0, '标题'),
        (1, '图片'),
    )

    category = models.ForeignKey('GoodsType', verbose_name='商品类型', on_delete=models.CASCADE)
    sku = models.ForeignKey('GoodsSKU', verbose_name='商品SKU', on_delete=models.CASCADE)
    display_type = models.SmallIntegerField(default=1, choices=DISPLAY_TYPE_CHOICE, verbose_name='展示类型')
    index = models.SmallIntegerField(default=0, verbose_name='展示顺序')

    class Meta:
        db_table = 'df_index_type_goods'
        verbose_name = '首页分类展示商品'
        verbose_name_plural = '首页分类展示商品列表'


class IndexPromotionBanner(BaseModel):
    """首页促销活动模型类"""

    name = models.CharField(max_length=20, verbose_name='活动名称')
    url = models.CharField(max_length=256, verbose_name='活动链接')
    image = models.ImageField(upload_to='banner', verbose_name='活动图片')
    index = models.SmallIntegerField(default=0, verbose_name='展示顺序')

    class Meta:
        db_table = 'df_index_promotion'
        verbose_name = '主页促销活动'
        verbose_name_plural = '主页促销活动列表'
