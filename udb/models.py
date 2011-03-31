from django.db import models

# Create your models here.



class User(models.Model):
	id = models.EmailField(primary_key=True)
	name = models.CharField(max_length=256)
	uid = models.IntegerField(default=5000, editable=False)
	gid = models.IntegerField(default=5000, editable=False)
	home = models.CharField(default="/var/spool/mail/virtual", editable=False, max_length=256)
	maildir = models.CharField(unique=True, max_length=255)
	enabled = models.BooleanField()
	change_password = models.BooleanField()
	clear = models.CharField(max_length=64, default="ChangeMe")
	crypt = models.CharField(max_length=64)
	quita = models.IntegerField()
	procmailrc = models.CharField(max_length=256, blank=True)
	spamassasinrc = models.CharField(max_length=256, blank=True)
	

	def __unicode__(self):
		return self.id
	
