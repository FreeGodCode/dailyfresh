from django.conf.urls import url

from DailyFresh.apps.cart.views import CartInfoView, CartAddView, CartUpdateView, CartDeleteView

urlpatterns = [
    url(r'^$', CartInfoView.as_view(), name='display'),
    url(r'^add/$', CartAddView.as_view(), name='add'),
    url(r'^update/$', CartUpdateView.as_view(), name='update'),
    url(r'^delete/$', CartDeleteView.as_view(), name='delete'),
]