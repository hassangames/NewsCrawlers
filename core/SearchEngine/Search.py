# Some edits
import json
import threading

# from googlesearch import search
from bs4 import BeautifulSoup

from core.Scrapers.AlarabiyaScraper import FindData as AlarabiyaScrapper
from core.Scrapers.AljazeeraScrapper import FindData as AjScrapper
from core.Scrapers.RtScraper import FindData as RT_Scraper
from core.TelegramBot.TelegramSender import SendToChannel
from core.appConfig import AppConfigurations
from core.ext.Utiltiy import write_json
from core.ext.http_Req import RequestDispatcher

config = AppConfigurations()
rt_scraper = RT_Scraper()
alarabiya = AlarabiyaScrapper() # EXTREACT NEWS DATA
aljazera = AjScrapper()


class Searcher:
    """A base class to search on google"""

    # @staticmethod
    # def performSearch(query, tld) -> list:
    #     """method to perform a search operation and returns a list of links"""
    #     try:
    #         links = []  # a list to store links from google
    #         re
    #         s
    
    #         ults = search(query=query, num=5, stop=10, tld=tld)
    #         for link in results:
    #             links.append(link)  # add links to list
    #         return links
    #     except BaseException as e:
    #         config.debug(level=1, data=e)

    @staticmethod
    def Ensure_netloc(sch: str, target: str, exclude: str) -> bool:
        """
        check if the target contains a certain part of string
        :param exclude: value must not be in target url
        :param sch: site's netloc
        :param target: needed site's url
        :rtype: bool the state if the url is the needed site or not
        """
        return sch in target and exclude not in target

    @staticmethod
    def Ensure_Rules(link: str, rule: str) -> bool:
        """
        a method to make sure the provided phrase contains the rule
        :param link: a link from search results
        :param rule: a string value that is needed to be in link
        :return bool: a state if the link contains rule or not"""
        return rule in link


class SkyNews(RequestDispatcher):
    def __init__(self, query: str):

        self.Results = {'SkyNews': []}
        self.query = query.strip()
        self.AR_searchEngine = 'https://api.skynewsarabia.com//rest/v2/search/text.json?deviceType=DESKTOP&from' \
                               '=&offset=36&pageSize=25&q={}&showEpisodes=true&sort=RELEVANCE&supportsInfographic' \
                               '=true&to= '.format(self.query)

    @staticmethod
    def CreateNewsLink(news_id, sectionUrl, urlFriendlySuffix):
        return 'https://www.skynewsarabia.com' + sectionUrl + '/' + news_id + '-' + urlFriendlySuffix

    def RunExtraction(self, language: str = 'ar') -> str:
        if language.lower() == 'ar':
            json_data = self.MakeRequest(target=self.AR_searchEngine, json=True)
            for data in json_data.get('contentItems'):
                title = data.get('headline')
                published_date = data.get('date')
                category = data.get('category')
                link = self.CreateNewsLink(data.get('id'), data.get('sectionUrl'),
                                           data.get('urlFriendlySuffix'))
                self.Results.get("SkyNews").append(
                    dict(title=title, published_date=published_date, category=category, link=link))
                if config.DEBUG:
                    print("title: ", title)
                    print("published date: ", published_date)
                    print("category: ", category)
                    print("Link: ", link)
                threading.Thread(target=SendToChannel,
                                 args=(title, published_date, category, link)).start()  # Send News to telegram
            write_json(config.EnvironmentPath(), 'skynews', self.Results)
            return ''


class RT_SearchEngine(RequestDispatcher):
    def __init__(self, query: str):
        """
        :type query: str: a keyword for search operation

        """
        self.Links = []
        self.query = query
        self.EN_searchEngineLink = 'https://www.rt.com/search?q='
        self.AR_searchEngine = 'https://arabic.rt.com/search?cx=012273702381800949580%3Aiy4mxcpqrji&cof=FORID%3A11&ie' \
                               '=utf8&q={}&sa=%D8%A7%D9%84%D8%A8%D8%AD%D8%AB '

    def getSourcePage(self, language='en'):
        if language == 'ar':
            response = self.MakeRequest(target=self.AR_searchEngine.format(self.query))
            return response
        else:
            response = self.MakeRequest(target=self.EN_searchEngineLink + self.query)
            return response

    @staticmethod
    def isLink(link: str) -> bool:
        return str(link).strip().startswith('http')

    def EN_extractNewsLinks(self):
        links = list()
        soup = BeautifulSoup(self.getSourcePage(), 'html.parser')
        news = soup.findAll('a', {'class': 'link link_hover'})
        for link in news:
            if self.isLink(link.text):
                links.append(link.text)
                if config.DEBUG:
                    print(link.text)

        self.Links.extend(links)
        if len(self.Links) > 1:
            rt_scraper.performDataExtraction(self.Links)
        return links

    def AR_extractNewsLinks(self):
        links = list()
        soup = BeautifulSoup(self.getSourcePage(language='ar'), 'html.parser')
        news = soup.findAll('a', {'class': 'list-search_media'})
        for link in news:
            links.append('https://arabic.rt.com' + link.get_attribute_list('href')[0])
        self.Links.extend(links)
        if len(self.Links) > 1:
            rt_scraper.performDataExtraction(self.Links)
        rt_scraper.performDataExtraction(self.Links)
        return links

    def RunExtraction(self, lang):
        if lang == 'ar':
            self.AR_extractNewsLinks()
        else:
            self.EN_extractNewsLinks()


