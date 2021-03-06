"""
classes responsible for obtaining results from the Event Registry
"""
import os, sys, urllib2, urllib, json, datetime, time, re;
from cookielib import CookieJar

mainLangs = ["eng", "deu", "zho", "slv", "spa"]
allLangs = [ "eng", "deu", "spa", "cat", "por", "ita", "fra", "rus", "ara", "tur", "zho", "slv", "hrv", "srp" ]
conceptTypes = ["loc", "person", "org", "keyword", "wiki", "concept-class", "topic-page"]


invalidCharRe = re.compile(r"[\x00-\x08]|\x0b|\x0c|\x0e|\x0f|[\x10-\x19]|[\x1a-\x1f]", re.IGNORECASE)
def removeInvalidChars(text):
    return invalidCharRe.sub("", text);


class Struct(object):
    """
    general class for converting dict to a native python object
    instead of a["b"]["c"] we can write a.b.c
    """
    def __init__(self, data):
        for name, value in data.iteritems():
            setattr(self, name, self._wrap(value))

    def _wrap(self, value):
        if isinstance(value, (tuple, list, set, frozenset)): 
            return type(value)([self._wrap(v) for v in value])
        else:
            return Struct(value) if isinstance(value, dict) else value

def createStructFromDict(data):
    """
    method to convert a list or dict to a native python object
    """
    if isinstance(data, list):
        return type(data)([createStructFromDict(v) for v in data])
    else:
        return Struct(data)

class Query(object):
    def __init__(self):
        self.queryParams = {};
        self.resultTypeList = [];
       
    # set the objects property propName if the propName key exists in dict and it is not the same as default value defVal         
    def _setQueryParamIfNotDefault(self, propName, dict, defVal):
        val = dict.pop(propName, defVal)
        if val != defVal:
            self.queryParams[propName] = val

    # add value value to key propName in queryParams dict - if key does not exist yet in the dict, create it first
    def _addQueryParamArray(self, propName, value):
        if not self.queryParams.has_key(propName):
            self.queryParams[propName] = []
        self.queryParams[propName].append(value)

    def clearRequestedResults(self):
        self.resultTypeList = [];

    # encode the request. if the username and pass are also provided then add also them to the request parameters
    def _encode(self, erUsername = None, erPassword = None):
        self._updateQueryParamsWithResultTypes();
        if erUsername != None and erPassword != None:
            self.queryParams["erUsername"] = erUsername;
            self.queryParams["erPassword"] = erPassword;
        return urllib.urlencode(self.queryParams, True);

    def _updateQueryParamsWithResultTypes(self):
        if len(self.resultTypeList) == 0:
            raise ValueError("The query does not have any result type specified. No sense in performing such a query");
        for request in self.resultTypeList:
            self.queryParams.update(request.__dict__);
        self.queryParams["resultType"] = [request.__dict__["resultType"] for request in self.resultTypeList];


class RequestBase(object):
    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)

    # set the objects property propName if the dictKey key exists in dict and it is not the same as default value defVal
    def _setPropIfNotDefault(self, propName, dict, dictKey, defVal):
        val = dict.pop(dictKey, defVal)
        if val != defVal:
            self.__dict__[propName] = val
    
    # parse the info that should be returned about an article    
    def _parseArticleFlags(self, prefix, **kwargs):
        self._setPropIfNotDefault(prefix + "IncludeArticleBasicInfo", kwargs, "includeArticleBasicInfo", True);
        self._setPropIfNotDefault(prefix + "IncludeArticleBody", kwargs, "includeArticleBody", True);
        self._setPropIfNotDefault(prefix + "IncludeArticleTitle", kwargs, "includeArticleTitle", True);
        self._setPropIfNotDefault(prefix + "IncludeArticleConcepts", kwargs, "includeArticleConcepts", False);
        self._setPropIfNotDefault(prefix + "IncludeArticleSourceInfo", kwargs, "includeArticleSourceInfo", True);
        self._setPropIfNotDefault(prefix + "IncludeArticleEventUri", kwargs, "includeArticleEventUri", True);
        self._setPropIfNotDefault(prefix + "IncludeArticleStoryUri", kwargs, "includeArticleStoryUri", False);
        self._setPropIfNotDefault(prefix + "IncludeArticleDuplicateList", kwargs, "includeArticleDuplicateList", False);
        self._setPropIfNotDefault(prefix + "IncludeArticleOriginalArticleInfo", kwargs, "includeArticleOriginalArticleInfo", False);
        self._setPropIfNotDefault(prefix + "IncludeArticleCategories", kwargs, "includeArticleCategories", False);
        self._setPropIfNotDefault(prefix + "IncludeArticleLocation", kwargs, "includeArticleLocation", False);
        self._setPropIfNotDefault(prefix + "IncludeArticleImage", kwargs, "includeArticleImage", False);
        self._setPropIfNotDefault(prefix + "IncludeArticleExtractedDates", kwargs, "includeArticleExtractedDates", False);
        self._setPropIfNotDefault(prefix + "IncludeArticleDetails", kwargs, "includeArticleDetails", False);

    # parse the info that should be returned about the concepts
    def _parseConceptFlags(self, prefix, **kwargs):
        self._setPropIfNotDefault(prefix + "IncludeConceptImage", kwargs, "includeConceptImage", False);
        self._setPropIfNotDefault(prefix + "IncludeConceptDescription", kwargs, "includeConceptDescription", False);
        self._setPropIfNotDefault(prefix + "IncludeConceptTrends", kwargs, "includeConceptTrends", False);
        self._setPropIfNotDefault(prefix + "IncludeConceptLocationInfo", kwargs, "includeConceptLocationInfo", False);
        self._setPropIfNotDefault(prefix + "IncludeConceptDetails", kwargs, "includeConceptDetails", False);
        
    # parse the info that should be returned about a news source    
    def _parseSourceFlags(self, prefix, **kwargs):
        self._setPropIfNotDefault(prefix + "IncludeSourceTitle", kwargs, "includeSourceTitle", True);
        self._setPropIfNotDefault(prefix + "IncludeSourceDescription", kwargs, "includeSourceDescription", False);
        self._setPropIfNotDefault(prefix + "IncludeSourceTags", kwargs, "includeSourceTags", False);
        self._setPropIfNotDefault(prefix + "IncludeSourceLocation", kwargs, "includeSourceLocation", False);
        self._setPropIfNotDefault(prefix + "IncludeSourceImportance", kwargs, "includeSourceImportance", False);
        self._setPropIfNotDefault(prefix + "IncludeSourceArticleCount", kwargs, "includeSourceArticleCount", False);
        self._setPropIfNotDefault(prefix + "IncludeSourceDetails", kwargs, "includeSourceDetails", False);

    # parse the info that should be returned about an event
    def _parseEventFlags(self, prefix, **kwargs):
        self._setPropIfNotDefault(prefix + "IncludeEventArticleCounts", kwargs, "includeEventArticleCounts", True);
        self._setPropIfNotDefault(prefix + "IncludeEventConcepts", kwargs, "includeEventConcepts", True);
        self._setPropIfNotDefault(prefix + "IncludeEventMultiLingInfo", kwargs, "includeEventMultiLingInfo", True);
        self._setPropIfNotDefault(prefix + "IncludeEventCategories", kwargs, "includeEventCategories", True);
        self._setPropIfNotDefault(prefix + "IncludeEventLocation", kwargs, "includeEventLocation", True);
        self._setPropIfNotDefault(prefix + "IncludeEventStories", kwargs, "includeEventStories", False);
        self._setPropIfNotDefault(prefix + "IncludeEventImages", kwargs, "includeEventImages", False);
        
    # parse the info that should be returned about a story
    def _parseStoryFlags(self, prefix, **kwargs):
        self._setPropIfNotDefault(prefix + "IncludeStoryBasicStats", kwargs, "includeStoryBasicStats", True);
        self._setPropIfNotDefault(prefix + "IncludeStoryCategory", kwargs, "includeStoryCategory", True);
        self._setPropIfNotDefault(prefix + "IncludeStoryLocation", kwargs, "includeStoryLocation", True);
        self._setPropIfNotDefault(prefix + "IncludeStoryDate", kwargs, "includeStoryDate", True);
        self._setPropIfNotDefault(prefix + "IncludeStoryConcepts", kwargs, "includeStoryConcepts", False);
        self._setPropIfNotDefault(prefix + "IncludeStoryTitle", kwargs, "includeStoryTitle", False);
        self._setPropIfNotDefault(prefix + "IncludeStorySummary", kwargs, "includeStorySummary", False);
        self._setPropIfNotDefault(prefix + "IncludeStoryMedoidArticle", kwargs, "includeStoryMedoidArticle", False);
        self._setPropIfNotDefault(prefix + "IncludeStoryExtractedDates", kwargs, "includeStoryExtractedDates", False);


