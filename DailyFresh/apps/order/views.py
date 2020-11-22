from django.views import View


class OrderPlaceView(View):
    """订单提交页面"""
    # pass
    def post(self, request):
        user = request.user


class OrderCommitView(View):
    """创建订单"""
    pass

class OrderPayView(View):
    """订单支付"""
    pass


class OrderCheckView(View):
    """订单签收"""
    pass


class OrderCommentView(View):
    """订单评论"""
    pass
