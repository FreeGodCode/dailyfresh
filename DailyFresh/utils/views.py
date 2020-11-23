from django.contrib.auth.decorators import login_required


class LoginRequiredMixin(object):
    """提供要求用户登录的功能"""
    @classmethod
    def as_view(cls, *args, **kwargs):
        view = super(LoginRequiredMixin, cls).as_view(*args, **kwargs)
        return login_required(view)