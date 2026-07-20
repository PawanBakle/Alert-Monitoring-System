from django.db import models
# from django.contrib.db.user import AbstractBaseUser
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
# Create your models here.
class NodeSimulator(models.Model):
    # data which will be sent by Servers
    server = models.CharField(max_lenght = 12)
    cpu = models.IntegerField(max_lenght = 6)

class NodeManager(BaseUserManager)
    def create_user(self, hostname, mac_address, password=None, **extra_fields):
        if not hostname:
            raise ValueError('Nodes must have a hostname')
        
        # Normalize hostname (optional, e.g., lowercase)
        hostname = self.model.normalize_hostname(hostname)
        
        user = self.model(
            hostname=hostname,
            mac_address=mac_address,
            **extra_fields
        )
        user.set_password(password) # You might set a random unusable password later
        user.save(using=self._db)
        return user


class Node(AbstractBaseUser):
    # data required to register "mac_address": "00:1A:2B:3C:4D:5E", 
    host_name = models.CharField(max_length = 12)
    mac_address = models.CharField(max_length = 15)
    os_version = models.CharField(max_length = 15)
    objects = NodeManager()
    # change user name from username to host_name
    USERNAME_FIELDS = 'host_name'
    # call the middle manager to over-ride this and for every user creation make sure username is host-name and not user-name for tables