# query class for searching for events in the event registry 
class QueryEvents(Query):
    def __init__(self,  **kwargs):
        super(QueryEvents, self).__init__();
        
        self.queryParams["action"] = "getEvents";

        self._setQueryParamIfNotDefault("keywords", kwargs, "");          # e.g. "bla bla"
        self._setQueryParamIfNotDefault("conceptUri", kwargs, []);      # e.g. ["http://en.wikipedia.org/wiki/Barack_Obama"]
        self._setQueryParamIfNotDefault("lang", kwargs, []);                  # eng, deu, spa, zho, slv, ...
        self._setQueryParamIfNotDefault("publisherUri", kwargs, []);    # ["www.bbc.co.uk"]
        self._setQueryParamIfNotDefault("locationUri", kwargs, []);    # ["http://en.wikipedia.org/wiki/Ljubljana"]
        self._setQueryParamIfNotDefault("categoryUri", kwargs, []);    # ["http://www.dmoz.org/Science/Astronomy"]
        self._setQueryParamIfNotDefault("categoryIncludeSub", kwargs, True);
        self._setQueryParamIfNotDefault("dateStart", kwargs, "");    # 2014-05-02
        self._setQueryParamIfNotDefault("dateEnd", kwargs, "");        # 2014-05-02
        if kwargs.has_key("minArticlesInEvent"):
            self.queryParams["minArticlesInEvent"] = kwargs["minArticlesInEvent"];
        if kwargs.has_key("maxArticlesInEvent"):
            self.queryParams["maxArticlesInEvent"] = kwargs["maxArticlesInEvent"];
        if kwargs.has_key("dateMentionStart"):
            self.queryParams["dateMentionStart"] = kwargs["dateMentionStart"];  # 2014-05-02
        if kwargs.has_key("dateMentionEnd"):
            self.queryParams["dateMentionEnd"] = kwargs["dateMentionEnd"];      # 2014-05-02

        self._setQueryParamIfNotDefault("ignoreKeywords", kwargs, "");
        self._setQueryParamIfNotDefault("ignoreConceptUri", kwargs, []);
        self._setQueryParamIfNotDefault("ignoreLang", kwargs, []);
        self._setQueryParamIfNotDefault("ignoreLocationUri", kwargs, []);
        self._setQueryParamIfNotDefault("ignorePublisherUri", kwargs, []);
        self._setQueryParamIfNotDefault("ignoreCategoryUri", kwargs, []);
        self._setQueryParamIfNotDefault("ignoreCategoryIncludeSub", kwargs, True);
        

    def _getPath(self):
        return "/json/event";

    def addConcept(self, conceptUri):
        self._addQueryParamArray("conceptUri", conceptUri);

    def addLocation(self, locationUri):
        self._addQueryParamArray("locationUri", locationUri);
        
    def addCategory(self, categoryUri):
        self._addQueryParamArray("categoryUri", categoryUri)

    def addNewsSource(self, newsSourceUri):
        self._addQueryParamArray("publisherUri", newsSourceUri)

    def addKeyword(self, keyword):
        self.queryParams["keywords"] = self.queryParams.pop("keywords", "") + " " + keyword;

    # set a custom list of event uris. the results will be then computed on this list - no query will be done
    def setEventUriList(self, uriList):
        self.queryParams = { "action": "getEvents", "eventUriList": ",".join(uriList) };

    def setDateLimit(self, startDate, endDate):
        if isinstance(startDate, datetime.date):
            self.queryParams["dateStart"] = startDate.isoformat()
        elif isinstance(startDate, datetime.datetime):
            self.queryParams["dateStart"] = startDate.date().isoformat()
        elif isinstance(startDate, str):
            self.queryParams["dateStart"] = startDate
        elif self.queryParams.has_key("dateStart"):
            del self.queryParams["dateStart"]

        if isinstance(endDate, datetime.date):
            self.queryParams["dateEnd"] = endDate.isoformat()
        elif isinstance(endDate, datetime.datetime):
            self.queryParams["dateEnd"] = endDate.date().isoformat()
        elif isinstance(endDate, str):
            self.queryParams["dateEnd"] = endDate
        elif self.queryParams.has_key("dateEnd"):
            del self.queryParams["dateEnd"]
            
    # what info does one want to get as a result of the query
    def addRequestedResult(self, requestEvents):
        if not isinstance(requestEvents, RequestEvents):
            raise AssertionError("QueryEvents class can only accept result requests that are of type RequestEvents");
        self.resultTypeList.append(requestEvents);


# query class for searching for events in the event registry 
class QueryEvent(Query):
    def __init__(self, eventUriOrList, **kwargs):
        super(QueryEvent, self).__init__();
        
        self.queryParams["action"] = "getEvent";

        self.queryParams["eventUri"] = eventUriOrList;                      # a single event uri or a list of event uris
        
    def _getPath(self):
        return "/json/event";   

    # what info does one want to get as a result of the query
    def addRequestedResult(self, requestEvent):
        if not isinstance(requestEvent, RequestEvent):
            raise AssertionError("QueryEvent class can only accept result requests that are of type RequestEvent");
        self.resultTypeList.append(requestEvent);


