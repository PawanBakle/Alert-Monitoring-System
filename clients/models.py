from django.db import models
# from django.contrib.db.user import AbstractBaseUser
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
# Create your models here. 
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

class NodeManager(BaseUserManager):
    def create_user(self, host_name, mac_address, password=None, **extra_fields):
        if not host_name:
            raise ValueError('Nodes must have a hostname')
        
        # Normalize hostname (optional, e.g., lowercase)
        host_name = host_name.lower()
        
        user = self.model(
            host_name=host_name,
            mac_address=mac_address,
            **extra_fields
        )
        user.set_password(password) # You might set a random unusable password later
        user.save(using=self._db)
        return user

# Registering a Node
class Node(AbstractBaseUser):
    # data required to register "mac_address": "00:1A:2B:3C:4D:5E", 
    host_name = models.CharField(max_length = 12,unique = True)
    mac_address = models.CharField(max_length = 15,unique = True)
    os_version = models.CharField(max_length = 15)
    objects = NodeManager()
    # change user name from username to host_name
    USERNAME_FIELD = 'host_name'
    # call the middle manager to over-ride this and for every user creation make sure username is host-name and not user-name for tables
    REQUIRED_FIELDS = ['mac_address']

# Metrics
class NodeSimulator(models.Model):
    # data which will be sent by Servers
    server = models.CharField(max_length = 12)
    cpu = models.IntegerField(max_length = 6)
