from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Group, Follow, Post, User, Comment
from .utils import posts_per_page


def index(request):
    template = 'posts/index.html'
    post_list = Post.objects.select_related(
        'author',
        'group'
    ).all()
    context = {
        'page_obj': posts_per_page(request, post_list),
        'view_name': 'posts:index',
    }
    return render(request, template, context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    template = 'posts/group_list.html'
    context = {
        'group': group,
        'page_obj': posts_per_page(request, posts),
    }
    return render(request, template, context)


def profile(request, username):
    author_post = get_object_or_404(User, username=username)
    post_list = author_post.posts.all()
    posts_count = post_list.count()
    template = 'posts/profile.html'
    following = request.user.is_authenticated and request.user.follower.filter(
        author=author_post).exists()
    context = {
        'author_post': author_post,
        'page_obj': posts_per_page(request, post_list),
        'following': following,
        'posts_count': posts_count,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    template = 'posts/post_detail.html'
    form = CommentForm(
        request.POST or None
    )
    comments = Comment.objects.filter(
        post_id=post_id
    )
    context = {
        'post': post,
        'form': form,
        'comments': comments,
    }
    return render(request, template, context)


@login_required
def post_create(request):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        form.save()
        return redirect('posts:profile', post.author)
    context = {
        'form': form,
    }
    template = 'posts/create_post.html'
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    template = 'posts/create_post.html'
    is_edit = True
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post)
    if post.author != request.user:
        return redirect('posts:profile', post.author)
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id)
    context = {
        'form': form,
        'is_edit': is_edit,
    }
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    post = Post.objects.get(pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    '''Передаем данные для страницы контекста'''
    posts = Post.objects.filter(
        author__following__user=request.user
    ).select_related('author', 'group')
    context = {
        'page_obj': posts_per_page(request, posts),
        'view_name': 'posts:follow_index'
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    '''Подписка на автора'''
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    '''Описка от автора'''
    Follow.objects.filter(
        author__username=username,
        user=request.user
    ).delete()
    return redirect('posts:profile', username=username)