# query class for searching for articles in the event registry 
class QueryArticles(Query):
    def __init__(self,  **kwargs):
        super(QueryArticles, self).__init__();
        self.queryParams["action"] = "getArticles";

        self._setQueryParamIfNotDefault("keywords", kwargs, "");          # e.g. "bla bla"
        self._setQueryParamIfNotDefault("conceptUri", kwargs, []);      # a single concept uri or a list (e.g. ["http://en.wikipedia.org/wiki/Barack_Obama"])
        self._setQueryParamIfNotDefault("lang", kwargs, []);                  # a single lang or list (possible: eng, deu, spa, zho, slv)
        self._setQueryParamIfNotDefault("publisherUri", kwargs, []);    # a single source uri or a list (e.g. ["www.bbc.co.uk"])
        self._setQueryParamIfNotDefault("locationUri", kwargs, []);    # a single location uri or a list (e.g. ["http://en.wikipedia.org/wiki/Ljubljana"])
        self._setQueryParamIfNotDefault("categoryUri", kwargs, []);    # a single category uri or a list (e.g. ["http://www.dmoz.org/Science/Astronomy"])
        self._setQueryParamIfNotDefault("categoryIncludeSub", kwargs, True);    # also include the subcategories for the given categories
        self._setQueryParamIfNotDefault("dateStart", kwargs, "");                # starting date of the published articles (e.g. 2014-05-02)
        self._setQueryParamIfNotDefault("dateEnd", kwargs, "");                    # ending date of the published articles (e.g. 2014-05-02)
        self._setQueryParamIfNotDefault("dateMentionStart", kwargs, "");  # first valid mentioned date detected in articles (e.g. 2014-05-02)
        self._setQueryParamIfNotDefault("dateMentionEnd", kwargs, "");      # last valid mentioned date detected in articles (e.g. 2014-05-02)

        self._setQueryParamIfNotDefault("ignoreKeywords", kwargs, "");
        self._setQueryParamIfNotDefault("ignoreConceptUri", kwargs, []);
        self._setQueryParamIfNotDefault("ignoreLang", kwargs, []);
        self._setQueryParamIfNotDefault("ignoreLocationUri", kwargs, []);
        self._setQueryParamIfNotDefault("ignorePublisherUri", kwargs, []);
        self._setQueryParamIfNotDefault("ignoreCategoryUri", kwargs, []);
        self._setQueryParamIfNotDefault("ignoreCategoryIncludeSub", kwargs, True);
        
    def _getPath(self):
        return "/json/article";
    
    def addConcept(self, conceptUri):
        self._addQueryParamArray("conceptUri", conceptUri);

    def addLocation(self, locationUri):
        self._addQueryParamArray("locationUri", locationUri);

    def addCategory(self, categoryUri):
        self._addQueryParamArray("categoryUri", categoryUri)

    def addKeyword(self, keyword):
        self.queryParams["keywords"] = self.queryParams.pop("keywords", "") + " " + keyword;

    def setDateLimit(self, startDate, endDate):
        if isinstance(startDate, datetime.date):
            self.queryParams["dateStart"] = startDate.isoformat()
        elif isinstance(startDate, datetime.datetime):
            self.queryParams["dateStart"] = startDate.date().isoformat()
        elif isinstance(startDate, str):
            self.queryParams["dateStart"] = startDate
        elif self.queryParams.has_key("dateStart"):
            del self.queryParams["dateStart"]

        if isinstance(endDate, datetime.date):
            self.queryParams["dateEnd"] = endDate.isoformat()
        elif isinstance(endDate, datetime.datetime):
            self.queryParams["dateEnd"] = endDate.date().isoformat()
        elif isinstance(endDate, str):
            self.queryParams["dateEnd"] = endDate
        elif self.queryParams.has_key("dateEnd"):
            del self.queryParams["dateEnd"]

    def setDateMentionLimit(self, startDate, endDate):
        if isinstance(startDate, datetime.date):
            self.queryParams["dateMentionStart"] = startDate.isoformat()
        elif isinstance(startDate, datetime.datetime):
            self.queryParams["dateMentionStart"] = startDate.date().isoformat()
        elif isinstance(startDate, str):
            self.queryParams["dateMentionStart"] = startDate
        elif self.queryParams.has_key("dateMentionStart"):
            del self.queryParams["dateMentionStart"]

        if isinstance(endDate, datetime.date):
            self.queryParams["dateMentionEnd"] = endDate.isoformat()
        elif isinstance(endDate, datetime.datetime):
            self.queryParams["dateMentionEnd"] = endDate.date().isoformat()
        elif isinstance(endDate, str):
            self.queryParams["dateMentionEnd"] = endDate
        elif self.queryParams.has_key("dateMentionEnd"):
            del self.queryParams["dateMentionEnd"]

    # what info does one want to get as a result of the query
    def addRequestedResult(self, requestArticles):
        if not isinstance(requestArticles, RequestArticles):
            raise AssertionError("QueryArticles class can only accept result requests that are of type RequestArticles");
        self.resultTypeList.append(requestArticles);

    # set a custom list of article ids. the results will be then computed on this list - no query will be done
    def setArticleIdList(self, idList):
        self.queryParams = { "action": "getArticles", "articleIdList": ",".join([str(val) for val in idList])};
                       

# class for finding all available info for one or more articles in the event registry 
class QueryArticle(Query):
    def __init__(self, articleUriOrUriList):
        super(QueryArticle, self).__init__();
        self.queryParams["articleUri"] = articleUriOrUriList;      # a single article uri or a list of article uris
        self.queryParams["action"] = "getArticle";
       
    @staticmethod
    def queryById(articleIdOrIdList):
        q = QueryArticle([])
        q.queryParams["articleId"] = articleIdOrIdList
        return q

    @staticmethod
    def queryByUrl(articleUrlOrUrlList):
        q = QueryArticle([])
        q.queryParams["articleUrl"] = articleUrlOrUrlList
        return q

    def _getPath(self):
        return "/json/article";   

    # what info does one want to get as a result of the query
    def addRequestedResult(self, requestArticle):
        if not isinstance(requestArticle, RequestArticle):
            raise AssertionError("QueryArticle class can only accept result requests that are of type RequestArticle");
        self.resultTypeList.append(requestArticle);


# #####################################
# #####################################
class RequestEvent(RequestBase):
    def __init__(self):
        self.resultType = None;
        
