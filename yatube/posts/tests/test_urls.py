from django.core.cache import cache
from django.test import Client, TestCase

from http import HTTPStatus

from posts.models import Group, Post, User


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(username='Auth')
        cls.authorized_user = User.objects.create_user(username='NameSurname')

        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание группы',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user_author,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.authorized_user)
        self.post_author = Client()
        self.post_author.force_login(self.user_author)
        cache.clear()

    def test_urls_exist_at_desired_location(self):
        """Страницы доступны любому пользователю."""
        url_names = [
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{self.authorized_user}/',
            f'/posts/{self.post.id}/'
        ]
        for url in url_names:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_url_exists_at_desired_location_authorized(self):
        """Страницы доступны авторизованному пользователю."""
        url_names = [
            '/create/',
            '/follow/'
        ]
        for url in url_names:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_url_exists_at_desired_location_author(self):
        """Страница /posts/1/edit/ доступна авторизованному
        пользователю - автору поста.
        """
        response = self.post_author.get('/posts/1/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_redirect_on_admin_login(self):
        """Страницы перенаправят пользователя на страницу логина."""
        url_names = [
            '/create/',
            '/follow/',
            f'/posts/{self.post.id}/edit/',
            f'/posts/{self.post.id}/comment/',
            f'/profile/{self.user_author}/follow/',
            f'/profile/{self.user_author}/unfollow/'
        ]
        for url in url_names:
            with self.subTest(url=url):
                response = self.guest_client.get(url, follow=True)
                self.assertRedirects(response, f'/auth/login/?next={url}')

    def test_urls_redirect_authorized_on_(self):
        """Страница /posts/1/edit/ перенапрявляет авторизованного
        пользователя, но не автора поста, на страницу поста.
        """
        response = self.authorized_client.get(f'/posts/{self.post.id}/edit/',
                                              follow=True)
        self.assertRedirects(response, f'/posts/{self.post.id}/')

    def test_unexisting_page_url_at_desired_location(self):
        """Страница /unexisting_page/ недоступна любому пользователю."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/profile/NameSurname/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            '/posts/1/edit/': 'posts/create_post.html',
            '/unexisting_page/': 'core/404.html',
            '/follow/': 'posts/follow.html'
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.post_author.get(url)
                self.assertTemplateUsed(response, template)
