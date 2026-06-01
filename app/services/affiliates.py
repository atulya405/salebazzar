from urllib.parse import quote, urlencode, urlparse, parse_qsl, urlunparse

from app.config import Settings


def _with_query(url: str, **params: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))
    query.update({key: value for key, value in params.items() if value})
    return urlunparse(parsed._replace(query=urlencode(query)))


def affiliate_url(product_url: str, settings: Settings) -> str:
    hostname = urlparse(product_url).hostname or ""
    if settings.amazon_affiliate_tag and ("amazon." in hostname or hostname.endswith("amzn.to")):
        return _with_query(product_url, tag=settings.amazon_affiliate_tag)
    if settings.flipkart_affiliate_tag and "flipkart." in hostname:
        return _with_query(product_url, affid=settings.flipkart_affiliate_tag)
    if settings.other_affiliate_template:
        return settings.other_affiliate_template.format(
            url=quote(product_url, safe=""), tag=quote(settings.other_affiliate_tag, safe="")
        )
    return product_url

