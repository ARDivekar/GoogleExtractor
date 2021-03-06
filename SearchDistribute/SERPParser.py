import re
from bs4 import BeautifulSoup
from SearchDistribute.SearchExtractorErrors import SERPParsingException
from SearchDistribute.Enums import SearchEngines
import urllib

class GoogleParser:
    ''' If any of the attributes are `None`, that attribute was not present on the SERP.'''
    start_offset = -1
    current_page_num = -1
    num_results = -1
    current_url = ""
    domain = ""
    protocol = ""
    results = []
    total_num_results_for_query = -1
    query_retrieval_time_in_seconds = -1.0
    link_to_previous_page = ""
    links_to_previous_pages = []
    links_to_next_pages = []
    link_to_next_page = ""
    location = ""
    css_selector_for_valid_page = "#search"

    def __init__(self, html, current_url, start_offset, current_page_num):
        self.current_url = current_url ## This must not be moved, as self._parse_navigation_links(...) uses it.
        self.start_offset = start_offset
        self.current_page_num = current_page_num
        self.protocol = urllib.parse.urlparse(current_url).scheme
        self.domain = urllib.parse.urlparse(current_url).netloc.replace("www.", "")

        bs = BeautifulSoup(html)

        results = self._parse_result_urls(bs)
        if results == None:
            raise SERPParsingException(search_engine=SearchEngines.Google, parsing_stage="search result urls")
        self.results = results
        self.num_results = len(self.results)

        self.total_num_results_for_query = self._parse_total_number_of_results_for_query(bs)
        self.query_retrieval_time_in_seconds = self._parse_query_retrieval_time(bs)

        nav_links = self._parse_navigation_links(bs, current_url, current_page_num)
        self.link_to_previous_page, self.links_to_previous_pages, temp, self.links_to_next_pages, self.link_to_next_page = nav_links

        self.location = self._parse_location(bs)





    def _parse_result_urls(self, bs):
        """ This function, given the BeautifulSoup of the HTML of a Google Search results page, extracts the urls of the Search Results. """
        temp_results_urls=bs.find_all(attrs={"class":"r"})     ## I have found that this extracts all 10 links per page
        if temp_results_urls==[]:
            return None

        results_page_urls=[]    ## all the search result urls from a relevant Google Search results page.

        for temp_url in temp_results_urls:
                ## Method 1:
            result_page_url=re.findall('(?<=/url\?q=)(.*?)(?=")', str(temp_url))
            if result_page_url!=[]:
                result_page_url=result_page_url[0]
                result_page_url=re.findall('(.*?)(?=&amp)', result_page_url)
                if result_page_url != []:
                    result_page_url=result_page_url[0]
                    results_page_urls.append(result_page_url)
            else:
                ## Method 2:
                result_page_url=re.findall('(?<=href=").*?(?=")',str(temp_url))
                if result_page_url!=[]:
                    results_page_urls.append(result_page_url[0])

        if results_page_urls==[]:
            return None

        return tuple(results_page_urls)




    def _parse_total_number_of_results_for_query(self, bs):
        """ This function, given the BeautifulSoup of the HTML of a Google Search results page, extracts the total number of Search Results the query has.
        This can technically be extracted from any search result page of that query."""
        resultStats_html = bs.find_all(attrs={"id":"resultStats"})    ## There should be only one.
        if resultStats_html==[]:
            return None

        resultStats_html=str(resultStats_html[0])
        resultStats_html=re.sub(",","", resultStats_html)
        total_num_results_for_query=re.findall('(?<=bout )\d+(?= results)', resultStats_html)
        if total_num_results_for_query==[]:
            return None

        total_num_results_for_query=total_num_results_for_query[0]
        try:
            total_num_results_for_query=int(total_num_results_for_query)
        except Exception:
            return None
        return total_num_results_for_query



    def _parse_query_retrieval_time(self, bs):
        try:
            time_text = bs.find_all(id="resultStats")[0].find_all('nobr')[0].text.strip()
            return float(re.findall("\((.*?)( )?seconds\)", time_text)[0][0])
        except Exception:
            return None


    def _parse_navigation_links(self, bs, current_url, current_page_num):
        ''' This function returns a 4-tuple with the following syntax:
            (link_to_previous_page, list_of_links_to_previous_pages, list_of_links_to_next_pages, link_to_next_page)
            All of the links are absolute links, e.g. 'https://www.google.co.in/search?q=killing+me+softly&biw=482&bih=580&ei=KyGrWOmOEJ6QvQSZ5IiQBA&start=30&sa=N'.
            If any of these do not exist (e.g. for the very first SERP, link_to_previous_page and list_of_links_to_previous_pages would not exist), we put a `None` in the corresponding index of the 4-tuple.
        '''
        try:
            base = urllib.parse.urlparse(current_url).scheme + "://" + urllib.parse.urlparse(current_url).netloc
            # current_url_start_offset = urllib.parse.parse_qs(urllib.parse.urlparse(current_url).query).get('start')

            link_to_previous_page = None
            list_of_links_to_previous_pages = []
            link_to_current_page = None
            list_of_links_to_next_pages = []
            link_to_next_page = None

            nav_links = bs.find_all(id="nav")[0].find_all('td')
            for nav_link_bs in nav_links:
                if len(nav_link_bs.find_all('a')) > 0:
                    nav_link = base + nav_link_bs.find_all('a')[0].get('href')
                    if nav_link_bs.text.isdigit():
                        nav_link_page_num = int(nav_link_bs.text)
                        if nav_link_page_num < current_page_num:
                            ## Add a previous page
                            if nav_link_page_num == current_page_num - 1:
                                link_to_previous_page = nav_link
                            else:
                                list_of_links_to_previous_pages.append(nav_link)

                        elif nav_link_page_num == current_page_num:
                            ## Add the current page
                            link_to_current_page = nav_link

                        elif nav_link_page_num > current_page_num:
                            ## Add a next page
                            if nav_link_page_num == current_page_num+1:
                                link_to_next_page = nav_link
                            else:
                                list_of_links_to_next_pages.append(nav_link)

            return (link_to_previous_page, list_of_links_to_previous_pages, link_to_current_page, list_of_links_to_next_pages, link_to_next_page)
        except Exception:
            return (None, None, None, None, None)


    def _parse_location(self, bs):
        try:
            return bs.find_all(id="swml_addr")[0].text.strip()
        except Exception:
            return None


    def __str__(self):
        out = ""
        current_url = ""
        start_offset = -1
        domain = ""
        protocol = ""
        results = []
        num_results = -1
        total_num_results_for_query = -1
        query_retrieval_time_in_seconds = -1.0
        link_to_previous_page = ""
        links_to_previous_pages = []
        links_to_next_pages = []
        link_to_next_page = ""
        location = ""




