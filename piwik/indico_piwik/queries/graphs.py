from base64 import b64encode

from . import PiwikQueryReportEventBase


class PiwikQueryReportEventGraphBase(PiwikQueryReportEventBase):
    """Base Piwik query for retrieving PNG graphs"""

    def call(self, apiModule, apiAction, height=None, width=None, graphType='verticalBar', **query_params):
        if height is not None:
            query_params['height'] = height
        if width is not None:
            query_params['width'] = width
        return super(PiwikQueryReportEventGraphBase, self).call(method='ImageGraph.get',
                                                                apiModule=apiModule, apiAction=apiAction,
                                                                aliasedGraph='1', graphType=graphType, **query_params)

    def get_result(self):
        """Perform the call and return the graph data

        :return: Encoded PNG graph data string to be inserted in a `src`
                 atribute of a HTML img tag.
        """
        img_prefix = 'data:image/png;base64,'
        png = self.call(default_response='none')
        if png == 'none':
            return png
        img_code = b64encode(png)
        return img_prefix + img_code


class PiwikQueryReportEventGraphCountries(PiwikQueryReportEventGraphBase):
    def call(self, **query_params):
        return super(PiwikQueryReportEventGraphCountries, self).call(apiModule='UserCountry', apiAction='getCountry',
                                                                     period='range', width=490, height=260,
                                                                     graphType='horizontalBar', **query_params)


class PiwikQueryReportEventGraphDevices(PiwikQueryReportEventGraphBase):
    def call(self, **query_params):
        return super(PiwikQueryReportEventGraphDevices, self).call(apiModule='UserSettings', apiAction='getOS',
                                                                   period='range', width=320, height=260,
                                                                   graphType='horizontalBar', **query_params)
