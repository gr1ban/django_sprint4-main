from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.utils import timezone  # timezone

from .forms import PostForm, CommentForm, UserForm
from .models import Post, Category, User, Comment

NUMBER_OF_PAGINATOR_PAGES = 10


def get_posts(**kwargs):
    """Отфильтрованное получение постов."""
    return Post.objects.select_related(
        'category',
        'location',
        'author'
    ).annotate(comment_count=Count('comments')
               ).filter(**kwargs).order_by('-pub_date')


def get_paginated_page(request, queryset,
                       number_of_pages=NUMBER_OF_PAGINATOR_PAGES):
    """Получение страницы из queryset для пагинации, по N-шт на странице."""
    paginator = Paginator(queryset, number_of_pages)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def get_filtered_posts_qs():
    """Получение queryset постов с общими условиями фильтрации."""
    return Post.objects.filter(
        is_published=True,
        category__is_published=True,
        pub_date__lte=timezone.now()
    )


def index(request):
    """Главная страница / Лента публикаций."""
    posts = get_filtered_posts_qs().annotate(comment_count=Count('comments')
                                             ).order_by('-pub_date')
    page_obj = get_paginated_page(request, posts)
    context = {'page_obj': page_obj}
    return render(request, 'blog/index.html', context)


def category_posts(request, category_slug):
    """Отображение публикаций в категории."""
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )
    # Фильтр уже есть в get_filtered_posts_qs, но добавляем для читаемости
    posts = get_filtered_posts_qs().order_by('-pub_date').filter(
        category=category
    )
    page_obj = get_paginated_page(request, posts)
    context = {'category': category, 'page_obj': page_obj}
    return render(request, 'blog/post_list.html', context)


def post_detail(request, post_id):
    """Отображение полного описания выбранной публикации."""
    try:
        post = Post.objects.get(id=post_id)

        if not post.is_published and post.author != request.user:
            raise Http404("Пост не найден")
    except Post.DoesNotExist:
        raise Http404("Пост не найден")

    form = CommentForm(request.POST or None)
    comments = Comment.objects.select_related('author').filter(post=post)
    context = {'post': post, 'form': form, 'comments': comments}
    return render(request, 'blog/post_detail.html', context)


@login_required
def create_post(request):
    """Создание публикации."""
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', request.user)
    context = {'form': form}
    return render(request, 'blog/create.html', context)


@login_required
def edit_post(request, post_id):
    """Редактирование публикации."""
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.author:
        return redirect('blog:post_detail', post_id)
    form = PostForm(request.POST or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id)
    context = {'form': form}
    return render(request, 'blog/create.html', context)


@login_required
def delete_post(request, post_id):
    """Удаление публикации."""
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.author:
        return redirect('blog:post_detail', post_id)
    form = PostForm(request.POST or None, instance=post)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:index')
    context = {'form': form}
    return render(request, 'blog/create.html', context)


@login_required
def add_comment(request, post_id):
    """Добавление комментария к публикации."""
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    """Редактирование комментария к публикации."""
    comment = get_object_or_404(Comment, id=comment_id)
    if request.user != comment.author:
        return redirect('blog:post_detail', post_id)
    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id)
    context = {'comment': comment,
               'form': form}
    return render(request, 'blog/comment.html', context)


@login_required
def delete_comment(request, post_id, comment_id):
    """Удаление комментария к публикации."""
    comment = get_object_or_404(Comment, id=comment_id)
    if request.user != comment.author:
        return redirect('blog:post_detail', post_id)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id)
    context = {'comment': comment}
    return render(request, 'blog/comment.html', context)


def profile(request, username):
    """Отображение страницы пользователя."""
    profile = get_object_or_404(
        User,
        username=username)

    posts = get_posts(author=profile)
    if request.user != profile:
        posts = (get_filtered_posts_qs().filter(author=profile).
                 annotate(comment_count=Count('comments')
                          ).order_by('-pub_date'))
    page_obj = get_paginated_page(request, posts)
    context = {'profile': profile,
               'page_obj': page_obj}
    return render(request, 'blog/profile.html', context)


@login_required
def edit_profile(request):
    """Редактирование страницы пользователя."""
    profile = get_object_or_404(
        User,
        username=request.user)
    form = UserForm(request.POST or None, instance=profile)
    if form.is_valid():
        form.save()
        return redirect('blog:profile', request.user)
    context = {'form': form}
    return render(request, 'blog/user.html', context)
