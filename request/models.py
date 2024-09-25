from socket import gethostbyaddr

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from . import settings as request_settings
from .managers import RequestManager
from .utils import HTTP_STATUS_CODES, browsers, engines, request_is_ajax

AUTH_USER_MODEL = getattr(settings, "AUTH_USER_MODEL", "auth.User")


class Request(models.Model):
    # Response information.
    response = models.SmallIntegerField(
        _("response"), choices=HTTP_STATUS_CODES, default=200
    )

    # Request information.
    method = models.CharField(_("method"), default="GET", max_length=7)
    path = models.CharField(_("path"), max_length=255)
    time = models.DateTimeField(_("time"), default=timezone.now, db_index=True)

    is_secure = models.BooleanField(_("is secure"), default=False)
    is_ajax = models.BooleanField(
        _("is ajax"),
        default=False,
        help_text=_("Whether this request was used via JavaScript."),
    )

    # User information.
    ip = models.GenericIPAddressField(_("ip address"))
    user = models.ForeignKey(
        AUTH_USER_MODEL,
        blank=True,
        null=True,
        verbose_name=_("user"),
        on_delete=models.SET_NULL,
    )
    referer = models.URLField(_("referer"), max_length=255, blank=True, null=True)
    user_agent = models.CharField(
        _("user agent"), max_length=255, blank=True, null=True
    )
    language = models.CharField(_("language"), max_length=255, blank=True, null=True)

    objects = RequestManager()

    class Meta:
        app_label = "request"
        verbose_name = _("request")
        verbose_name_plural = _("requests")
        ordering = ("-time",)

    def __str__(self):
        return "[{0}] {1} {2} {3}".format(
            self.time, self.method, self.path, self.response
        )

    def get_user(self):
        return get_user_model().objects.get(pk=self.user_id)

    def from_http_request(self, request, response=None, commit=True):
        # Request information.
        self.method = request.method
        self.path = request.path[:255]

        self.is_secure = request.is_secure()
        self.is_ajax = request_is_ajax(request)

        # User information.
        self.ip = request.META.get("REMOTE_ADDR", "")
        self.referer = request.META.get("HTTP_REFERER", "")[:255]
        self.user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]
        self.language = request.META.get("HTTP_ACCEPT_LANGUAGE", "")[:255]

        if hasattr(request, "user") and hasattr(request.user, "is_authenticated"):
            is_authenticated = request.user.is_authenticated
            if is_authenticated:
                self.user_id = request.user.id

        if response:
            self.response = response.status_code

            if (response.status_code == 301) or (response.status_code == 302):
                self.redirect = response["Location"]

        if commit:
            self.save()

    @property
    def browser(self):
        if not self.user_agent:
            return

        if not hasattr(self, "_browser"):
            self._browser = browsers.resolve(self.user_agent)
        return self._browser[0]

    @property
    def keywords(self):
        if not self.referer:
            return

        if not hasattr(self, "_keywords"):
            self._keywords = engines.resolve(self.referer)
        if self._keywords:
            return " ".join(self._keywords[1]["keywords"].split("+"))

    @property
    def hostname(self):
        try:
            return gethostbyaddr(self.ip)[0]
        except Exception:  # socket.gaierror, socket.herror, etc
            return self.ip

    def save(self, *args, **kwargs):
        if not request_settings.LOG_IP:
            self.ip = request_settings.IP_DUMMY
        elif request_settings.ANONYMOUS_IP:
            parts = self.ip.split(".")[0:-1]
            parts.append("1")
            self.ip = ".".join(parts)
        if not request_settings.LOG_USER:
            self.user = None

        super().save(*args, **kwargs)
