from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    coins = models.IntegerField(default=10)
    last_checkin = models.DateField(null=True, blank=True)

    def __str__(self):
        return f'{self.user.username} Profile'

# == Rất quan trọng: Tự động tạo Profile khi User được tạo ==
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()