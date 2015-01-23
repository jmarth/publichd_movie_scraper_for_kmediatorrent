from kmediatorrent import plugin
from kmediatorrent.scrapers import scraper
from kmediatorrent.ga import tracked
from kmediatorrent.caching import cached_route
from kmediatorrent.utils import ensure_fanart
from kmediatorrent.library import library_context
import xbmc, xbmcgui
import bs4
import mechanize
import urllib2
import cookielib
import re

username = "username"
password = "password"
base_url = "https://publichd.to"

br = mechanize.Browser()
cj = cookielib.LWPCookieJar()
br.set_cookiejar(cj)

br.set_handle_equiv(True)
br.set_handle_gzip(True)
br.set_handle_redirect(True)
br.set_handle_referer(True)
br.set_handle_robots(False)
br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

br.addheaders = [('User-agent', 'Chrome')]

br.open("%s/auth/login"%base_url)

br.select_form(nr=0)

br.form['username'] = "%s" % username
br.form['password'] = "%s" % password

br.submit()

def get_movie_names(pageNum):  
    soup = bs4.BeautifulSoup(br.open("%s/movies?page=%s" % (base_url, pageNum)).read())
    titles =[a.attrs.get('title') for a in soup.select('div.thumbnail a[title]')]
    names = soup.findAll('div',{'class': 'caption'})
    new_titles =[]
    for title in titles:
        new_titles.append(title.rsplit(' ', 1)[0])
    return new_titles

def get_movie_page_urls(pageNumber):
    soup = bs4.BeautifulSoup(br.open("%s/movies?page=%s" % (base_url, pageNumber)).read())
    links = [a.attrs.get('href') for a in soup.select('div.thumbnail a[href^=https://publichd]') ]
    return links

def get_torrents_for_movie_name(link):
    titles=[]
    i=0
    html = br.open("%s" % link).read()
    soup = bs4.BeautifulSoup(html)
    names = soup.findAll('div',{'class': 'torrent-filename'})
    for name in names:
        size = soup.find("tbody").findAll("tr")[i].findAll("td")[3].getText()
        seeds = soup.find("tbody").findAll("tr")[i].findAll("td")[6].getText()
        leech = soup.find("tbody").findAll("tr")[i].findAll("td")[7].getText()
        titles.append(re.sub(' +',' ',(name.getText().replace("\n","") + " (%s) (S:%s) (L:%s)" % (size, seeds, leech))))  
        i=i+1
    return titles

def get_torrents_for_movie(link):
    soup = bs4.BeautifulSoup(br.open("%s" % link).read())
    links = [a.attrs.get('href') for a in soup.select('div.torrent-filename a[href^=https://publichd]') ]
    return links

def get_torrent_uri(link):
    html = br.open("%s" % link).read()
    soup = bs4.BeautifulSoup(html)
    links = [a.attrs.get('href') for a in soup.select('table.table.torrent-desc a[href^=magnet:?]')][0]
    print links
    return links

@scraper("PublicHD - Moives", "%s"%plugin.get_setting("phd_picture"))
@plugin.route("/phd")
@ensure_fanart
@tracked
def phd_index():
    plugin.redirect(plugin.url_for("show_movie_names", pageNumber=1))

@plugin.route("/phd/show_movie_names/<pageNumber>")
def show_movie_names(pageNumber):
    movies = get_movie_names(pageNumber)
    for movie in movies:
        yield {
                'label': '%s'%movie,
                'path': plugin.url_for("show_message", movieName=movie, pageNumber=pageNumber),
                'is_playable': True,
                #"path": plugin.url_for("piratebay_page", root="/browse/%d" % cat[1], page=0),
        }
    yield {
        "label": ">> Next page",
        "path": plugin.url_for("show_movie_names", pageNumber=int(pageNumber) + 1),
        "is_playable": False,
    }   
   
@plugin.route("/phd/show_message/<movieName>/<pageNumber>")    
def show_message(movieName, pageNumber): 
    movies = get_movie_names(pageNumber)
    movieUrls = get_movie_page_urls(pageNumber)
    movieDict = dict(zip(movies, movieUrls))
    plugin.log.info("movie info: %s"%get_torrents_for_movie_name(movieDict[movieName]))
    dialog = xbmcgui.Dialog()
    index = dialog.select(plugin.name, get_torrents_for_movie_name(movieDict[movieName]))
    torrentLinks = get_torrents_for_movie(movieDict[movieName])
    plugin.log.info("index: %s"%index)
    if index != -1:
        uri = get_torrent_uri(torrentLinks[index])
        plugin.log.info(uri)
        plugin.redirect(plugin.url_for("play", uri=uri))