class Aljazeera(Searcher, RequestDispatcher):
    """Aljazeera search engine using google service"""

    def __init__(self, query, language='en'):
        self.lang = language
        self.newsLinks = []
        self.query = query
        self.AR_headers = {
            'Host': 'www.aljazeera.net',
            "Accept-Encoding": 'gzip, deflate, br',
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": 'keep-alive',
            "If-None-Match": """W/"e0-c53f7wDo53oXBizh9J4Kc52/FPs""",

            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/88.0.4324.146 Safari/537.36',
            'content-type': 'application/json',
            'accept': '*/*',
            "wp-site": "aje",
            "X-KL-Ajax-Request": "Ajax_Request",
            'original-domain': 'www.aljazeera.net',
            'Referer': f'https://www.aljazeera.net/search/{query}',

        }
        self.EN_headers = {
            'Host': 'www.aljazeera.com',
            "Accept-Encoding": 'gzip, deflate, br',
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": 'keep-alive',
            "If-None-Match": """W/"e0-c53f7wDo53oXBizh9J4Kc52/FPs""",

            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/88.0.4324.146 Safari/537.36',
            'content-type': 'application/json',
            'accept': '*/*',
            "wp-site": "aje",
            "X-KL-Ajax-Request": "Ajax_Request",
            'original-domain': 'www.aljazeera.com',
            'Referer': f'https://www.aljazeera.net/search/{self.query}',

        }
        self.Search_data = dict(query=query.decode('utf-8'), start=1, sort="relevance")
        self.API = "https://www.aljazeera.com/graphql?wp-site=aje&operationName=SearchQuery&variables={}&extensions={}".format(
            json.dumps(self.Search_data), '')
        self.AR_API = "https://www.aljazeera.net/graphql?wp-site=aje&operationName=SearchQuery&variables={}&extensions={}".format(
            json.dumps(self.Search_data), '')

    def getNewsLinks(self):
        try:
            """Gather links from response and store them into list"""
            if self.lang == 'ar':
                result = self.MakeRequest(target=self.AR_API, json=True, headers=self.AR_headers)
                for news_url in result.get('data').get('searchPosts').get('items'):
                    self.newsLinks.append(news_url.get('link'))
                    if config.DEBUG:
                        print(news_url.get('title'))
                        print(news_url.get('link'))
                aljazera.performDataExtraction(self.newsLinks, self.lang)
            else:
                result = self.MakeRequest(target=self.API, json=True, headers=self.EN_headers)
                for news_url in result.get('data').get('searchPosts').get('items'):
                    self.newsLinks.append(news_url.get('link'))
                    if config.DEBUG:
                        print(news_url.get('title'))
                        print(news_url.get('link'))

                aljazera.performDataExtraction(self.newsLinks, self.lang)
        except BaseException as e:
            config.debug(level=1, data=e)


class CNN(Searcher, RequestDispatcher):
    """CNN search engine using google service"""

    def __init__(self):
        self.newsLinks = []
        self.Results = {'cnn': []}
        self.API_CNN_EN = "https://search.api.cnn.io/content?q={}&size=18&category=us,politics,world,opinion," \
                          "health&sort=relevance "

    @staticmethod
    def makeDorkSearch(query: str) -> str:
        """Make the search operation to best match """
        return '"cnn.com " "{}"'.format(query)

    def EN_CNN_Search(self, query: str):
        results = self.MakeRequest(target=self.API_CNN_EN.format(query.strip()), json=True)
        for news in results.get('result'):
            title = news.get('headline')
            tags = news.get('section')
            published_date = news.get('firstPublishDate')
            link = news.get('url')
            self.Results.get("cnn").append(dict(title=title, tags=tags, published_date=published_date, link=link))
        write_json(config.EnvironmentPath(), 'cnn', self.Results)
    # def getNewsLinks(self, query: str):
    #     try:
    #         """Gather response links and store them into list"""
    #         results = self.performSearch(query=self.makeDorkSearch(query), tld='com')
    #         for newsLink in results:
    #             if self.Ensure_Rules(newsLink, 'world') or self.Ensure_Rules(newsLink, 'article'):
    #                 print("Rules matched==>", newsLink)
    #                 self.newsLinks.append(newsLink)
    #     except BaseException as e:
    #
    #         config.debug(level=1, data=e)