# return a list of event details
class RequestEventInfo(RequestEvent):
    def __init__(self, conceptLang = ["eng"], conceptTypes = ["person", "org", "loc", "wiki"],
                 # what info about the event to return:
                 **kwargs):
        self.infoConceptLang = conceptLang      # in which language should be the labels of concepts in the event
        self.infoConceptType = conceptTypes     # which types of concepts to return for the event

        self._parseEventFlags("info", **kwargs);
        self._parseStoryFlags("info", **kwargs);
        self._parseConceptFlags("info", **kwargs);
                
        self.resultType = "info"

# return a list of articles
class RequestEventArticles(RequestEvent):
    def __init__(self, page = 0, count = 20, lang = mainLangs, bodyLen = 200, sortBy = "cosSim", sortByAsc = False, conceptLang = ["eng"], conceptTypes = ["person", "org", "loc", "wiki"],      # what info about the articles to include:
            **kwargs):
        assert count <= 200
        self.articlesLang = lang                # return articles in specified language(s)
        self.articlesPage = page                # page of the articles
        self.articlesCount = count              # number of articles to return
        self.articlesSortBy = sortBy            # how are the event articles sorted (date, id, cosSim, fq)
        self.articlesSortByAsc = sortByAsc      
        self.articlesBodyLen = bodyLen              # length of the body to return (-1 for whole article)
        self.articlesConceptLang = conceptLang      # in which language should be the labels of concepts in the articles
        self.articlesConceptType = conceptTypes     # which types of concepts to return for each article

        self._parseArticleFlags("articles", **kwargs);
        self._parseConceptFlags("articles", **kwargs);
        self._parseSourceFlags("articles", **kwargs);

        self.resultType = "articles"

# return a list of article uris
class RequestEventArticleUris(RequestEvent):
    def __init__(self, lang = mainLangs, sortBy = "cosSim", sortByAsc = False):
        self.articleUrisLang = lang
        self.articleUrisSortBy = sortBy          # none, id, date, cosSim, fq
        self.articleUrisSortByAsc = sortByAsc
        self.resultType = "articleUris"

# get keyword aggregate of articles in the event
class RequestEventKeywordAggr(RequestEvent):
    def __init__(self, eventSampleSize = 500):
        assert eventSampleSize <= 1000
        self.keywordAggrSampleSize = eventSampleSize
        self.resultType = "keywordAggr"

# get source distribution of articles in the event
class RequestEventSourceAggr(RequestEvent):
    def __init__(self):
        self.resultType = "sourceAggr"

# get distribution of date mentions found in the event articles
class RequestEventDateMentionAggr(RequestEvent):
    def __init__(self):
        self.resultType = "dateMentionAggr"
        
# get trending information for the articles about the event
class RequestEventArticleTrend(RequestEvent):
    def __init__(self, lang = mainLangs, minArticleCosSim = -1, bodyLen = 0, conceptLang = ["eng"], conceptTypes = ["person", "org", "loc", "wiki"], **kwargs):
        self.articleTrendLang = lang
        self.articleTrendMinArticleCosSim = minArticleCosSim;

        self.articleTrendBodyLen = bodyLen              # length of the body to return (-1 for whole article)
        self.articleTrendConceptLang = conceptLang      # in which language should be the labels of concepts in the articles
        self.articleTrendConceptType = conceptTypes     # which types of concepts to return for each article
        
        self._parseArticleFlags("articleTrend", **kwargs);
        self._parseConceptFlags("articleTrend", **kwargs);
        self._parseSourceFlags("articleTrend", **kwargs);

        self.resultType = "articleTrend"

# get information about similar events
class RequestEventSimilarEvents(RequestEvent):
    def __init__(self, count = 20, source = "concept", maxDayDiff = sys.maxint, conceptLang = ["eng"], conceptTypes = ["person", "org", "loc", "wiki"], addArticleTrendInfo = False, similarEventsAggrHours = 6, includeSelf = False,
                 # which info about events to include:
                 **kwargs):
        assert count <= 200
        self.similarEventsCount = count                 # number of similar events to return
        self.similarEventsConceptLang = conceptLang     # in which language(s) should be the labels of the concepts
        self.similarEventsConceptType = conceptTypes    # which concept types to use when computing similarity (relevant when source == "concept")
        self.similarEventsSource = source               # concept, cca - how to compute similarity
        self.similarEventsMaxDayDiff = maxDayDiff       # what is the maximum time difference between the similar events and this one
        
        self.similarEventsAddArticleTrendInfo = addArticleTrendInfo     # add info how the articles in the similar events are distributed over time
        self.similarEventsAggrHours = aggrHours                         # if similarEventsAddArticleTrendInfo == True then this is the aggregating window

        self.similarEventsIncludeSelf = includeSelf                     # should the info about the event itself be included among the results

        self._parseEventFlags("similarEvents", **kwargs);
        self._parseStoryFlags("similarEvents", **kwargs);
        self._parseConceptFlags("similarEvents", **kwargs);

        self.resultType = "similarEvents"

# get information about similar stories (clusters)
class RequestEventSimilarStories(RequestEvent):
    def __init__(self, count = 20, source = "concept", lang = ["eng"], maxDayDiff = sys.maxint, conceptLang = ["eng"], conceptTypes = ["person", "org", "loc", "wiki"],
                 # which info about stories to include:
                 **kwargs):
        assert count <= 200
        self.similarStoriesCount = count                # number of similar stories to return
        self.similarStoriesLang = lang                  # in which language should be the stories
        self.similarStoriesConceptLang = conceptLang    # in which language(s) should be the labels of the concepts
        self.similarStoriesConceptType = conceptTypes   # which concept types to use when computing similarity (relevant when source == "concept")
        self.similarStoriesSource = source               # concept, cca - how to compute similarity
        self.similarStoriesMaxDayDiff = maxDayDiff       # what is the maximum time difference between the similar stories and this one

        self._parseStoryFlags("similarStories", **kwargs);
        self._parseConceptFlags("similarStories", **kwargs);

        self.resultType = "similarEvents"

# #####################################
# #####################################
class RequestArticle(RequestBase):
    def __init__(self):
        self.resultType = None;

# return a list of event details
class RequestArticleInfo(RequestArticle):
    def __init__(self, bodyLen = -1, conceptLang = ["eng"], conceptTypes = ["person", "org", "loc", "wiki"], 
                 # what info about the article to include:
                 **kwargs):
        self.infoBodyLen = bodyLen
        self.infoConceptLang = conceptLang      # in which language should be the labels of concepts in the article
        self.infoConceptType = conceptTypes     # which types of concepts to return for the article
                
        self._parseArticleFlags("info", **kwargs);
        self._parseConceptFlags("info", **kwargs);
        self._parseSourceFlags("info", **kwargs);
                        
        self.resultType = "info"


