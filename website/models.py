from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from PIL import Image
from django.core.files import File
from .validators import validate_file_size

# Create your models here.
class Paper(models.Model):
    author = models.CharField(max_length=250, default="")
    title = models.CharField(max_length=250, default="")
    year = models.IntegerField(default=None)
    publish = models.CharField(max_length=250, default="")
    link = models.CharField(max_length=1000, default="")
    upload = models.FileField(default=None)

    def __str__(self):
        return self.title + ' - ' + self.author

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    photo = models.ImageField(default='defaultuser.png', validators=[validate_file_size])
    bio = models.TextField(max_length=1000, blank=True)

    # Cropping
    x = models.FloatField(default=0)
    y = models.FloatField(default=0)
    width = models.FloatField(default=0)
    height = models.FloatField(default=0)

    #Choice Fields

    NONE = '--'
    DOCTOR = 'Dr.'
    SURNAME_CHOICES = (
        (NONE, ''),
        (DOCTOR, 'DR'),
    )
    surname = models.CharField(
        max_length=5,
        choices=SURNAME_CHOICES,
        default=NONE,
    )
    NONE = 'User'
    RETIRED = 'Retired'
    MODERATOR = 'Moderator'
    ADMIN = 'Admin'
    STAFF_STATUS = (
        (NONE, 'USER'),
        (RETIRED, 'RETIRED'),
        (MODERATOR, 'MODERATOR'),
        (ADMIN, 'ADMIN'),
    )

    staffStatus = models.CharField(max_length=15, choices=STAFF_STATUS, default=NONE)

    def isAdmin(self):
        return self.staffStatus in (self.ADMIN)

    def isModerator(self):
        return self.staffStatus in (self.MODERATOR)

    def isRetired(self):
        return self.staffStatus in (self.RETIRED)

    def isDoctor(self):
        return self.surname in (self.DOCTOR)

    def __str__(self):
        return self.user.first_name

    # Permissions

    class Meta:
        permissions = (
            ("Admin", "A faculty member working on the project."),
            ("Moderator", "An assistant currently working on the project."),
            ("Retired", "Previous researchers on project."),
        )

@receiver(post_save, sender=User)
def createUserProfile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def saveUserProfile(sender, instance, **kwargs):
    instance.profile.save()

@receiver(post_save, sender=Profile)
def updatePhoto(sender, instance, **kwargs):
    image = Image.open(instance.photo.file)
    width, height = image.size
    image.thumbnail((500, 500), Image.ANTIALIAS)
    width, height = image.size
    x, y = 0, 0
    if width > height:
        x, y = (width - height)//2, 0
    elif width < height:
        x, y = 0,(height - width)//2
    width, height = image.size
    image = image.crop((x, y, width - x, height - y))
    image = image.resize((500, 500), Image.ANTIALIAS)
    image.save(instance.photo.path)

@receiver(post_delete, sender=Profile)
def deleteOnDelete(sender, instance, **kwargs):
    if instance.photo:
        if os.path.basename(instance.photo.name) != "defaultuser.png":
            if os.path.isfile(instance.photo.path):
                os.remove(instance.photo.path)

@receiver(pre_save, sender=Profile)
def deleteOnChange(sender, instance, **kwargs):
    if not instance.pk:
        return False

    try:
        oldPhoto = Profile.objects.get(pk=instance.pk).photo
    except Profile.DoesNotExist:
        return False

    newPhoto = instance.photo
    if os.path.basename(oldPhoto.name) == "defaultuser.png":
        return False
    else:
        if os.path.basename(oldPhoto.name) == os.path.basename(newPhoto.name):
            return False

        if os.path.isfile(oldPhoto.path):
            os.remove(oldPhoto.path)