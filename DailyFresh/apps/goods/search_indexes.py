from haystack import indexes

from DailyFresh.apps.goods.models import GoodsSKU


# 商品搜索框索引,索引文件生成
# 指定对于某个类的某些数据建立索引
class GoodsSKUIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        return GoodsSKU

    def index_queryset(self, using=None):
        return self.get_model().objects.all()