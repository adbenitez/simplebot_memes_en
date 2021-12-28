"""Plugin's hooks and commands definitions."""

import functools
import io
import mimetypes
import re
from typing import Callable

import bs4
import requests
import simplebot
from pkg_resources import DistributionNotFound, get_distribution
from simplebot.bot import DeltaBot, Replies

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    __version__ = "0.0.0.dev0-unknown"
session = requests.Session()
session.headers.update(
    {
        "user-agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0"
    }
)
session.request = functools.partial(session.request, timeout=15)  # type: ignore


@simplebot.hookimpl
def deltabot_init(bot: DeltaBot) -> None:
    _getdefault(bot, "max_meme_size", 1024 * 1024 * 5)


@simplebot.command
def memecenter(bot: DeltaBot, replies: Replies) -> None:
    """Get random memes from www.memecenter.com"""
    replies.add(**_get_meme(bot, _get_image))


def _get_image() -> tuple:
    url = "https://www.memecenter.com"
    with session.get(url) as resp:
        resp.raise_for_status()
        soup = bs4.BeautifulSoup(resp.text, "html.parser")
    url = soup.find("a", class_="random")["href"]
    with session.get(url) as resp:
        resp.raise_for_status()
        soup = bs4.BeautifulSoup(resp.text, "html.parser")
    img_desc = soup.title.get_text().strip()
    img_url = soup.find("div", id="fdc_download").a["href"]
    return (img_desc, img_url)


def _get_meme(bot: DeltaBot, get_image: Callable) -> dict:
    img = b""
    max_meme_size = int(_getdefault(bot, "max_meme_size"))
    for _ in range(10):
        img_desc, img_url = get_image()
        with session.get(img_url) as resp:
            resp.raise_for_status()
            if len(resp.content) <= max_meme_size:
                img = resp.content
                ext = _get_ext(resp) or ".jpg"
                break
            if not img or len(img) > len(resp.content):
                img = resp.content
                ext = _get_ext(resp) or ".jpg"

    return dict(text=img_desc, filename="meme" + ext, bytefile=io.BytesIO(img))


def _get_ext(resp: requests.Response) -> str:
    disp = resp.headers.get("content-disposition")
    if disp is not None and re.findall("filename=(.+)", disp):
        fname = re.findall("filename=(.+)", disp)[0].strip('"')
    else:
        fname = resp.url.split("/")[-1].split("?")[0].split("#")[0]
    if "." in fname:
        ext = "." + fname.rsplit(".", maxsplit=1)[-1]
    else:
        ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
        if ctype == "text/plain":
            ext = ".txt"
        elif ctype == "image/jpeg":
            ext = ".jpg"
        else:
            ext = mimetypes.guess_extension(ctype)
    return ext


def _getdefault(bot: DeltaBot, key: str, value=None) -> str:
    val = bot.get(key, scope=__name__)
    if val is None and value is not None:
        bot.set(key, value, scope=__name__)
        val = value
    return val


class TestPlugin:
    """Online tests"""

    def test_memecenter(self, mocker):
        msg = mocker.get_one_reply("/memecenter")
        assert msg.filename