# return a list of similar articles based on the CCA
class RequestArticleSimilarArticles(RequestArticle):
    def __init__(self, page = 0, count = 20, lang = ["eng"], limitPerLang = -1, bodyLen = -1, sortBy = "cosSim", sortByAsc = False, conceptLang = ["eng"], conceptTypes = ["person", "org", "loc", "wiki"], 
                 # what info about the article to include:
                 **kwargs):
        assert count <= 200
        self.similarArticlesPage = page                 # page of the articles
        self.similarArticlesCount = count               # number of articles to return
        self.similarArticlesLimitPerLang = limitPerLang # max number of articles per language to return (-1 for no limit)
        self.similarArticlesLang = lang                 # in which language(s) should be the similar articles
        self.similarArticlesSortBy = sortBy             # how are the event articles sorted (date, id, cosSim, fq)
        self.similarArticlesSortByAsc = sortByAsc      
        
        self.similarArticlesBodyLen = bodyLen              # length of the body to return (-1 for whole article)
        self.similarArticlesConceptLang = conceptLang      # in which language should be the labels of concepts in the articles
        self.similarArticlesConceptType = conceptTypes     # which types of concepts to return for each article

        self._parseArticleFlags("similarArticles", **kwargs);
        self._parseConceptFlags("similarArticles", **kwargs);
        self._parseSourceFlags("similarArticles", **kwargs);
        
        self.resultType = "similarArticles"
        

# return a list of duplicated articles of the current article
class RequestArticleDuplicatedArticles(RequestArticle):
    def __init__(self, page = 0, count = 20, bodyLen = -1, sortBy = "cosSim", sortByAsc = False, conceptLang = ["eng"], conceptTypes = ["person", "org", "loc", "wiki"], 
                 # what info about the article to include:
                 **kwargs):
        self.duplicatedArticlesPage = page                 # page of the articles
        self.duplicatedArticlesCount = count               # number of articles to return
        self.duplicatedArticlesSortBy = sortBy             # how are the event articles sorted (date, id)
        self.duplicatedArticlesSortByAsc = sortByAsc      
        
        self.duplicatedArticlesBodyLen = bodyLen              # length of the body to return (-1 for whole article)
        self.duplicatedArticlesConceptLang = conceptLang      # in which language should be the labels of concepts in the articles
        self.duplicatedArticlesConceptType = conceptTypes     # which types of concepts to return for each article

        self._parseArticleFlags("duplicatedArticles", **kwargs);
        self._parseConceptFlags("duplicatedArticles", **kwargs);
        self._parseSourceFlags("duplicatedArticles", **kwargs);
        
        self.resultType = "duplicatedArticles"


# return the article that is the original of the given article (the current article is a duplicate)
class RequestArticleOriginalArticle(RequestArticle):
    def __init__(self, bodyLen = -1, sortBy = "cosSim", sortByAsc = False, conceptLang = ["eng"], conceptTypes = ["person", "org", "loc", "wiki"], 
                 # what info about the article to include:
                 **kwargs):
        self._parseArticleFlags("originalArticle", **kwargs);
        self._parseConceptFlags("originalArticle", **kwargs);
        self._parseSourceFlags("originalArticle", **kwargs);

        self.resultType = "originalArticle"


# #####################################
# #####################################
class RequestEvents(RequestBase):
    def __init__(self):
        self.resultType = None;

# return a list of event details
class RequestEventsInfo(RequestEvents):
    def __init__(self, page = 0, count = 20, sortBy = "date", sortByAsc = False, conceptLang = ["eng"], conceptTypes = ["person", "org", "loc", "wiki"], 
                 # what info about events to include:
                 **kwargs):
        assert count <= 200
        self.eventsPage = page
        self.eventsCount = count
        self.eventsSortBy = sortBy          # date, size, rel
        self.eventsSortByAsc = sortByAsc
        self.eventsConceptLang = conceptLang
        self.eventsConceptType = conceptTypes

        self._parseEventFlags("events", **kwargs);
        self._parseStoryFlags("events", **kwargs);
        self._parseConceptFlags("events", **kwargs);
        
        self.resultType = "events"

    def setPage(self, page):
        self.eventsPage = page

    def setCount(self, count):
        self.eventsCount = count

# return a list of event uris
class RequestEventsUriList(RequestEvents):
    def __init__(self):
        self.resultType = "uriList"

        # get time distribution of resulting events
class RequestEventsTimeAggr(RequestEvents):
    def __init__(self):
        self.resultType = "timeAggr"

# get keyword aggregate of resulting events
class RequestEventsKeywordAggr(RequestEvents):
    def __init__(self, lang = "eng"):
        self.keywordAggrLang = lang;
        self.resultType = "keywordAggr"

# get aggreate of locations of resulting events
class RequestEventsLocAggr(RequestEvents):
    def __init__(self, conceptLangs = ["eng"]):
        self.locAggrConceptLang = conceptLangs
        self.resultType = "locAggr"

# get aggreate of locations and times of resulting events
class RequestEventsLocTimeAggr(RequestEvents):
    def __init__(self, conceptLangs = ["eng"]):
        self.locTimeAggrConceptLang = conceptLangs
        self.resultType = "locTimeAggr"

# list of top publishers that report about events that are among the results
class RequestEventsTopPublisherAggr(RequestEvents):
    def __init__(self, topPublisherCount = 20, includePublisherDetails = True):
        assert topPublisherCount <= 200
        self.topPublisherAggrTopPublisherCount = topPublisherCount
        self.topPublisherAggrIncludePublisherDetails = includePublisherDetails
        self.resultType = "topPublisherAggr"

# get aggregated list of concepts - top concepts that appear in events 
class RequestEventsConceptAggr(RequestEvents):
    def __init__(self, conceptCount = 20, conceptTypes = ["person", "org", "loc", "wiki"], conceptLangs = ["eng"], **kwargs):
        assert conceptCount <= 200
        self.conceptAggrConceptType = conceptTypes
        self.conceptAggrConceptCount = conceptCount
        self.conceptAggrConceptLang = conceptLangs
        
        self._parseConceptFlags("conceptAggr", **kwargs)
        
        self.resultType = "conceptAggr"

# get a graph of concepts - connect concepts that are frequently in the same events
class RequestEventsConceptGraph(RequestEvents):
    def __init__(self, conceptCount = 25, conceptTypes = ["person", "org", "loc", "wiki"], conceptLangs = ["eng"], linkCount = 50, eventsSampleSize = 500, **kwargs):
        assert conceptCount <= 1000
        assert linkCount <= 2000
        assert eventsSampleSize <= 20000
        self.conceptGraphConceptType = conceptTypes
        self.conceptGraphConceptCount = conceptCount
        self.conceptGraphConceptLang = conceptLangs
        self.conceptGraphLinkCount = linkCount
        self.conceptGraphSampleSize = eventsSampleSize
        
        self._parseConceptFlags("conceptGraph", **kwargs)

        self.resultType = "conceptGraph"

