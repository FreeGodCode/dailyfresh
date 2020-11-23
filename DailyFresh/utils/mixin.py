from django.contrib.auth.decorators import login_required
from django.views.generic.base import View


class LoginRequiredView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        # 调View类中的as_view
        view = super(LoginRequiredView, cls).as_view(**initkwargs)
        # 调用login_required()装饰器函数
        return login_required(view)


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        # 使用super调用as_view()
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        # 调用login_required()装饰器函数
        return login_required(view)