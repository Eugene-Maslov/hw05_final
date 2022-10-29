import shutil
import tempfile

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms

from posts.models import Comment, Follow, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(username='Auth')
        cls.authorized_user = User.objects.create_user(username='NameSurname')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug'
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.image_post_form_data = {
            'text': 'Тестовый пост с картинкой',
            'author': cls.user_author,
            'group': cls.group,
            'image': uploaded
        }
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user_author,
            group=cls.group,
            image=uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.authorized_user)
        self.post_author = Client()
        self.post_author.force_login(self.user_author)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        pages_names_templates = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': 'NameSurname'}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': '1'}):
                'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': '1'}):
                'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html'
        }
        for reverse_name, template in pages_names_templates.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.post_author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.assertIn('form', response.context)
        form_fields_create = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields_create.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.post_author.get(
            reverse('posts:post_edit', kwargs={'post_id': '1'}))
        self.assertIn('form', response.context)
        self.assertIn('is_edit', response.context)
        self.assertTrue(response.context.get('is_edit'))
        form_fields_edit = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields_edit.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': '1'}))
        set_form_fields = {
            'post': PostPagesTests.post,
            'author_posts_number': Post.objects.count(),
        }
        for value, expected in set_form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get(value)
                self.assertEqual(form_field, expected)

    def test_index_page_show_correct_context(self):
        response = self.client.get(reverse('posts:index'))
        posts = response.context.get('page_obj').object_list
        for post in posts:
            with self.subTest(post=post):
                self.assertEqual(post, self.post)

    def test_group_list_page_show_correct_context(self):
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}))
        self.assertEqual(response.context.get('group'), self.group)
        posts = response.context.get('page_obj').object_list
        for post in posts:
            with self.subTest(post=post):
                self.assertEqual(post, self.post)

    def test_profile_page_show_correct_context(self):
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': 'Auth'}))
        self.assertEqual(response.context.get('user_obj'), self.user_author)
        self.assertEqual(response.context.get('posts_number'), 1)
        posts = response.context.get('page_obj').object_list
        for post in posts:
            with self.subTest(post=post):
                self.assertEqual(post, self.post)

    def test_index_page_show_correct_context_image(self):
        self.authorized_client.post(
            reverse('posts:post_create'),
            self.image_post_form_data,
            follow=True
        )
        pages_to_test = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}),
            reverse('posts:profile', kwargs={'username': 'NameSurname'})
        ]
        for value in pages_to_test:
            response = self.authorized_client.get(value)
            posts = response.context.get('page_obj').object_list
            for post in posts:
                with self.subTest(post=post):
                    self.assertEqual(post.image, self.post.image)

    def test_post_detail_page_show_correct_context_image(self):
        self.authorized_client.post(
            reverse('posts:post_create'),
            self.image_post_form_data,
            follow=True
        )
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': '1'}))
        post_obj = response.context.get('post')
        self.assertEqual(post_obj.image, self.post.image)

    def test_post_detail_page_show_correct_comment_context(self):
        form = {'text': 'Комментарий'}
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': '1'}),
            form,
            follow=True
        )
        self.assertEqual(Comment.objects.first().text, form['text'])

    def test_index_cache(self):
        """Проверка хранения и очищения кэша для index."""
        self.assertNotEqual(Post.objects.count(), 0)
        initial_response = self.authorized_client.get(reverse('posts:index'))
        initial_content = initial_response.content
        Post.objects.get(pk=1).delete()
        new_response = self.authorized_client.get(reverse('posts:index'))
        cached_content = new_response.content
        self.assertEqual(cached_content, initial_content)
        cache.clear()
        updated_response = self.authorized_client.get(reverse('posts:index'))
        real_content = updated_response.content
        self.assertNotEqual(real_content, cached_content)

    def test_new_posts_in_feed_after_subscription(self):
        response = self.authorized_client.get(reverse('posts:follow_index'))
        no_posts = response.context.get('page_obj').object_list
        self.assertQuerysetEqual(no_posts, [])
        Follow.objects.create(user=self.authorized_user,
                              author=self.user_author)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        new_posts = response.context.get('page_obj').object_list
        self.assertNotEqual(no_posts, new_posts)
        for post in new_posts:
            with self.subTest(post=post):
                self.assertEqual(post, self.post)

    def test_no_new_posts_in_feed_without_subscription(self):
        response = self.post_author.get(reverse('posts:follow_index'))
        no_posts = response.context.get('page_obj').object_list
        self.assertQuerysetEqual(no_posts, [])
        self.post_author.post(
            reverse('posts:post_create'),
            self.image_post_form_data,
            follow=True
        )
        response = self.post_author.get(reverse('posts:follow_index'))
        still_no_posts = response.context.get('page_obj').object_list
        self.assertQuerysetEqual(no_posts, still_no_posts)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Auth')

        cls.group_1 = Group.objects.create(
            title='Тестовая группа № 1',
            slug='test-slug_1'
        )
        cls.group_2 = Group.objects.create(
            title='Тестовая группа № 2',
            slug='test-slug_2'
        )
        cls.all_posts = [
            Post.objects.create(
                text=f'Тестовый пост № {i+1}',
                author=cls.user,
                group=cls.group_1,
            ) for i in range(13)
        ]

    def setUp(self):
        self.client = Client()
        cache.clear()

    def test_first_pages_contain_ten_records(self):
        pages_to_test = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'test-slug_1'}),
            reverse('posts:profile', kwargs={'username': 'Auth'})
        ]
        for value in pages_to_test:
            response = self.client.get(value)
            self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_pages_contain_three_records(self):
        pages_to_test = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'test-slug_1'}),
            reverse('posts:profile', kwargs={'username': 'Auth'})
        ]
        for value in pages_to_test:
            response = self.client.get(value + '?page=2')
            self.assertEqual(len(response.context['page_obj']), 3)

    def test_new_post_appearance_on_correct_pages(self):
        form = {
            'text': self.all_posts[0].text,
            'group': self.all_posts[0].group,
        }
        self.client.post(reverse('posts:post_create'), form)
        new_post_on_pages = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'test-slug_1'}),
            reverse('posts:profile', kwargs={'username': 'Auth'})
        ]
        for value in new_post_on_pages:
            response = self.client.get(value)
            posts = response.context.get('page_obj').object_list
            for post in posts:
                with self.subTest(post=post):
                    if post == self.all_posts[0]:
                        self.assertEqual(post, self.all_posts[0])

    def test_new_post_not_in_wrong_group(self):
        form = {
            'text': self.all_posts[0].text,
            'group': self.all_posts[0].group,
        }
        self.client.post(reverse('posts:post_create'), form)
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug_2'}))
        posts = response.context.get('page_obj').object_list
        for post in posts:
            with self.subTest(post=post):
                self.assertNotEqual(post, self.all_posts[0])
