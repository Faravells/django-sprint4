from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)

from .forms import CommentForm, PostForm, ProfileEditForm
from .models import Category, Comment, Post

User = get_user_model()

POSTS_PER_PAGE = 10


def get_published_posts():
    """Возвращает QuerySet опубликованных постов с аннотацией."""
    return Post.objects.filter(
        is_published=True,
        pub_date__lte=timezone.now(),
        category__is_published=True,
    ).select_related(
        'author', 'category', 'location'
    ).annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')


class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/registration_form.html'
    success_url = reverse_lazy('login')


class IndexView(ListView):
    template_name = 'blog/index.html'
    paginate_by = POSTS_PER_PAGE
    context_object_name = 'page_obj'

    def get_queryset(self):
        return get_published_posts()


class CategoryPostsView(ListView):
    template_name = 'blog/category.html'
    paginate_by = POSTS_PER_PAGE
    context_object_name = 'page_obj'

    def get_queryset(self):
        self.category = get_object_or_404(
            Category,
            slug=self.kwargs['category_slug'],
            is_published=True,
        )
        return self.category.posts.filter(
            is_published=True,
            pub_date__lte=timezone.now(),
        ).select_related(
            'author', 'category', 'location'
        ).annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'

    def get_object(self, queryset=None):
        post = get_object_or_404(
            Post.objects.select_related(
                'author', 'category', 'location'
            ).annotate(comment_count=Count('comments')),
            pk=self.kwargs['post_id'],
        )
        if post.author == self.request.user:
            return post
        if not (post.is_published
                and post.pub_date <= timezone.now()
                and post.category.is_published):
            from django.http import Http404
            raise Http404
        return post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comments.select_related('author')
        return context


class ProfileView(ListView):
    template_name = 'blog/profile.html'
    paginate_by = POSTS_PER_PAGE
    context_object_name = 'page_obj'

    def get_queryset(self):
        self.profile = get_object_or_404(
            User,
            username=self.kwargs['username'],
        )
        qs = Post.objects.filter(author=self.profile).select_related(
            'author', 'category', 'location'
        ).annotate(comment_count=Count('comments')).order_by('-pub_date')
        if self.request.user != self.profile:
            qs = qs.filter(
                is_published=True,
                pub_date__lte=timezone.now(),
                category__is_published=True,
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.profile
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.request.user.username},
        )


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author

    def handle_no_permission(self):
        # Если не автор — редирект на просмотр поста
        if self.request.user.is_authenticated:
            return redirect('blog:post_detail', post_id=self.kwargs['post_id'])
        return super().handle_no_permission()

    def get_success_url(self):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.object.id},
        )


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('blog:post_detail', post_id=self.kwargs['post_id'])
        return super().handle_no_permission()

    def get_success_url(self):
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.request.user.username},
        )


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post = get_object_or_404(Post, pk=self.kwargs['post_id'])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']},
        )


class CommentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.author

    def get_success_url(self):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']},
        )


class CommentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.author

    def get_success_url(self):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']},
        )


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileEditForm
    template_name = 'blog/create.html'
    success_url = reverse_lazy('blog:index')

    def get_object(self, queryset=None):
        return self.request.user