# get a matrix of concepts and their dependencies
class RequestEventsConceptMatrix(RequestEvents):
    def __init__(self, conceptCount = 25, conceptTypes = ["person", "org", "loc", "wiki"], conceptLangs = ["eng"], measure = "pmi", eventsSampleSize = 500, **kwargs):
        assert conceptCount <= 200
        assert eventsSampleSize <= 10000
        self.conceptMatrixConceptType = conceptTypes
        self.conceptMatrixConceptCount = conceptCount
        self.conceptMatrixConceptLang = conceptLangs
        self.conceptMatrixMeasure = measure
        self.conceptMatrixSampleSize = eventsSampleSize

        self._parseConceptFlags("conceptMatrix", **kwargs)

        self.resultType = "conceptMatrix"

# get a list of top trending concepts and their daily trends over time
class RequestEventsConceptTrends(RequestEvents):
    def __init__(self, conceptCount = 10, conceptTypes = ["person", "org", "loc", "wiki"], conceptLangs = ["eng"], **kwargs):
        assert conceptCount <= 50
        self.trendingConceptsConceptType = conceptTypes
        self.trendingConceptsConceptCount = conceptCount
        self.trendingConceptsConceptLang = conceptLangs

        self._parseConceptFlags("conceptTrends", **kwargs)

        self.resultType = "conceptTrends"

# get events and the dates they mention
class RequestEventsDateMentionAggr(RequestEvents):
    def __init__(self, minDaysApart = 0, minDateMentionCount = 5):
        self.dateMentionAggrMinDateMentionCount = minDateMentionCount
        self.dateMentionAggrMinDaysApart = minDaysApart
        self.resultType = "dateMentionAggr"

# get hierarchical clustering of events into smaller clusters.
class RequestEventsEventClusters(RequestEvents):
    def __init__(self, keywordCount = 30, conceptLangs = ["eng"], maxEventsToCluster = 10000):
        assert keywordCount <= 100
        assert maxEventsToCluster <= 10000
        self.eventClustersKeywordCount = keywordCount
        self.eventClustersConceptLang = conceptLangs
        self.eventClustersMaxEventsToCluster = maxEventsToCluster
        self.resultType = "eventClusters"

# get distribution of events into dmoz categories
class RequestEventsCategoryAggr(RequestEvents):
    def __init__(self):
        self.resultType = "categoryAggr"

# get list of recently changed events
class RequestEventsRecentActivity(RequestEvents):
    def __init__(self, maxEventCount = 60, maxMinsBack = 10 * 60, lastEventActivityId = 0, lang = "eng", eventsWithLocationOnly = True, eventsWithLangOnly = False, minAvgCosSim = 0, **kwargs):
        assert maxEventCount <= 1000
        self.eventsRecentActivityMaxEventCount = maxEventCount
        self.eventsRecentActivityMaxMinsBack = maxMinsBack
        self.eventsRecentActivityLastEventActivityId = lastEventActivityId
        self.eventsRecentActivityEventLang = lang                                   # the language in which title should be returned
        self.eventsRecentActivityEventsWithLocationOnly = eventsWithLocationOnly    # return only events for which we've recognized their location
        self.eventsRecentActivityEventsWithLangOnly = eventsWithLangOnly            # return only event that have a cluster at least in the lang language
        self.eventsRecentActivityMinAvgCosSim = minAvgCosSim                        # the minimum avg cos sim of the events to be returned (events with lower quality should not be included)

        self._parseEventFlags("events", **kwargs);
        self._parseStoryFlags("events", **kwargs);
        self._parseConceptFlags("events", **kwargs);

        self.resultType = "recentActivity"


# #####################################
# #####################################
class RequestArticles(RequestBase):
    def __init__(self):
        self.resultType = None;

# return a list of event details
class RequestArticlesInfo(RequestArticles):
    # possible sorting values: date, id, cosSim, fq
    def __init__(self, page = 0, count = 20, sortBy = "date", sortByAsc = False, conceptLang = ["eng"], conceptTypes = ["person", "org", "loc", "wiki"], bodyLen = 300, 
                 # what info about articles to return:
                 **kwargs):
        assert count <= 200
        self.articlesPage = page
        self.articlesCount = count
        self.articlesSortBy = sortBy        # date, id, cosSim, fq
        self.articlesSortByAsc = sortByAsc
        self.articlesBodyLen = bodyLen;
        self.articlesConceptLang = conceptLang
        self.articlesConceptTypes = conceptTypes
        
        self._parseArticleFlags("articles", **kwargs);
        self._parseConceptFlags("articles", **kwargs);
        self._parseSourceFlags("articles", **kwargs);
                
        self.resultType = "articles"

    def setPage(self, page):
        self.articlesPage = page

    def setCount(self, count):
        self.articlesCount = count
        
# return a list of article uris
class RequestArticlesUriList(RequestArticles):
    def __init__(self):
        self.resultType = "uriList"

# return a list of article ids
class RequestArticlesIdList(RequestArticles):
    def __init__(self):
        self.resultType = "articleIds"

# get time distribution of resulting articles
class RequestArticlesTimeAggr(RequestArticles):
    def __init__(self):
        self.resultType = "timeAggr"

# get aggreate of categories of resulting articles
class RequestArticlesCategoryAggr(RequestArticles):
    def __init__(self, articlesSampleSize = 20000):
        assert articlesSampleSize <= 50000
        self.categoryAggrSampleSize = articlesSampleSize
        self.resultType = "categoryAggr"

# get aggreate of concepts of resulting articles
class RequestArticlesConceptAggr(RequestArticles):
    def __init__(self, conceptLang = ["eng"], conceptTypes = ["person", "org", "loc", "wiki"], conceptCount = 25, articlesSampleSize = 1000, **kwargs):
        assert conceptCount <= 500
        assert articlesSampleSize <= 10000
        self.conceptAggrConceptLang = conceptLang
        self.conceptAggrConceptType = conceptTypes
        self.conceptAggrConceptCount = conceptCount
        self.conceptAggrSampleSize = articlesSampleSize  
        
        self._parseConceptFlags("conceptAggr", **kwargs);
              
        self.resultType = "conceptAggr"

# get aggreate of sources of resulting articles
class RequestArticlesSourceAggr(RequestArticles):
    def __init__(self, **kwargs):
        self._parseSourceFlags("sourceAggr", **kwargs);
        self.resultType = "sourceAggr"

# get aggreate of sources of resulting articles
class RequestArticlesKeywordAggr(RequestArticles):
    def __init__(self, lang = "eng", articlesSampleSize = 500):
        assert articlesSampleSize <= 1000
        self.keywordAggrLang = articlesSampleSize
        self.resultType = "keywordAggr"
        
