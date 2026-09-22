from io import BytesIO, StringIO
from tempfile import TemporaryDirectory
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image
from allauth.socialaccount.models import SocialAccount
from core.models import Banner
from products.models import Product, Category
from orders.models import Order, OrderItem, CartItem, Wish


def upload(name='product.png'):
    output = BytesIO()
    Image.new('RGB', (64, 64), '#c7ae99').save(output, 'PNG')
    return SimpleUploadedFile(name, output.getvalue(), content_type='image/png')


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', ACCOUNT_RATE_LIMITS=False)
class BackofficeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.staff = User.objects.create_user('manager-test', 'manager-test@example.com', 'Manager-test-9265!', is_staff=True)
        cls.customer = User.objects.create_user('customer', 'customer@example.com', 'Customer-test-9265!')
        SocialAccount.objects.create(user=cls.customer, provider='google', uid='customer-google')
        cls.category = Category.objects.create(name='拉拉熊玩偶', slug='dolls')
        cls.product = Product.objects.create(name='拉拉熊測試玩偶', slug='bear-test', category=cls.category, price=500, stock=10, image='products/test.png')
        cls.banner = Banner.objects.create(title='測試廣告', image='banners/test.png')
        cls.order = Order.objects.create(user=cls.customer, customer_email=cls.customer.email,
            recipient_name='測試收件人', recipient_phone='0912345678', recipient_address='台北市測試路 100 號',
            total_amount=1060, shipping_fee=60, note='請小心包裝')
        OrderItem.objects.create(order=cls.order, product=cls.product, product_name=cls.product.name, quantity=2, price=500)
        cls.wish = Wish.objects.create(user=cls.customer, wish_type='product_wish', title='日本限定拉拉熊', description='想找的商品')

    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        override = override_settings(MEDIA_ROOT=temp.name)
        override.enable()
        self.addCleanup(override.disable)

    def staff_login(self):
        self.client.force_login(self.staff)

    def product_data(self, **extra):
        self.product.refresh_from_db()
        return {'name': self.product.name, 'category': self.category.pk, 'description': '商品說明',
                'price': 500, 'stock': 10, 'is_active': 'on', 'version': self.product.updated_at.isoformat(),
                'images-TOTAL_FORMS': 1, 'images-INITIAL_FORMS': 0, 'images-MIN_NUM_FORMS': 0, 'images-MAX_NUM_FORMS': 10, 'images-0-order': 0, **extra}

    def order_data(self, status, **extra):
        self.order.refresh_from_db()
        return {'status': status, 'tracking_number': '', 'admin_note': '', 'version': self.order.updated_at.isoformat(), **extra}

    def test_guests_and_customers_cannot_enter_management(self):
        url = reverse('backoffice:products')
        response = self.client.get(url)
        self.assertRedirects(response, '/manage/login/?next=/manage/products/')
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(reverse('backoffice:product_edit', args=[self.product.pk]), {'stock': 99}).status_code, 403)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)

    def test_staff_password_login_is_exempt_from_social_binding(self):
        response = self.client.post('/manage/login/', {'username': self.staff.username, 'password': 'Manager-test-9265!'}, follow=True)
        self.assertRedirects(response, '/manage/')
        self.assertContains(response, '管理總覽')
        self.assertFalse(self.staff.socialaccount_set.exists())
        self.assertEqual(self.client.get('/manage/logout/').status_code, 405)

    def test_customer_credentials_do_not_log_in_to_management(self):
        response = self.client.post('/manage/login/', {'username': self.customer.username, 'password': 'Customer-test-9265!'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_staff_login_rejects_external_next(self):
        response = self.client.post('/manage/login/', {'username': self.staff.username, 'password': 'Manager-test-9265!', 'next': 'https://evil.example'})
        self.assertRedirects(response, '/manage/')

    def test_every_management_page_uses_the_storefront_css(self):
        self.staff_login()
        for url in ('/manage/', '/manage/products/', '/manage/products/new/', f'/manage/products/{self.product.pk}/',
                    '/manage/orders/', f'/manage/orders/{self.order.order_number}/', '/manage/banners/',
                    '/manage/banners/new/', f'/manage/banners/{self.banner.pk}/', '/manage/categories/',
                    '/manage/categories/new/', '/manage/wishes/', f'/manage/wishes/{self.wish.pk}/', '/manage/settings/'):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'base.html')
                self.assertContains(response, 'id="sidebar"', count=1)
                self.assertContains(response, '/static/css/style')
                self.assertIn('no-store', response.headers['Cache-Control'])

    def test_staff_writes_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.staff)
        self.assertEqual(client.post('/manage/products/new/', self.product_data()).status_code, 403)

    def test_add_product_with_image_and_long_name(self):
        self.staff_login()
        response = self.client.post('/manage/products/new/', self.product_data(name='拉拉熊新品' * 15, image=upload(), version=''))
        self.assertEqual(response.status_code, 302, (response.context['form'].errors, response.context['images'].errors) if response.status_code == 200 else '')
        self.assertRedirects(response, '/manage/products/')
        new = Product.objects.exclude(pk=self.product.pk).get()
        self.assertTrue(new.image.name.startswith('products/'))
        self.assertLessEqual(len(new.slug), 50)
        self.assertContains(self.client.get('/products/'), new.name)

    def test_edit_stock_and_reject_stale_submission(self):
        self.staff_login()
        stale = self.product_data(stock=99)
        url = reverse('backoffice:product_edit', args=[self.product.pk])
        self.assertEqual(self.client.post(url, self.product_data(stock=7)).status_code, 302)
        response = self.client.post(url, stale)
        self.assertContains(response, '重新載入')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 7)

    def test_invalid_price_and_image_do_not_create_product(self):
        self.staff_login()
        for data in (self.product_data(price=-1, image=upload()), self.product_data(image=SimpleUploadedFile('fake.png', b'not-image', content_type='image/png'))):
            self.assertEqual(self.client.post('/manage/products/new/', data).status_code, 200)
        self.assertEqual(Product.objects.count(), 1)

    def test_edit_banner_image_mobile_image_order_and_homepage_first_slide(self):
        self.staff_login()
        response = self.client.post(reverse('backoffice:banner_edit', args=[self.banner.pk]), {
            'title': '管理員更換的第一張', 'description': '自己的廣告', 'image': upload('new-banner.png'),
            'mobile_image': upload('mobile-banner.png'), 'order': 0, 'button_text': '立即看看', 'is_active': 'on',
        })
        self.assertRedirects(response, '/manage/banners/')
        self.banner.refresh_from_db()
        home = self.client.get('/')
        self.assertContains(home, '管理員更換的第一張')
        self.assertContains(home, self.banner.image.url)
        self.assertContains(home, self.banner.mobile_image.url)
        self.assertNotContains(home, '/static/images/rilakkuma/hero.jpg')

    def test_disable_all_banners_hides_carousel_without_old_fallback(self):
        Banner.objects.update(is_active=False)
        self.assertNotContains(self.client.get('/'), 'class="hero-slide ')

    def test_banner_rejects_unsafe_link(self):
        self.staff_login()
        response = self.client.post('/manage/banners/new/', {'title': 'Unsafe', 'image': upload(), 'order': 0,
            'button_text': 'test', 'link': 'javascript:alert(1)'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Banner.objects.count(), 1)

    def test_full_customer_order_is_saved_and_visible_to_staff_without_payment(self):
        self.client.force_login(self.customer)
        CartItem.objects.create(user=self.customer, product=self.product, quantity=2)
        response = self.client.post('/orders/checkout/', {'recipient_name': '完整訂單測試', 'recipient_phone': '0987654321',
            'recipient_address': '台北市信義區測試街 55 號', 'note': '星期六送達', 'agree': 'on'})
        self.assertEqual(response.status_code, 302)
        order = Order.objects.exclude(pk=self.order.pk).get()
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.customer_email, self.customer.email)
        self.assertEqual(order.items.get().quantity, 2)
        self.assertEqual(order.total_amount, 1060)
        self.staff_login()
        detail = self.client.get(reverse('backoffice:order_detail', args=[order.order_number]))
        for value in (order.customer_email, order.recipient_name, order.recipient_phone, order.recipient_address, order.note, self.product.name):
            self.assertContains(detail, value)

    def test_cancel_restores_stock_once_and_records_history(self):
        self.staff_login()
        url = reverse('backoffice:order_detail', args=[self.order.order_number])
        for _ in range(2):
            self.assertEqual(self.client.post(url, self.order_data('cancelled')).status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 12)
        self.assertEqual(self.order.status_logs.count(), 1)
        self.assertContains(self.client.post(url, self.order_data('confirmed')), '無法直接切換')

    def test_order_status_sequence_and_internal_notes_are_private(self):
        self.staff_login()
        url = reverse('backoffice:order_detail', args=[self.order.order_number])
        self.assertContains(self.client.post(url, self.order_data('completed')), '無法直接切換')
        for status in ('confirmed', 'shipped', 'completed'):
            self.assertEqual(self.client.post(url, self.order_data(status, admin_note='INTERNAL-SECRET-NOTE', tracking_number='SHIP1234')).status_code, 302)
        self.client.force_login(self.customer)
        response = self.client.get(reverse('orders:order_detail', args=[self.order.order_number]))
        self.assertContains(response, 'SHIP1234')
        self.assertNotContains(response, 'INTERNAL-SECRET-NOTE')

    def test_member_cannot_read_another_order(self):
        other = get_user_model().objects.create_user('stranger', 'stranger@example.com', 'Stranger-9265!')
        SocialAccount.objects.create(user=other, provider='line', uid='stranger-line')
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse('orders:order_detail', args=[self.order.order_number])).status_code, 404)

    def test_wish_reply_is_visible_to_owner(self):
        self.staff_login()
        self.assertEqual(self.client.post(reverse('backoffice:wish_edit', args=[self.wish.pk]), {'status': 'quoted', 'admin_reply': '已找到商品，請查看報價。'}).status_code, 302)
        self.client.force_login(self.customer)
        self.assertContains(self.client.get('/orders/wish/'), '已找到商品，請查看報價。')

    @override_settings(ADMIN_USERNAME='env-owner', ADMIN_PASSWORD='Unique-owner-pass-9265!', ADMIN_EMAIL='env-owner@example.com')
    def test_env_admin_sync_is_idempotent_and_hashes_password(self):
        output = StringIO()
        call_command('sync_admin', stdout=output)
        call_command('sync_admin', stdout=output)
        owner = get_user_model().objects.get(username='env-owner')
        self.assertTrue(owner.is_staff)
        self.assertTrue(owner.check_password('Unique-owner-pass-9265!'))
        self.assertNotEqual(owner.password, 'Unique-owner-pass-9265!')
        self.assertNotIn('Unique-owner-pass-9265!', output.getvalue())

    @override_settings(ADMIN_USERNAME='customer', ADMIN_PASSWORD='Unique-owner-pass-9265!', ADMIN_EMAIL='env-owner@example.com')
    def test_env_sync_never_promotes_existing_customer(self):
        with self.assertRaises(CommandError): call_command('sync_admin', stdout=StringIO())
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_staff)
