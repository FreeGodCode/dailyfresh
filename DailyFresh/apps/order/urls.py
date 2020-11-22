from django.conf.urls import url

from DailyFresh.apps.order.views import OrderPlaceView, OrderCommitView, OrderPayView, OrderCheckView, OrderCommentView

urlpatterns = [
    url(r'^place/$', OrderPlaceView.as_view(), name='place'), #提交订单页面
    url(r'^commit/$', OrderCommitView.as_view(), name='commit'), #创建订单
    url(r'^pay/$', OrderPayView.as_view(), name='pay'), #订单支付
    url(r'^check/$', OrderCheckView.as_view(), name='check'), #订单签收
    url(r'^comment/$', OrderCommentView.as_view(), name='comment'), #订单评论
]