# get aggreate of sources of resulting articles
class RequestArticlesConceptMatrix(RequestArticles):
    def __init__(self, count = 25, conceptTypes = ["person", "org", "loc", "wiki"], conceptLang = ["eng"], measure = "pmi", sampleSize = 500, **kwargs):
        assert count <= 200
        assert sampleSize <= 10000
        self.conceptMatrixConceptCount = count
        self.conceptMatrixConceptLang = conceptLang
        self.conceptMatrixConceptType = conceptTypes
        self.conceptMatrixSampleSize = sampleSize
        self.conceptMatrixMeasure = measure             # pmi (pointwise mutual information), pairTfIdf (pair frequence * IDF of individual concepts), chiSquare

        self._parseConceptFlags("conceptMatrix", **kwargs);

        self.resultType = "conceptMatrix"

# get concept graph of resulting articles
class RequestArticlesConceptGraph(RequestArticles):
    def __init__(self, count = 25, conceptTypes = ["person", "org", "loc", "wiki"], conceptLang = ["eng"], linkCount = 50, sampleSize = 500, **kwargs):
        assert count <= 1000
        assert linkCount <= 2000
        assert sampleSize <= 20000
        self.conceptGraphConceptCount = count
        self.conceptGraphConceptLang = conceptLang
        self.conceptGraphConceptType = conceptTypes
        self.conceptGraphSampleSize = sampleSize
        self.conceptGraphLinkCount = linkCount

        self._parseConceptFlags("conceptGraph", **kwargs);

        self.resultType = "conceptGraph"

# get trending of concepts in the resulting articles
class RequestArticlesConceptTrends(RequestArticles):
    def __init__(self, count = 25, conceptLang = ["eng"]):
        assert count <= 50
        self.trendingConceptsConceptCount = count
        self.trendingConceptsConceptLang = conceptLang

        self._parseConceptFlags("conceptTrends", **kwargs);

        self.resultType = "conceptTrends"

# get mentioned dates in the articles
class RequestArticlesDateMentionAggr(RequestArticles):
    def __init__(self):
        self.resultType = "dateMentionAggr"

# get the list of articles that were added recently
class RequestArticlesRecentActivity(RequestArticles):
    def __init__(self, maxArticleCount = 60, maxMinsBack = 10 * 60, lastArticleActivityId = 0, articlesWithLocationOnly = True, **kwargs):
        assert maxArticleCount <= 1000
        self.articleRecentActivityMaxArticleCount  = maxArticleCount
        self.articleRecentActivityMaxMinsBack = maxMinsBack
        self.articleRecentActivityLastArticleActivityId  = lastArticleActivityId
        self.articleRecentActivityArticlesWithLocationOnly  = articlesWithLocationOnly

        self._parseArticleFlags("recentActivity", **kwargs);
        self._parseConceptFlags("recentActivity", **kwargs);
        self._parseSourceFlags("recentActivity", **kwargs);

        self.resultType = "recentActivity"
        
# #####################################
# #####################################

