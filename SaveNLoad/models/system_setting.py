from django.db import models


class SystemSetting(models.Model):
    """
    Simple key/value store for admin-managed settings and feature flags.
    """
    key = models.CharField(max_length=200, unique=True)
    value = models.JSONField(null=True, blank=True)
    updated_by = models.ForeignKey(
        'SaveNLoad.SimpleUsers',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'system_settings'
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'

    def __str__(self):
        return f"{self.key}"
