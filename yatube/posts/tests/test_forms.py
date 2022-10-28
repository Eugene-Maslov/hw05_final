import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Follow, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Auth')
        cls.follower_user = User.objects.create_user(username='Follower')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.post_author = Client()
        self.post_author_follower = Client()
        self.post_author.force_login(PostFormTests.user)
        self.post_author_follower.force_login(PostFormTests.follower_user)

    def test_post_create_authorized(self):
        posts_count = Post.objects.count()
        form = {
            'text': 'Новая запись',
            'group': self.group.id,
        }
        self.post_author.post(reverse('posts:post_create'), form, follow=True)
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(Post.objects.first().group.id, self.group.id)
        self.assertEqual(Post.objects.first().text, 'Новая запись')

    def test_post_create_guest(self):
        posts_count_initial = Post.objects.count()
        form = {
            'text': 'Новая запись',
            'group': self.group.id,
        }
        response = self.guest_client.post(reverse('posts:post_create'),
                                          form, follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')
        self.assertEqual(Post.objects.count(), posts_count_initial)
        self.assertFalse(Post.objects.filter(text='Новая запись',).exists())

    def test_post_edit(self):
        self.test_post_create_authorized()
        posts_count = Post.objects.count()
        post_id_initial = Post.objects.first().id
        form_edit = {
            'text': 'Отредактировано',
            'group': self.group.id,
        }
        self.post_author.post(
            reverse('posts:post_edit', kwargs={'post_id': post_id_initial}),
            form_edit,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(Post.objects.first().id, post_id_initial)
        self.assertEqual(Post.objects.first().text, 'Отредактировано')

    def test_post_create_authorized_image(self):
        posts_count = Post.objects.count()
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
        image_post_form_data = {
            'text': 'Пост с картинкой',
            'group': self.group.id,
            'image': uploaded
        }
        self.post_author.post(
            reverse('posts:post_create'),
            image_post_form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(Post.objects.first().text, 'Пост с картинкой')
        self.assertEqual(Post.objects.first().image, 'posts/small.gif')

    def test_add_comment_authorized(self):
        self.test_post_create_authorized()
        comments_count = Comment.objects.count()
        form = {'text': 'Тестовый комментарий'}
        self.post_author.post(
            reverse('posts:add_comment', kwargs={'post_id': '1'}),
            form,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertEqual(Comment.objects.first().text, 'Тестовый комментарий')

    def test_add_comment_guest(self):
        self.test_post_create_authorized()
        comments_count = Comment.objects.count()
        form = {'text': 'Тестовый комментарий'}
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': '1'}),
            form,
            follow=True
        )
        self.assertRedirects(response,
                             f'/auth/login/?next=/posts/'
                             f'{Post.objects.first().id}/comment/')
        self.assertEqual(Comment.objects.count(), comments_count)
        self.assertFalse(Comment.objects.filter
                         (text='Тестовый комментарий',).exists())

    def test_subscription_check(self):
        Follow.objects.create(user=self.follower_user, author=self.user)
        self.assertTrue(Follow.objects.filter(user=self.follower_user,
                        author=self.user).exists())
        Follow.objects.filter(user=self.follower_user,
                              author=self.user).delete()
        self.assertFalse(Follow.objects.filter(user=self.follower_user,
                         author=self.user).exists())
