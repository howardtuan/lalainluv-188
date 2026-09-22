from decimal import Decimal
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from django.test import TestCase, TransactionTestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connections
from django.urls import reverse
from PIL import Image
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from products.models import Product, Category
from .models import CartItem, Order, Wish

TEST_SETTINGS = dict(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                     ALLOWED_HOSTS=['testserver','localhost','127.0.0.1'],
                     SECURE_SSL_REDIRECT=False, ACCOUNT_RATE_LIMITS=False)
CHECKOUT = {'recipient_name':'測試收件人','recipient_phone':'0912345678',
            'recipient_address':'台北市中正區測試路 100 號','note':'測試訂單','agree':'on'}


@override_settings(**TEST_SETTINGS)
class ShopTests(TestCase):
    def setUp(self):
        self.category=Category.objects.create(name='玩偶系列',slug='dolls')
        self.product=Product.objects.create(name='奶油垂耳兔',slug='cream-bunny',category=self.category,
                                           price=890,stock=4,is_new=True,is_hot=True)
        self.user=get_user_model().objects.create_user('shoptest','shoptest@example.com','Lovely-test-9265!')
        self.other=get_user_model().objects.create_user('other','other@example.com','Lovely-test-9265!')
        EmailAddress.objects.create(user=self.user,email=self.user.email,verified=True,primary=True)
        SocialAccount.objects.create(user=self.user,provider='google',uid='shoptest-google')

    def add(self,quantity=1,client=None):
        return (client or self.client).post(reverse('orders:cart_add',args=[self.product.pk]),
                                          {'quantity':quantity},content_type='application/json')

    def test_public_pages_and_empty_states(self):
        for route in ('/','/products/','/products/?q=找不到','/products/category/dolls/',
                      '/products/cream-bunny/','/orders/cart/','/orders/wish/',
                      '/accounts/login/','/accounts/signup/','/accounts/password/reset/','/about/','/notice/','/healthz'):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code,200)

    def test_cart_quantity_count_and_stock_limits(self):
        self.assertEqual(self.add(2).json()['cart_count'],2)
        self.assertEqual(self.add(3).status_code,400)
        self.assertEqual(CartItem.objects.get().quantity,2)
        item=CartItem.objects.get()
        response=self.client.post(reverse('orders:cart_update',args=[item.pk]),{'quantity':4},content_type='application/json')
        self.assertEqual(response.json()['cart_count'],4)
        self.assertEqual(Decimal(response.json()['shipping']),0)

    def test_malformed_quantities_are_rejected(self):
        for value in ('bad',-1,0,1.5,True,100,{},None):
            with self.subTest(value=value):
                self.assertEqual(self.add(value).status_code,400)
        url=reverse('orders:cart_add',args=[self.product.pk])
        self.assertEqual(self.client.post(url,'invalid-json',content_type='application/json').status_code,400)
        self.assertFalse(CartItem.objects.exists())

    def test_cart_requires_post_and_csrf(self):
        url=reverse('orders:cart_add',args=[self.product.pk])
        self.assertEqual(self.client.get(url).status_code,405)
        self.assertEqual(Client(enforce_csrf_checks=True).post(url,{'quantity':1}).status_code,403)

    def test_guests_cannot_change_another_cart(self):
        self.add()
        item=CartItem.objects.get()
        stranger=Client()
        self.assertEqual(stranger.post(reverse('orders:cart_remove',args=[item.pk])).status_code,404)
        self.assertEqual(stranger.post(reverse('orders:cart_update',args=[item.pk]),{'quantity':2}).status_code,404)
        self.assertEqual(CartItem.objects.count(),1)

    def test_members_cannot_change_another_cart(self):
        item=CartItem.objects.create(user=self.other,product=self.product)
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(reverse('orders:cart_remove',args=[item.pk])).status_code,404)

    def test_real_login_merges_guest_cart(self):
        self.add(2)
        CartItem.objects.create(user=self.user,product=self.product,quantity=1)
        response=self.client.post('/accounts/login/',{'login':self.user.email,'password':'Lovely-test-9265!'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(CartItem.objects.get(user=self.user).quantity,3)
        self.assertFalse(CartItem.objects.filter(user__isnull=True).exists())

    def test_checkout_totals_inventory_notification_and_repeat_submission(self):
        self.client.force_login(self.user)
        self.add(2)
        with self.captureOnCommitCallbacks(execute=True):
            response=self.client.post('/orders/checkout/',CHECKOUT)
        self.assertEqual(response.status_code,302)
        order=Order.objects.get()
        self.assertEqual(order.total_amount,Decimal(1840))
        self.assertEqual(order.shipping_fee,Decimal(60))
        self.assertEqual(order.items.get().quantity,2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock,2)
        self.assertFalse(CartItem.objects.exists())
        self.assertIn('奶油垂耳兔',mail.outbox[-1].body)
        self.assertEqual(self.client.get(response.url).status_code,200)
        self.client.post('/orders/checkout/',CHECKOUT)
        self.assertEqual(Order.objects.count(),1)

    def test_stock_change_does_not_create_partial_order(self):
        self.client.force_login(self.user)
        self.add(4)
        Product.objects.filter(pk=self.product.pk).update(stock=1)
        self.client.post('/orders/checkout/',CHECKOUT)
        self.assertFalse(Order.objects.exists())
        self.assertEqual(CartItem.objects.get().quantity,4)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock,1)

    def test_checkout_validates_consent_and_address(self):
        self.client.force_login(self.user)
        self.add()
        for data in ({**CHECKOUT,'agree':''},{**CHECKOUT,'recipient_phone':'abc'},{**CHECKOUT,'recipient_address':'x'}):
            self.assertEqual(self.client.post('/orders/checkout/',data).status_code,200)
            self.assertFalse(Order.objects.exists())

    def test_private_orders_and_wishes(self):
        order=Order.objects.create(user=self.other,recipient_name='Other',recipient_phone='0912345678',recipient_address='台北市')
        wish=Wish.objects.create(user=self.other,title='PRIVATE-WISH-OTHER',description='PRIVATE-DESCRIPTION',wish_type='custom')
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('orders:order_detail',args=[order.order_number])).status_code,404)
        self.assertNotContains(self.client.get('/orders/wish/'),'PRIVATE-WISH-OTHER')
        self.assertEqual(self.client.get(reverse('orders:wish_image',args=[wish.pk])).status_code,404)

    def test_wish_submission_and_invalid_image(self):
        self.client.force_login(self.user)
        data={'wish_type':'product_wish','title':'想找小熊','description':'希望尋找奶茶色小熊','reference_url':'https://example.com/product'}
        response=self.client.post('/orders/wish/create/',data)
        self.assertEqual(response.status_code,302)
        self.assertEqual(Wish.objects.get().user,self.user)
        data['reference_image']=SimpleUploadedFile('unsafe.jpg',b'not an image',content_type='image/jpeg')
        self.assertEqual(self.client.post('/orders/wish/create/',data).status_code,200)
        self.assertEqual(Wish.objects.count(),1)

    def test_authenticated_pages(self):
        self.client.force_login(self.user)
        self.add()
        for route in ('/accounts/profile/','/orders/','/orders/wish/','/orders/wish/create/','/orders/checkout/'):
            self.assertEqual(self.client.get(route).status_code,200)

    def test_filters_search_and_ordering(self):
        Product.objects.create(name='平價兔',slug='budget',category=self.category,price=100,stock=1)
        response=self.client.get('/products/',{'q':'兔','sort':'price_asc'})
        self.assertEqual([p.slug for p in response.context['page_obj']],['budget','cream-bunny'])
        response=self.client.get('/products/',{'collection':'new'})
        self.assertEqual(response.context['page_obj'].paginator.count,1)
        self.product.is_active=False
        self.product.save()
        self.assertEqual(self.add().status_code,404)

    def test_free_shipping_threshold(self):
        from .views import totals
        self.product.price=1000
        item=CartItem(product=self.product,quantity=2)
        self.assertEqual(totals([item])['shipping'],0)
        self.assertEqual(totals([item])['total'],2000)

    def test_profile_cannot_silently_change_login_email(self):
        self.client.force_login(self.user)
        self.client.post('/accounts/profile/',{'first_name':'小花','email':self.other.email,'phone':'0912345678','address':'台北市','line_id':''})
        self.user.refresh_from_db()
        self.assertEqual(self.user.email,'shoptest@example.com')
        self.assertEqual(self.user.first_name,'小花')

    def test_signup_works_without_social_credentials(self):
        response=self.client.post('/accounts/signup/',{'email':'newmember@example.com','password1':'Strong-lovely-9265!','password2':'Strong-lovely-9265!'})
        self.assertEqual(response.status_code,302)
        self.assertTrue(get_user_model().objects.filter(email='newmember@example.com').exists())


@override_settings(**TEST_SETTINGS)
class StockConcurrencyTests(TransactionTestCase):
    def test_two_buyers_cannot_buy_the_last_item(self):
        category=Category.objects.create(name='Test',slug='test')
        product=Product.objects.create(name='Last bunny',slug='last-bunny',category=category,price=500,stock=1)
        clients=[]
        for number in range(2):
            user=get_user_model().objects.create_user(f'buyer{number}',f'buyer{number}@example.com','password12345')
            SocialAccount.objects.create(user=user,provider='google',uid=f'buyer-google-{number}')
            CartItem.objects.create(user=user,product=product,quantity=1)
            client=Client()
            client.force_login(user)
            clients.append(client)
        def purchase(client):
            try:
                return client.post('/orders/checkout/',CHECKOUT).status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses=list(pool.map(purchase,clients))
        self.assertEqual(statuses,[302,302])
        self.assertEqual(Order.objects.count(),1)
        product.refresh_from_db()
        self.assertEqual(product.stock,0)
