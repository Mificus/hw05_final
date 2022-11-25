from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.core.cache import cache

from ..models import Post, Group

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.public_urls = {
            '/': 'posts/index.html',
            f'/posts/{cls.post.id}/': 'posts/post_detail.html',
            f'/group/{cls.group.slug}/': 'posts/group_list.html',
            '/profile/auth/': 'posts/profile.html',
        }
        cls.private_urls = {
            '/create/': 'posts/create_post.html',
            f'/posts/{cls.post.id}/edit/': 'posts/create_post.html',
            '/follow/': 'posts/follow.html'
        }

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_urls_authorized_client(self):
        """Проверяем правильность отдаваемого шаблона,
         в том числе и для authorized_client"""
        self.private_urls.update(self.public_urls)
        for reverse_name, template in self.public_urls.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_unexist_page(self):
        """Тестирование unexist_page"""
        response = self.guest_client.get('/unexist_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_url_exist_public_url_for_guest_client(self):
        """Проверяем доступность public_url"""
        for address, template in self.public_urls.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_exist_private_url_for_guest_client(self):
        """Проверяем редирект private_url for guest_client"""
        for address, template in self.private_urls.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address, follow=True)
                self.assertRedirects(response, f'/auth/login/?next={address}')

    def test_url_exist_url_for_authorized_client(self):
        """Проверяем доступность public_url and
        private_url для authorized_client"""
        self.private_urls.update(self.public_urls)
        for address, template in self.private_urls.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)
