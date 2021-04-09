import queue
import threading
import time

from bs4 import BeautifulSoup

from core.SearchEngine.Search import RequestDispatcher
from core.appConfig import AppConfigurations

config = AppConfigurations()


class FindData(RequestDispatcher):
    def __init__(self):
        self.sourcePage = None

    def FindTags(self, target: dict) -> list:
        try:
            tags_container = list()
            soup = BeautifulSoup(self.sourcePage, 'html.parser')
            tags = soup.find('ul', target)
            for tag in tags.li.find_next_siblings():
                tags_container.append(tag.text)
            return tags_container
        except BaseException as e:
            print("Could not extract tags", e)

    def extractData(self, link: str) -> tuple:
        """method to extract title and tag"""
        text = self.MakeRequest(target=link)
        self.sourcePage = text
        soup = BeautifulSoup(text, 'html.parser')
        try:
            if 'video' in link:
                title = soup.find('h1', {"class": "Q2kXR_hT9c flipboard-title"}).text
                print(self.FindTags({'class': '_38q8dhe3Fx'}))
                category = self.FindTags({'class': '_38q8dhe3Fx'})
                published_date = soup.find('div', {"class": "_2Jrc-IHPAI _6-YEXCu4FK"}).text
                if config.DEBUG:
                    print("Data For: {}\nTitle: {}\nCategory: {}\nPublished Date: {}".format(link, title, category,
                                                                                             published_date))
                # SendToChannel(title, published_date, category, link)
                return title, published_date
            elif 'article' in link:
                title = soup.find('h1', {"class": "_2JPm2UuC56 flipboard-title"}).text
                category = self.FindTags({'class': 'AsCeVPiOdE'})
                print(self.FindTags({'class': 'AsCeVPiOdE'}))
                published_date = soup.find('div', {"class": "_2Jrc-IHPAI"}).text
                if config.DEBUG:
                    print("Data For: {}\nTitle: {}\nCategory: {}\nPublished Date: {}".format(link, title, category,
                                                                                             published_date))
                # SendToChannel(title, published_date, category, link)
        except BaseException as e:
            config.debug(level=1, data=e)

    def performDataExtraction(self, links: list):
        DataFetcherQueue = queue.Queue()
        for link in links:
            DataFetcherQueue.put(link)
            DataFetcherThread = threading.Thread(target=self.extractData, args=(DataFetcherQueue.get(),))
            DataFetcherThread.start()
            while threading.active_count() >= 20:
                time.sleep(3)
