from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from datetime import timedelta
from django.utils import timezone

class Subject(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=210, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-generate unique slug from name if not provided
        if not self.slug:
            base_slug = slugify(self.name)
            slug_candidate = base_slug
            counter = 1
            while Subject.objects.filter(slug=slug_candidate).exclude(pk=self.pk).exists():
                slug_candidate = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug_candidate
        super().save(*args, **kwargs)


class Forum(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="forums")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Forum"
        verbose_name_plural = "Forums"
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.subject.name})"


class Thread(models.Model):
    forum = models.ForeignKey(Forum, on_delete=models.CASCADE, related_name="threads")
    title = models.CharField(max_length=255)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="threads")
    content = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Thread"
        verbose_name_plural = "Threads"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Post(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="posts")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Post"
        verbose_name_plural = "Posts"
        ordering = ["created_at"]

    def __str__(self):
        return f"Post by {self.author} on {self.thread}"
    def _forum_latest_posts(self, limit=10):
        """
        Return the most recent posts in this forum (across all threads).
        Default limit is 10.
        """
        return (
            Post.objects
            .filter(thread__forum=self)
            .select_related("author", "thread")
            .order_by("-created_at")[:limit]
        )

    def _forum_new_posts(self, since=None):
        """
        Return posts in this forum created after `since`. If `since` is None,
        default to posts from the last 24 hours.
        """
        if since is None:
            since = timezone.now() - timedelta(days=1)
        return (
            Post.objects
            .filter(thread__forum=self, created_at__gt=since)
            .select_related("author", "thread")
            .order_by("created_at")
        )

    # Attach as methods on Forum
    Forum.latest_posts = _forum_latest_posts
    Forum.new_posts = _forum_new_posts