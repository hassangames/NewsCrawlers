import queue
import threading

from bs4 import BeautifulSoup

from core.appConfig import AppConfigurations
from core.ext.Utiltiy import write_json
from core.ext.http_Req import RequestDispatcher

config = AppConfigurations()


class FindData(RequestDispatcher):
    def __init__(self):
        self.ResultsData = {'alajazera': []}
    def findTags(self,rawData):
        tags = []
        for i in rawData:
            tags.append(i.text)
        return tags
    def extractData(self, link: str, language) -> tuple:

        """method to extract title and tag"""
        try:
            if language == 'en':
                text = self.MakeRequest(target=link)
                soup = BeautifulSoup(text, 'html.parser')
                title = soup.findAll("h1")[0].text
                category = soup.findAll("div", {"class": "topics"})[0].text
                published_date = soup.findAll("div", {"class": "date-simple"})[0].text
                self.ResultsData.get('alajazera').append(
                    dict(title=title, category=category, published_date=published_date, link=link))
                if config.DEBUG:
                    print("Title: {}\nCategory: {}\nPublished Date: {}\nSource: @Aljazeera".format(title, category,
                                                                                                   published_date))
                # SendToChannel(title, published_date, category, link)
                # return title, category
            else:
                text = self.MakeRequest(target=link)
                soup = BeautifulSoup(text, 'html.parser')
                title = soup.findAll("header", {"class": "article-header"})[0].h1.text
                category = soup.findAll("div", {"class": "topics"})[0].text
                published_date = soup.findAll("span", {"class": "article-dates__published"})[0].text
                self.ResultsData.get('alajazera').append(
                    dict(title=title, category=category, published_date=published_date, link=link))
                if config.DEBUG:
                    print("Title: {}\nCategory: {}\nPublished Date: {}\nSource: @Aljazeera".format(title, category,
                                                                                                   published_date))
                # SendToChannel(title, published_date, category, link)
                return title, category
        except BaseException as e:

            config.debug(level=1, data=e)

    def performDataExtraction(self, links: list, language):
        try:
            DataFetcherQueue = queue.Queue()
            threads = []
            for link in links:
                DataFetcherQueue.put(link)
                DataFetcherThread = threading.Thread(target=self.extractData, args=(DataFetcherQueue.get(), language))
                threads.append(DataFetcherThread)
            for thread_starter in threads:
                thread_starter.start()
            for thread_joiner in threads:
                thread_joiner.join()
        except BaseException as e:
            print(e)
        write_json(config.EnvironmentPath(), 'aljazeera', self.ResultsData)