class Alarabiya(RequestDispatcher):
    """
    EXTRACT NEWS LINKS
    """
    def __init__(self, query):
        self.newsLinks = [] # store news links
        self.SearchEngine = "https://www.alarabiya.net/tools/search?query={}".format(query)
        self.ENSearchEngine = "https://english.alarabiya.net/tools/search?query={}".format(query)

    @staticmethod
    def CombineURL(path: str) -> str:
        return 'https://www.alarabiya.net' + path

    def AR_getNewsLinks(self) -> list:
        """Gather response links and store them into list"""
        results = self.MakeRequest(self.SearchEngine) # HTTP REQUEST
        soup = BeautifulSoup(results, 'html.parser')
        news = soup.find_all('div', {"class": 'latest_content'})
        for link in news:
            if config.DEBUG:
                print(self.CombineURL(link.a.get_attribute_list('href')[0]))
            self.newsLinks.append(self.CombineURL(link.a.get_attribute_list('href')[0]))
        alarabiya.performDataExtraction(self.newsLinks)
        return self.newsLinks

    def EN_getNewsLinks(self) -> list:
        """Gather response links and store them into list"""
        results = self.MakeRequest(self.ENSearchEngine)
        soup = BeautifulSoup(results, 'html.parser')
        news = soup.find_all('div', {'class': 'latest_content'})
        for link in news:
            if link.a.get_attribute_list('href')[0]:
                if config.DEBUG:
                    print('https://english.alarabiya.net' + link.a.get_attribute_list('href')[0])
                self.newsLinks.append('https://english.alarabiya.net' + link.a.get_attribute_list('href')[0])
            else:
                if config.DEBUG:
                    print(link.a)
        alarabiya.performDataExtraction(self.newsLinks)
        return self.newsLinks

    def RunExtraction(self, lang):
        if lang == 'ar':
            self.AR_getNewsLinks()
        else:
            self.EN_getNewsLinks()


# class BBC(Searcher):
#     """BBC search engine using google service"""
#
#     def __init__(self, query: str):
#         self.query = query
#         self.newsLinks = []
#
#     @staticmethod
#     def makeDorkSearch(query: str) -> str:
#         """Make the search operation to best match """
#         return '"bbc.com" {}'.format(query)
#
#     def getNewsLinks(self: str) -> None:
#         """Gather response links and store them into list"""
#         results = self.performSearch(query=self.makeDorkSearch(self.query), tld='net')
#         for newsLink in results:
#             if self.Ensure_Rules(newsLink, 'bbc.com'):
#                 if config.DEBUG:
#                     print("Rules matched==>", newsLink)
#                 self.newsLinks.append(newsLink)


class FoxNews_EN(RequestDispatcher, Searcher):
    def __init__(self, query):
        self.Results = {'foxnews': []}
        self.query = query
        self.API = f"https://api.foxnews.com/search/web?q={self.query}+-filetype:json+-filetype:json+more:pagemap:metatags-prism.section&siteSearch=foxnews.com&siteSearchFilter=i&callback=__jp0"

    def convertToJson(self) -> dict:
        """A method to manipulate response and convert it from string into dictionary"""
        try:
            response = self.MakeRequest(target=self.API, json=False)  # creating HTTP req to API
            data_json = response.split("(", 1)[1].strip(")")  # removing the () from response
            parsed_json = json.loads(data_json.strip(');'))  # remove suffix ');' and convert to json
            return parsed_json
        except BaseException as e:

            config.debug(level=1, data=e)

    def parseResults(self):
        """
        A method to parse the json object to actual data and send the results to telegram channel
        """
        try:
            # json object from API response
            json_data = self.convertToJson()
            # iterate in news list
            for item in json_data.get('items'):
                # checks if the link is a news and not anything else
                if not self.Ensure_Rules(link=item.get('link'), rule='category'):
                    # gather news metadata from API response
                    news_link = item.get('link')
                    news_title = item.get('title')
                    news_published_date = item.get('pagemap').get('metatags')[0].get('dcterms.created')
                    news_tags = None
                    # Get news category using two possible dict keys
                    if item.get('pagemap').get('metatags')[0].get('classification-tags'):
                        news_tags = item.get('pagemap').get('metatags')[0].get('classification-tags').split(',')
                    else:
                        if hasattr(item.get('pagemap').get('metatags')[0].get('classification-isa'), 'split'):
                            news_tags = item.get('pagemap').get('metatags')[0].get('classification-isa').split(',')
                    # Print data to user
                    title = news_title
                    published_date = news_published_date
                    link = news_link
                    category = news_tags
                    self.Results.get("foxnews").append(
                        dict(title=title, published_date=published_date, category=category, link=link))
                    if config.DEBUG:
                        if config.DEBUG:
                            print("Link", news_link)
                            print("Title", news_title)
                            print("Categories", news_tags)
                            print("Published date:", news_published_date)
        except BaseException as e:
            print(e)
        write_json(config.EnvironmentPath(), 'foxnews', self.Results)
        # Send news to telegram channel
        # threading.Thread(target=SendToChannel, args=(title, published_date, category, link)).start()
