import shutil
import tempfile

from django import forms
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.cache import cache

from ..models import Group, Follow, Post


User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    PAGE_ONE_POST_COUNT = 10
    PAGE_TWO_POST_COUNT = 3
    POST_COUNT = PAGE_ONE_POST_COUNT + PAGE_TWO_POST_COUNT
    NAME = 'HasNoName'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=PostPagesTests.NAME)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='slug',
            description='Тестовое описание',
        )
        cls.group_test = Group.objects.create(
            title='Тестовая группа 2',
            slug='slug-test',
            description='Тестовое описание 2',
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
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
            image=uploaded,
        )
        cls.privet_urls = (
            (f'/posts/{PostPagesTests.post.pk}/edit/',
             'posts/create_post.html'),
            ('/create/', 'posts/create_post.html'),
        )
        cls.paginator_urls = (
            ('/', 'posts/index.html'),
            (f'/group/{PostPagesTests.group.slug}/', 'posts/group_list.html'),
            (f'/profile/{PostPagesTests.user}/', 'posts/profile.html'),
        )
        cls.public_urls = (
            (f'/posts/{PostPagesTests.post.pk}/', 'posts/post_detail.html'),
        ) + cls.paginator_urls

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)

    def test_urls_uses_by_authorized_client_correct_template(self):
        """Views при авторизованном пользователе
        использует соответствующий шаблон."""
        for reverse_name, template in self.privet_urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_urls_uses_by_guest_client_correct_template(self):
        """Views при неавторизованном пользователе
        использует соответствующий шаблон."""
        for reverse_name, template in self.public_urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def check_post_fields(self, post_object):
        self.assertEqual(post_object.text, self.post.text)
        self.assertEqual(post_object.author, self.post.author)
        self.assertEqual(post_object.group, self.post.group)
        self.assertEqual(post_object.pk, self.post.pk)
        self.assertEqual(post_object.image, self.post.image)

    def test_index_page_show_correct_context(self):
        """Шаблон из public_urls сформирован с правильным контекстом."""
        for reverse_name, template in self.public_urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                if 'page_obj' in response.context:
                    post_object = response.context['page_obj'][0]
                else:
                    post_object = response.context['post']
                self.check_post_fields(post_object)

    def test_privet_urls_show_correct_context(self):
        """Шаблоны post_edit и create_post
        сформированы с правильным контекстом."""
        for reverse_name, template in self.privet_urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                form_fields = {
                    'text': forms.fields.CharField,
                    'group': forms.fields.ChoiceField,
                }
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = response.context.get(
                            'form'
                        ).fields.get(value)
                        self.assertIsInstance(form_field, expected)

    def test_post_not_in_wrong_group(self):
        """Проверяем, что пост попал в нужную группу"""
        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': 'slug'}
        ))
        post_object = response.context['page_obj'][0]
        group = post_object.group
        self.assertEqual(group, self.group)

    def test_paginator(self):
        posts_count = Post.objects.count()
        posts = []
        for _ in range(self.POST_COUNT):
            post = Post(
                author=self.user,
                text='Тестовый текст',
                group=self.group
            )
            posts.append(post)
        Post.objects.bulk_create(posts)
        pages = (
            (1, self.PAGE_ONE_POST_COUNT),
            (2, self.PAGE_TWO_POST_COUNT + posts_count),
        )
        for page, count in pages:
            for url, _ in self.paginator_urls:
                with self.subTest(url=url):
                    response = self.client.get(url, {'page': page})
                    self.assertEqual(
                        len(response.context['page_obj'].object_list), count
                    )

    def test_index_page_cache(self):
        '''Проверяем, что записи на главной странице
        хранятся в cache'''
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        response_cache = response.content
        post = Post.objects.get(pk=1)
        post.delete()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response_cache, response.content)


class FollowPagesTest(TestCase):
    NAME_AUTHOR = 'Bilbo'
    NAME_USER = 'Frodo'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(
            username=FollowPagesTest.NAME_AUTHOR
        )
        cls.user = User.objects.create_user(
            username=FollowPagesTest.NAME_USER
        )
        cls.new_group = Group.objects.create(
            title='Тестовая группа',
            slug='slug',
            description='Тестовое описание',
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_added_in_follow_list(self):
        '''Запись плоявляется в лентах тех, кто подписан'''
        Follow.objects.create(
            user=self.user,
            author=self.author,
        )
        post = Post.objects.create(
            author=self.author,
            text='Тестовый текст публикации',
            group=self.new_group,
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        follow_objects = response.context['page_obj']
        self.assertIn(post, follow_objects)

    def test_post_not_added_in_unfollower_list(self):
        '''Запись не плоявляется в лентах тех, кто не подписан'''
        post = Post.objects.create(
            author=self.author,
            text='Тестовый текст публикации',
            group=self.new_group,
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        follow_objects = response.context['page_obj']
        self.assertNotIn(post, follow_objects)

    def test_authorized_client_can_follow(self):
        '''Авторизованный пользователь может
        подписываться на автора'''
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                args=[self.author]
            )
        )
        follow = Follow.objects.filter(
            user=self.user,
            author=self.author,
        ).exists()
        self.assertTrue(follow)

    def test_authorized_client_can_unfollow(self):
        '''Авторизованный пользователь может
        отписываться от автора'''
        Follow.objects.create(
            user=self.user,
            author=self.author,
        )
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                args=[self.author]
            )
        )
        unfollow = Follow.objects.filter(
            user=self.user,
            author=self.author,
        ).exists()
        self.assertFalse(unfollow)
