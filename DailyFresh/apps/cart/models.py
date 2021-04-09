from DailyFresh.db.base_model import BaseModel


class Cart(BaseModel):
    """购物车模型类"""

    class Meta:
        db_table = 'db_cart'
        verbose_name = '购物车'
        verbose_name_plural = '购物车列表'
