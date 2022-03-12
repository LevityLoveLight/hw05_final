import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post


User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='slug',
            description='Тестовое описание',
        )
        cls.user = User.objects.create_user(username='HasNoName')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.guest_client = Client()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        '''Проверяем, что авторизованный пользователь может создать пост'''
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
        form_data = {
            'text': 'test',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.user.username}))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='test',
                group=self.group,
                image='posts/small.gif'
            ).exists()
        )

    def test_guest_client_try_to_create_post(self):
        '''Проверяем, что неавторизованный пользователь
        не может создать пост'''
        posts_count = Post.objects.count()
        form_data = {
            'text': 'test',
            'group': self.group.id,
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, '/auth/login/?next=/create/')
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertFalse(
            Post.objects.filter(
                text='test',
                group=self.group,
            ).exists()
        )

    def test_post_edit(self):
        '''Проверяем, что авторизованный пользователь
        может редакртировать пост'''
        new_group = Group.objects.create(
            title='Новая тестовая группа',
            slug='slug-test',
            description='Тестовое описание для новой группы',
        )
        post = Post.objects.create(
            author=self.user,
            text='Тестовый текст',
            group=self.group,
        )
        form_data = {
            'text': 'Новый тестовый текст',
            'group': new_group.id
        }
        self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )
        changed_post = Post.objects.get(id=post.id)
        self.assertNotEqual(post.text, changed_post.text)
        self.assertNotEqual(post.group.id, changed_post.group.id)

    def test_guest_client_try_to_edit_post(self):
        '''Проверяем, что неавторизованный пользователь
        не может редактировать пост'''
        new_group = Group.objects.create(
            title='Новая тестовая группа',
            slug='slug-test',
            description='Тестовое описание для новой группы',
        )
        post = Post.objects.create(
            author=self.user,
            text='Тестовый текст',
            group=self.group,
        )
        form_data = {
            'text': 'Новый тестовый текст',
            'group': new_group,
        }
        response = self.guest_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, '/auth/login/?next=/posts/1/edit/')

    def test_authorized_client_try_to_make_a_comment(self):
        '''Проверяем, что авторизованный пользователь
        может создать комменнтарий'''
        comments_count = Comment.objects.count()
        post = Post.objects.create(
            author=self.user,
            text='Тестовый текст',
            group=self.group,
        )
        form_data = {
            'text': 'test comment',
        }
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)

    def test_guest_client_try_to_make_a_comment(self):
        '''Проверяем, что неавторизованный пользователь
        может создать комменнтарий'''
        comments_count = Comment.objects.count()
        post = Post.objects.create(
            author=self.user,
            text='Тестовый текст',
            group=self.group,
        )
        form_data = {
            'text': 'test comment',
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count)
        self.assertRedirects(response, '/auth/login/?next=/posts/1/comment/')
