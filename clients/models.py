from django.db import models
# from django.contrib.db.user import AbstractBaseUser
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

from django.core.validators import MinValueValidator, MaxValueValidator

class NodeManager(BaseUserManager):
    def create_user(self, node_name, mac_address, password=None, **extra_fields):
        if not node_name:
            raise ValueError('Nodes must have a hostname')
        node_name = node_name.lower()
        
        user = self.model(
            node_name=node_name,
            mac_address=mac_address,
            **extra_fields
        )
        user.set_password(password) # You might set a random unusable password later
        user.save(using=self._db)
        return user

# Registering a Node
class Node(AbstractBaseUser):
    # data required to register "mac_address": "00:1A:2B:3C:4D:5E", 
    STATUS_ONLINE= 'ONLINE'
    STATUS_OFFLINE= 'OFFLINE'
    STATUS_CHOICES = ((STATUS_ONLINE,'Online'),(STATUS_OFFLINE,'Offline'))
    node_name = models.CharField(max_length = 12,unique = True)
    mac_address = models.CharField(max_length = 20,unique = True)
    os_version = models.CharField(max_length = 15)
    time_registered = models.DateTimeField(auto_now_add = True)
    status = models.CharField(max_length=25,choices = STATUS_CHOICES,default = STATUS_OFFLINE)
    objects = NodeManager()
    # change user name from username to host_name
    USERNAME_FIELD = 'node_name'
    # call the middle manager to over-ride this and for every user creation make sure username is host-name and not user-name for tables
    REQUIRED_FIELDS = ['mac_address']
    

# Metrics
class Metrics(models.Model):
    # data which will be sent by Servers
    seq_id = models.IntegerField(unique = False,default= 0) # it should be unique but for testing have used incremental
    # seq_id = models.IntegerField(help_text="Temporary", unique=False) # it should be unique but for testing have used incremental
    node_server = models.ForeignKey('Node', on_delete = models.PROTECT)
    # server = models.CharField(max_length = 12)
    cpu = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    memory = models.IntegerField()
    disk = models.IntegerField()
    time_stamp = models.DateTimeField(auto_now = True)
    severity = models.CharField(max_length=20, choices=[
        ('NORMAL', 'Normal'),
        ('WARNING', 'Warning'),
        ('CRITICAL', 'Critical'),
    ], default='NORMAL')
    alert_reason = models.CharField(max_length = 255, null = True, blank = True)


    
