from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from ..models import Group, Post


User = get_user_model()


class PostURLTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        cls.public_urls = (
            ('/', 'posts/index.html'),
            (f'/group/{PostURLTests.group.slug}/', 'posts/group_list.html'),
            (f'/profile/{PostURLTests.user}/', 'posts/profile.html'),
            (f'/posts/{PostURLTests.post.pk}/', 'posts/post_detail.html'),
        )
        cls.privet_urls = (
            (f'/posts/{PostURLTests.post.pk}/edit/', 'posts/create_post.html'),
            ('/create/', 'posts/create_post.html'),
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostURLTests.user)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        posts_urls = self.public_urls + self.privet_urls
        for address, template in posts_urls:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_uses_by_guest_client(self):
        for address, _ in self.public_urls:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_by_authorized_client(self):
        for address, _ in self.privet_urls:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_wrong_urls_uses_by_guest_client(self):
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')

    def test_privet_urls_uses_by_guest_client(self):
        for address, _ in self.privet_urls:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)
