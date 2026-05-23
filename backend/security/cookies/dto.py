from __future__ import annotations

from dataclasses import dataclass

from security.cookies.enums import CookieSameSite


@dataclass(frozen=True, slots=True)
class CookieOptions:
    secure: bool
    httponly: bool
    samesite: CookieSameSite
    domain: str | None
    path: str

    def to_set_cookie_kwargs(self) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "secure": self.secure,
            "httponly": self.httponly,
            "samesite": self.samesite,
            "path": self.path,
        }
        if self.domain is not None:
            kwargs["domain"] = self.domain
        return kwargs

    def to_delete_cookie_kwargs(self) -> dict[str, object]:
        return self.to_set_cookie_kwargs()


@dataclass(frozen=True, slots=True)
class AuthCookieNames:
    access: str
    refresh: str


__all__ = ["CookieOptions", "AuthCookieNames"]
