from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User

POSTS_QUANTITY: int = 10


def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, POSTS_QUANTITY)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    paginator = Paginator(post_list, POSTS_QUANTITY)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    user_obj = get_object_or_404(User, username=username)
    users_posts = user_obj.posts.all()
    posts_number = users_posts.count()
    paginator = Paginator(users_posts, POSTS_QUANTITY)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    following = (request.user.is_authenticated and Follow.objects.filter(
        user=request.user, author=user_obj).exists())
    context = {
        'user_obj': user_obj,
        'posts_number': posts_number,
        'page_obj': page_obj,
        'following': following
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    author_posts_number = post.author.posts.count()
    comment_form = CommentForm()
    comments = post.comments.select_related('post')
    context = {
        'post': post,
        'author_posts_number': author_posts_number,
        'comment_form': comment_form,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', username=request.user)
    context = {
        'is_edit': False,
        'form': form,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id)
    context = {
        'is_edit': True,
        'form': form,
        'post_id': post_id,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    form = CommentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = get_object_or_404(Post, pk=post_id)
        comment.save()
    return redirect('posts:post_detail', post_id)


@login_required
def follow_index(request):
    post_list = (Post.objects.filter(author__following__user=request.user))
    paginator = Paginator(post_list, POSTS_QUANTITY)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    following_user = get_object_or_404(User, username=username)
    if (request.user != following_user and not Follow.objects.filter(
            user=request.user, author=following_user).exists()):
        Follow.objects.create(user=request.user, author=following_user)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    follow_record = Follow.objects.filter(
        user=request.user,
        author=get_object_or_404(User, username=username)
    )
    if follow_record.exists():
        follow_record.delete()
    return redirect('posts:profile', username=username)
