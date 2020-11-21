from django.db import models

from DailyFresh.db.base_model import BaseModel


class GoodsSKU(BaseModel):
    """商品模型类"""

    # id = models.
    stock = models.IntegerField(default=0, verbose_name='商品库存')

    class Meta:
        db_table = 'db_goods'
        verbose_name = '商品'
        verbose_name_plural = '商品列表'