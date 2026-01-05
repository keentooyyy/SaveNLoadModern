import hashlib

from django.db import models
from django.utils import timezone

from SaveNLoad.models.user import SimpleUsers


class RefreshToken(models.Model):
    """
    Tracks refresh tokens for rotation and revocation.
    """

    user = models.ForeignKey(SimpleUsers, on_delete=models.CASCADE, related_name='refresh_tokens')
    jti = models.UUIDField(unique=True)
    user_agent_hash = models.CharField(max_length=64, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    replaced_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'refresh_tokens'
        verbose_name = 'Refresh Token'
        verbose_name_plural = 'Refresh Tokens'
        indexes = [
            models.Index(fields=['user', 'revoked_at']),
            models.Index(fields=['expires_at']),
        ]

    def is_active(self) -> bool:
        """
        Return True if token is not revoked and not expired.
        """
        if self.revoked_at is not None:
            return False
        return timezone.now() < self.expires_at

    def matches_context(self, user_agent: str | None, ip_address: str | None) -> bool:
        """
        Ensure refresh token is used from the same client context.
        """
        ua_hash = hashlib.sha256((user_agent or '').encode('utf-8')).hexdigest()
        if self.user_agent_hash and ua_hash != self.user_agent_hash:
            return False
        if self.ip_address and ip_address and self.ip_address != ip_address:
            return False
        return True

    def revoke(self, replaced_by=None):
        """
        Mark token as revoked and optionally store replacement jti.
        """
        self.revoked_at = timezone.now()
        if replaced_by:
            self.replaced_by = replaced_by
        self.save(update_fields=['revoked_at', 'replaced_by'])