# object that can access event registry 
class EventRegistry(object):
    def __init__(self, host = "http://eventregistry.org", logging = False, 
                 minDelayBetweenRequests = 0.5,     # the minimum number of seconds between individual api calls
                 repeatFailedRequestCount = -1):    # if a request fails (for example, because ER is down), what is the max number of times the request should be repeated (-1 for indefinitely)
        self.Host = host
        self._lastException = None
        self._logRequests = logging
        self._erUsername = None
        self._erPassword = None
        self._minDelayBetweenRequests = minDelayBetweenRequests
        self._repeatFailedRequestCount = repeatFailedRequestCount
        self._lastQueryTime = time.time()

        cj = CookieJar()
        self._reqOpener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

        # if there is a settings.json file in the directory then try using it to login to ER
        currPath = os.path.split(__file__)[0]
        if os.path.join(currPath, "settings.json"):
            settings = json.load(open(os.path.join(currPath, "settings.json")))
            self.login(settings.get("username", ""), settings.get("password", ""), False)
        
    # ensure that queries are not made too fast
    def _sleepIfNecessary(self):
        t = time.time();
        if t - self._lastQueryTime < self._minDelayBetweenRequests:
            time.sleep(self._minDelayBetweenRequests - (t - self._lastQueryTime))
        self._lastQueryTime = t

     # make the request - repeat it _repeatFailedRequestCount times, if they fail (indefinitely if _repeatFailedRequestCount = -1)
    def _getUrlResponse(self, url, data = None):
        tryCount = 0
        while self._repeatFailedRequestCount < 0 or tryCount < self._repeatFailedRequestCount:
            tryCount += 1
            try:
                req = urllib2.Request(url, data)
                respInfo = self._reqOpener.open(req).read()
                return respInfo
            except Exception as ex:
                self._lastException = ex
                print(ex)
                time.sleep(5)   # sleep for 5 seconds on error
        return None

    def setLogging(val):
        self._logRequests = val

    def getLastException(self):
        return self._lastException

    def printLastException(self):
        print str(self._lastException)

    # login the user. without logging in, the user is limited to 10.000 queries per day. 
    # if you have a registered account, the number of allowed requests per day can be higher, depending on your subscription plan
    def login(self, username, password, throwExceptOnFailure = True):
        self._erUsername = username
        self._erPassword = password
        req = urllib2.Request(self.Host + "/login", urllib.urlencode({ "email": username, "pass": password }))
        respInfo = self._reqOpener.open(req).read()
        respInfo = json.loads(respInfo);
        if throwExceptOnFailure and respInfo.has_key("error"):
            raise Exception(respInfo["error"]);
        return respInfo;

    # make a get request
    def jsonRequest(self, methodUrl, paramDict):
        self._sleepIfNecessary();
        self._lastException = None

        # add user credentials if specified
        if self._erUsername != None and self._erPassword != None:
            paramDict["erUsername"] = self._erUsername
            paramDict["erPassword"] = self._erPassword
        
        try:
            params = urllib.urlencode(paramDict, True)
            url = self.Host + methodUrl + "?" + params
            if self._logRequests:
                with open("requests_log.txt", "a") as log:
                    log.write(url + "\n")
            # make the request
            respInfo = self._getUrlResponse(url)
            if respInfo != None:
                respInfo = json.loads(respInfo)
            return respInfo
        except Exception as ex:
            self._lastException = ex;
            return None

    # make a post request where all parameters are encoded in the body - use for requests with many parameters
    def jsonPostRequest(self, methodUrl, paramDict):
        self._sleepIfNecessary();
        self._lastException = None

        # add user credentials if specified
        if self._erUsername != None and self._erPassword != None:
            paramDict["erUsername"] = self._erUsername
            paramDict["erPassword"] = self._erPassword
        
        try:
            params = urllib.urlencode(paramDict, True)
            url = self.Host + methodUrl
            if self._logRequests:
                with open("requests_log.txt", "a") as log:
                    log.write(url + "\n")
            # make the request
            respInfo = self._getUrlResponse(url, params)
            if respInfo != None:
                respInfo = json.loads(respInfo)
            return respInfo
        except Exception as ex:
            self._lastException = ex;
            return None
            
    # main method for executing the search queries. 
    def execQuery(self, query, convertToDict = True):
        self._sleepIfNecessary();
        self._lastException = None

        try:
            params = query._encode(self._erUsername, self._erPassword)
            url = self.Host + query._getPath() + "?" + params
            if self._logRequests:
                with open("requests_log.txt", "a") as log:
                    log.write(url + "\n")
            # make the request
            respInfo = self._getUrlResponse(url)
            if respInfo != None and convertToDict:
                respInfo = json.loads(respInfo)
            return respInfo
        except Exception as ex:
            self._lastException = ex
            return None

    # return a list of concepts that contain the given prefix
    # valid sources: person, loc, org, wiki, entities (== person + loc + org), concepts (== entities + wiki), conceptClass, conceptFolder
    # fullLocInfo determines if you wish to see as label "city, country" or just "city"
    def suggestConcepts(self, prefix, sources = ["concepts"], lang = "eng", labelLang = "eng", page = 0, count = 20, fullLocInfo = False):      
        return self.jsonRequest("/json/suggestConcepts", { "prefix": prefix, "source": sources, "lang": lang, "labelLang": labelLang, "page": page, "count": count, "fullLocInfo": fullLocInfo })
        
    # return a list of news sources that match the prefix
    def suggestNewsSources(self, prefix, page = 0, count = 20):
        return self.jsonRequest("/json/suggestSources", { "prefix": prefix, "page": page, "count": count })
        
    # return a list of locations (cities or countries) that contain the prefix
    def suggestLocations(self, prefix, count = 20, lang = "eng", source = ["city", "country"]):
        return self.jsonRequest("/json/suggestLocations", { "prefix": prefix, "count": count, "source": source, "lang": lang })
        
    # return a list of dmoz categories that contain the prefix
    def suggestCategories(self, prefix, page = 0, count = 20):
        return self.jsonRequest("/json/suggestCategories", { "prefix": prefix, "page": page, "count": count })

    # return a list of dmoz categories that contain the prefix
    def suggestConceptClasses(self, prefix, lang = "eng", labelLang = "eng", page = 0, count = 20):
        return self.jsonRequest("/json/suggestConceptClasses", { "prefix": prefix, "lang": lang, "labelLang": labelLang, "page": page, "count": count })
        
    # return a concept uri that is the best match for the given concept label
    def getConceptUri(self, conceptLabel, lang = "eng", sources = ["concepts"]):
        matches = self.suggestConcepts(conceptLabel, lang = lang, sources = sources)
        if matches != None and len(matches) > 0 and matches[0].has_key("uri"):
            return matches[0]["uri"]
        return None

    # return a location uri that is the best match for the given location label
    def getLocationUri(self, locationLabel, lang = "eng"):
        matches = self.suggestConcepts(locationLabel, sources = ["loc"], lang = lang, fullLocInfo = True);
        if matches != None and len(matches) > 0 and matches[0].has_key("uri"):
            return matches[0]["uri"]
        return None;

    # return a category uri that is the best match for the given label
    def getCategoryUri(self, categoryLabel):
        matches = self.suggestCategories(categoryLabel);
        if matches != None and len(matches) > 0 and matches[0].has_key("uri"):
            return matches[0]["uri"]
        return None;

    # return the news source that best matches the source name
    def getNewsSourceUri(self, sourceName):
        matches = self.suggestNewsSources(sourceName);
        if matches != None and len(matches) > 0 and matches[0].has_key("uri"):
            return matches[0]["uri"]
        return None;
    
    # return a uri of the concept class that is the best match for the given label
    def getConceptClass(self, classLabel, lang = "eng"):
        matches = self.suggestConceptClasses(classLabel, lang = lang)
        if matches != None and len(matches) > 0 and matches[0].has_key("uri"):
            return matches[0]["uri"]
        return None    

    ### return info about recently modified events
    # maxEventCount determines the maximum number of events to return in a single call (max 250)
    # maxMinsBack sets how much in the history are we interested to look
    # set mandatoryLang if you wish to only get events covered at least by the specified language
    # if mandatoryLocation == True then return only events that have a known geographic location
    # lastActivityId is another way of settings how much in the history are we interested to look. Set when you have repeated calls of the method. Set it to lastActivityId obtained in the last response
    def getRecentEvents(self, maxEventCount = 60, maxMinsBack = 10 * 60, mandatoryLang = None, mandatoryLocation = True, lastActivityId = 0, **kwargs):
        assert maxEventCount <= 1000
        params = {  "action": "getRecentActivity",
                    "addEvents": True,
                    "addArticles": False,
                    "recentActivityEventsMaxEventCount": maxEventCount,             # max number of returned events
                    "recentActivityEventsMaxMinsBack": maxMinsBack,
                    "recentActivityEventsMandatoryLocation": mandatoryLocation,     # return only events that have a known geo location
                    "recentActivityEventsLastActivityId": lastActivityId       # one criteria for telling the system about what was the latest activity already received (obtained by previous calls to this method)
                  }
        # return only events that have at least a story in the specified language
        if mandatoryLang != None:
            params["recentActivityEventsMandatoryLang"] = mandatoryLang;

        req = RequestBase(**params)
        req._parseEventFlags("recentActivityEvents", **kwargs);
        req._parseStoryFlags("recentActivityEvents", **kwargs);
        req._parseConceptFlags("recentActivityEvents", **kwargs);
        
        return self.jsonRequest("/json/overview", req.__dict__)

    ### return info about recently added articles
    # maxArticleCount determines the maximum number of articles to return in a single call (max 250)
    # maxMinsBack sets how much in the history are we interested to look
    # if mandatorySourceLocation == True then return only articles from sources for which we know geographic location
    # lastActivityId is another way of settings how much in the history are we interested to look. Set when you have repeated calls of the method. Set it to lastActivityId obtained in the last response
    def getRecentArticles(self, maxArticleCount = 60, maxMinsBack = 10 * 60, mandatorySourceLocation = True, lastActivityId = 0, **kwargs):
        assert maxArticleCount <= 1000
        params = {
            "action": "getRecentActivity",
            "addEvents": False,
            "addArticles": True,
            "recentActivityArticlesMaxMinsBack": maxMinsBack,
            "recentActivityArticlesMaxArticleCount": maxArticleCount,                   # max number of returned events
            "recentActivityArticlesMandatorySourceLocation": mandatorySourceLocation,   # return only articles that have a known geo location
            "recentActivityArticlesLastActivityId": lastActivityId                      # one criteria for telling the system about what was the latest activity already received (obtained by previous calls to this method)
            }

        req = RequestBase(**params)
        req._parseArticleFlags("recentActivityArticles", **kwargs);
        req._parseSourceFlags("recentActivityArticles", **kwargs);
        
        return self.jsonRequest("/json/overview", req.__dict__)

    # get some stats about recently imported articles and events
    def getRecentStats(self):
        return self.jsonRequest("/json/overview", { "action": "getRecentStats"})
