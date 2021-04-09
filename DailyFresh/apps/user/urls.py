from django.conf.urls import url

# urlpatterns = [
#     url(r'^register/', views.register, name='register'),
#     url(r'^login/', views.login, name='login'),
#     url(r'^forget/', views.forget_password, name='forget_password'),
#     url(r'^reset/', views.reset_password, name='reset_password'),
# ]

from DailyFresh.apps.user.views import UserInfoView, RegisterView, ActiveView, LoginView, LogoutView, UserOrderView, \
    AddressView

urlpatterns = [
    # 用户中心
    url(r'^$', UserInfoView.as_view(), name='user'),

    url(r'^register/$', RegisterView.as_view(), name='register'),
    # 激活
    url(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),
    url(r'^login/$', LoginView.as_view(), name='login'),
    url(r'^logout/$', LogoutView.as_view(), name='logout'),

    url(r'^order/(?P<page>(\d)*)$', UserOrderView.as_view(), name='order'),
    url(r'^address/$', AddressView.as_view(), name='address'),

]