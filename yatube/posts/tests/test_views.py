import shutil
import tempfile
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Post, Group, Follow

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='auth')
        cls.user_2 = User.objects.create_user(username='Test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded,
        )
        cls.public_urls = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:post_detail', kwargs={'post_id':
                    cls.post.id}): 'posts/post_detail.html',
            reverse('posts:group_list', kwargs={'slug':
                    cls.group.slug}): 'posts/group_list.html',
            reverse('posts:profile', kwargs={'username':
                    cls.post.author}): 'posts/profile.html',
        }
        cls.private_urls = {
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id':
                    cls.post.id}): 'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostViewTests.user)
        cache.clear()

    def test_pages_uses_correct_public_url(self):
        """URL-адрес использует соответствующий шаблон.
        В том числе и для пользователя для public_url"""
        for reverse_name, template in self.public_urls.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_pages_uses_correct_private_url(self):
        """URL-адрес использует соответствующий шаблон.
         private_url for authoized_cient """
        for reverse_name, template in self.private_urls.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_page_create_show_correct_context(self):
        """Проверяем словарь контекста для create"""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_posts_index_page_show_correct_context(self):
        """Проверяем, что словарь context страницы index
        содержит ожидаемый контекст"""
        response = self.guest_client.get(reverse('posts:index'))
        expected = list(Post.objects.all()[:10])
        self.assertEqual(list(response.context['page_obj']), expected)
        self.assertEqual(response.context['page_obj'][0].image,
                         self.post.image)

    def test_posts_group_list_pages_show_correct_context(self):
        """Проверяем, что словарь context страницы group_list
        содержит ожидаемый контекст"""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        expected = list(Post.objects.filter(group_id=self.group.id))
        self.assertEqual(list(response.context['page_obj']), expected)
        self.assertEqual(response.context['page_obj'][0].image,
                         self.post.image)

    def test_posts_profile_pages_show_correct_context(self):
        """Проверяем, что словарь context страницы profile
        содержит ожидаемый контекст"""
        response = self.guest_client.get(
            reverse('posts:profile', args=(self.post.author,))
        )
        expected = list(Post.objects.filter(author_id=self.user.id)[:10])
        self.assertEqual(list(response.context['page_obj']), expected)
        self.assertEqual(response.context['page_obj'][0].image,
                         self.post.image)

    def test_posts_post_detail_pages_show_correct_context(self):
        """Проверяем, что словарь context страницы post_detail
        содержит ожидаемый контекст"""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(response.context.get('post').author, self.post.author)
        self.assertEqual(response.context.get('post').group, self.post.group)
        self.assertEqual(response.context.get('post').image, self.post.image)
        self.assertEqual(response.context.get('post').comments,
                         self.post.comments)

    def tests_posts_post_exist_authorized_client_private_url(self):
        """Проверяем доступность authorized_client
        для private_urls"""
        for address, template in self.private_urls.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def tests_posts_post_exist_authorized_client_public_url(self):
        """Проверяем доступность authorized_client
        для public_urls"""
        for address, template in self.public_urls.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def tests_posts_post_exist_guest_client_public_urls(self):
        """Проверяем доступность guest_client для public_urls"""
        for address, template in self.public_urls.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def tests_posts_post_exist_guest_client_private_urls(self):
        """Проверяем redirect для guest_client_private_urls"""
        for address, template in self.private_urls.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertRedirects(response, f'/auth/login/?next={address}')

    def test_posts_added_correctly(self):
        """Пост при создании добавлен корректно"""
        posts_urls = {
            reverse('posts:index'): Post.objects.get(group=self.post.group),
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): Post.objects.get(group=self.post.group),
            reverse(
                'posts:profile', kwargs={'username': self.post.author}
            ): Post.objects.get(group=self.post.group)
        }
        for value, expected in posts_urls.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                posts_urls = response.context['page_obj']
                self.assertIn(expected, posts_urls)

    def test_posts_added_2_correctly(self):
        """Проверка, что пост не попал в чужую группу"""

        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        response_context = response.context['page_obj']
        self.assertNotIn(response, response_context)


# Тест паджинатора
POSTS_TESTS_COUNT: int = 13


class PaginatorViewsTest(TestCase):
    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='auth')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group'
        )
        bulk_post: list = []
        for i in range(POSTS_TESTS_COUNT):
            bulk_post.append(
                Post(text=f'Тестовый текст {i}',
                     group=self.group,
                     author=self.user,
                     )
            )
        Post.objects.bulk_create(bulk_post)

    def test_first_page_contains_ten_records(self):
        cache.clear()
        response = self.client.get(reverse('posts:index'))
        # Проверка: количество постов на первой странице равно 10.
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_records(self):
        # Проверка: на второй странице должно быть три поста.
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)


class FollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_author = User.objects.create(username='author')
        cls.post_follower = User.objects.create(username='follower')
        cls.post = Post.objects.create(text='Подпишись на меня',
                                       author=cls.post_author,)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.post_follower)
        self.follower_client = Client()
        self.follower_client.force_login(self.post_author)
        cache.clear()

    def test_follow_on_user(self):
        """Проверка подписки на пользователя."""
        count_follow = Follow.objects.count()
        self.follower_client.post(
            reverse('posts:profile_follow',
                    kwargs={'username': self.post_follower}))
        follow = Follow.objects.all().latest('id')
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        self.assertEqual(follow.author_id, self.post_follower.id)
        self.assertEqual(follow.user_id, self.post_author.id)

    def test_unfollow_on_user(self):
        """Проверка отписки от пользователя."""
        Follow.objects.create(user=self.post_author,
                              author=self.post_follower)
        count_follow = Follow.objects.count()
        self.follower_client.post(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.post_follower}))
        self.assertEqual(Follow.objects.count(), count_follow - 1)

    def test_follow_on_authors(self):
        """Проверка записей у тех кто подписан."""
        post = Post.objects.create(author=self.post_author,
                                   text="Подпишись на меня")
        Follow.objects.create(user=self.post_follower,
                              author=self.post_author)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertIn(post, response.context['page_obj'].object_list)

    def test_notfollow_on_authors(self):
        """Проверка записей у тех кто не подписан."""
        post = Post.objects.create(author=self.post_author,
                                   text="Подпишись на меня")
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertNotIn(post, response.context['page_obj'].object_list)

    def test_follow_myself(self):
        """Проверка невозможности подписаться на себя"""
        self.follower_client.post(
            reverse('posts:profile_follow',
                    kwargs={'username': self.post_author.username}))
        follow = Follow.objects.filter(
            author=self.post_author, user=self.post_author
        )
        self.assertFalse(follow.exists())


class TestCache(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='title',
            slug='slug',
            description='description'
        )
        cls.post = Post.objects.create(
            text='Текст поста',
            group=cls.group,
            author=cls.user,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_cache_index(self):
        """Проверка хранения и очищения кэша для index."""
        response = self.authorized_client.get(reverse('posts:index'))
        posts = response.content
        Post.objects.create(text='Текст поста',
                            author=self.user,)
        response_old = self.authorized_client.get(reverse('posts:index'))
        old_posts = response_old.content
        self.assertEqual(old_posts, posts)
        cache.clear()
        response_new = self.authorized_client.get(reverse('posts:index'))
        new_posts = response_new.content
        self.assertNotEqual(old_posts, new_posts)
