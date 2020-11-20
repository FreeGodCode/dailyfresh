from django.contrib.auth.models import AbstractUser
from django.db import models


class BaseMoled(models.Model):
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='是否删除')

    class Meta:
        """指定为抽象模型类"""
        abstract = True

class User(BaseMoled, AbstractUser):
    """用户模型类"""

    class Meta:
        db_table = "df_user"
        verbose_name = '用户'
        verbose_name_plural = "用户列表"


class AddressManager(models.Manager):
    """地址模型管理器类"""

    # 改变原有查询的结果集
    def get_default_address(self, user):
        """获取user用户的默认收货地址"""
        try:
            # address = Address.objects.filter(user = user, is_default=True)
            address = self.get(user=user, is_default=True)
        except self.model.DoesNotExist:
            address = None
        return address

    def get_all_address(self, user):
        """获取所有地址"""
        try:
            address = self.filter(user=user)
        except self.model.DoesNotExist:
            address = None
        return address

class Address(BaseMoled):
    user = models.ForeignKey('User', verbose_name='所属账户', on_delete=models.CASCADE)
    receiver = models.CharField(max_length=20, verbose_name='收件人')
    addr = models.CharField(max_length=256, verbose_name='收件地址')
    post_code = models.CharField(max_length=6, null=True, verbose_name='邮政编码')
    phone_num = models.CharField(max_length=11, verbose_name='联系电话')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')

    # 自定义模型管理器类对象
    manager = AddressManager()

    class Meta:
        db_table = "df_address"
        verbose_name = '地址'
        verbose_name_plural = "地址列表"
