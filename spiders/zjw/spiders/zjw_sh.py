import json
import re
from typing import Iterable
from urllib.parse import urlparse
from copy import deepcopy

import arrow
import ddddocr
import scrapy
from bs4 import BeautifulSoup, ResultSet
from scrapy.http import Request, Response, FormRequest
from zjw.items import ZjwShProjectItem


class ZjwSh(scrapy.Spider):
    name = "ZjwSh"
    custom_settings = {
        "FEEDS": {
            "crawled_data/%(location)s.jsonl": {
                "format": "jsonlines",
                "encoding": "utf8",
                "item_classes": ["zjw.items.ZjwShProjectItem"],
                "overwrite": True
            }
        },
        "FEED_URI_PARAMS": "zjw.utils.uri_params"
    }

    def __init__(self, location, *args, **kwargs):
        super(ZjwSh, self).__init__(*args, **kwargs)
        self.crawled_urls = set()
        self.location = location
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
        self.cookies = {
            "wondersLog_zwdt_G_D_I": "1f580e54c482ba21e186645064ddff88-3603",
            "wondersLog_zwdt_sdk": """{"persistedTime":1707113286699,"updatedTime":1707113807944,"sessionStartTime":1707113286886,"sessionReferrer":"https://zwdt.sh.gov.cn/govPortals/municipalDepartments/SHJSSH","deviceId":"1f580e54c482ba21e186645064ddff88-3603","LASTEVENT":{"eventId":"办事指南浏览","time":1707113807944},"sessionUuid":9635270103677052,"costTime":{},"recommend_code":6059053712858958}""",
            "ASP.NET_SessionId": "lvolqmhi0nzj4knn4gqixqg1",
        }
        self.ocr = ddddocr.DdddOcr()
        self.post_param = {
            "__VIEWSTATE": "",
            "__VIEWSTATEGENERATOR": "",
            "__EVENTVALIDATION": "",
            "txtbjbh": "",
            "txtxmmc": "",
            "txtjsdw": "",
            "txtjsdd": self.location,
            "txtyzm": "",
            "btnSearch": "查询▶",
        }

    def start_requests(self) -> Iterable[Request]:
        return [
            Request("https://zjw.sh.gov.cn/jsgcxmbsjggscx/index.html",
                    headers=self.headers,
                    callback=self.initial_page)
        ]

    def initial_page(self, response: Response):
        return Request("https://ciac.zjw.sh.gov.cn/xmbjwsbsweb/xmquery/XmList.aspx",
                       headers=self.headers,
                       cookies=self.cookies,
                       callback=self.get_XmList)

    def get_XmList(self, response: Response):
        self.extract_post_param_from_response(response)
        return Request("https://ciac.zjw.sh.gov.cn/xmbjwsbsweb/xmquery/ValidatePic.aspx",
                    #    headers=self.headers,
                       callback=self.validate_pic)

    def validate_pic(self, response: Response):
        self.post_param["txtyzm"] = self.ocr.classification(response.body).strip()
        print(self.post_param)
        headers = deepcopy(self.headers)
        headers['Content-Type'] = "application/x-www-form-urlencoded"
        headers["Referer"] = "https://ciac.zjw.sh.gov.cn/xmbjwsbsweb/xmquery/XmList.aspx"
        return FormRequest("https://ciac.zjw.sh.gov.cn/xmbjwsbsweb/xmquery/XmList.aspx",
                       headers=headers,
                       cookies=self.cookies,
                       formdata=self.post_param,
                       dont_filter=True,
                       callback=self.list_projects)

    def list_projects(self, response: Response):
        self.extract_post_param_from_response(response)
        soup = BeautifulSoup(response.text, features="html.parser")
        gridtds: list[ResultSet] = soup.find_all("tr", {"class": "gridtd"})
        for gridtd in gridtds:
            onclick = gridtd.find_all("a")[0]['onclick']
            bjbh_id = onclick.replace(
                "openXmDetailWin('", "").replace("');", "")
            item = ZjwShProjectItem()
            item['id'] = bjbh_id
            item['url'] = f"https://ciac.zjw.sh.gov.cn/xmbjwsbsweb/xmquery/Xmxx.aspx?bjbh={bjbh_id}"
            yield Request(item['url'],
                          headers=self.headers,
                          callback=self.project_quote_detail,
                          meta={"item": item})
        #<span id="gvXmList_ctl04_lblPage">第2页/共2页</span>
        if tr_page_info := soup.find("tr", {"align":"right"}):
            if page_info := tr_page_info.find("span"):
                current_page, total_pages = page_info.text.split("/")
                current_page = int(current_page.replace("第","").replace("页",""))
                total_pages = int(total_pages.replace("共","").replace("页",""))
                print(current_page, total_pages)
                if current_page < total_pages:
                    post_param = deepcopy(self.post_param)
                    eventtarget = page_info['id'].split("_")[1]
                    post_param.update({
                        "__EVENTTARGET": f"gvXmList${eventtarget}$lbnNext",
                        "__EVENTARGUMENT": "",
                        f"gvXmList${eventtarget}$inPageNum": ""
                        })
                    headers = deepcopy(self.headers)
                    headers['Content-Type'] = "application/x-www-form-urlencoded"
                    headers["Referer"] = "https://ciac.zjw.sh.gov.cn/xmbjwsbsweb/xmquery/XmList.aspx"
                    del post_param['btnSearch']
                    yield FormRequest("https://ciac.zjw.sh.gov.cn/xmbjwsbsweb/xmquery/XmList.aspx",
                                headers=headers,
                                cookies=self.cookies,
                                formdata=post_param,
                                dont_filter=True,
                                callback=self.list_projects)

    def project_quote_detail(self, response: Response):
        quote_detail = self.extract_project_detail(response.text)
        item: ZjwShProjectItem = response.meta['item']
        item['project_name'] = quote_detail.get('项目名称', "")
        item['project_id'] = quote_detail.get('报建编号', "")
        item['construction_unit'] = quote_detail.get('建设单位', "")
        item['construction_location'] = quote_detail.get('建设地点', "")
        item['total_investment'] = quote_detail.get('总投资(万元)', "")
        item['project_category'] = quote_detail.get('项目分类', "")
        item['area_in_plan'] = quote_detail.get('建设规模(建筑面积)', "")
        yield Request(f"https://ciac.zjw.sh.gov.cn/xmbjwsbsweb/xmquery/Sgxkxx.aspx?bjbh={item['id']}",
                      headers=self.headers,
                      callback=self.project_permission_detail,
                      meta={"item": item})

    def project_permission_detail(self, response: Response):
        permission_detail = self.construction_permission(response.text)
        item: ZjwShProjectItem = response.meta['item']
        item['permission_no'] = permission_detail.get("施工许可证号", "")
        item['permission_issue_date'] = permission_detail.get("施工许可日期", "")
        item['area'] = permission_detail.get("建设规模（建筑面积㎡）", "")
        item['contract_duration'] = permission_detail.get("合同工期(日历天)", "")
        item['completion_date'] = permission_detail.get("理论竣工日期", "")
        item['contract_start_date'] = permission_detail.get("合同开工日期", "")
        item['contract_completion_date'] = permission_detail.get("合同竣工日期", "")
        yield item

    def construction_permission(self, html_content):
        soup = BeautifulSoup(html_content, features="html.parser")
        permission_detail = {}
        # 2015 or old or others?
        if format_version := soup.find("span", {"id": "lblsqsx"}):
            format_version = format_version.text
            if format_version == "2015版":
                if table := soup.find("table", {"class": "table"}):
                    if tr := table.find(lambda tag: tag.name == "tr" and "施工许可证号" in tag.text):
                        permission_detail['施工许可证号'] = tr.find(
                            'span', {"id": "Label2"}).text
                    if tr := table.find(lambda tag: tag.name == "tr" and "施工许可日期" in tag.text):
                        permission_detail['施工许可日期'] = tr.find(
                            'span', {"id": "Label3"}).text
                    if tr := table.find(lambda tag: tag.name == "tr" and "建设规模（建筑面积㎡）" in tag.text):
                        space_text = tr.find("span", {"id": "lblJsgm"}).text
                        reg = r'\d+(?:\.\d+)?'
                        if result := re.findall(reg, space_text):
                            permission_detail["建设规模（建筑面积㎡）"] = result[0]
                    if tr := table.find(lambda tag: tag.name == "tr" and "合同工期(日历天)" in tag.text):
                        permission_detail['合同工期(日历天)'] = tr.find(
                            "span", {"id": "lblhtgq"}).text
                        permission_detail['理论竣工日期'] = arrow.get(permission_detail['施工许可日期']).shift(
                            days=int(permission_detail['合同工期(日历天)'])).format("YYYY/MM/DD")
            elif format_version == "旧版":
                if table := soup.find("table", {"class": "table"}):
                    if tr := table.find(lambda tag: tag.name == "tr" and "施工许可证号" in tag.text):
                        permission_detail['施工许可证号'] = tr.find(
                            'span', {"id": "Label2"}).text
                    if tr := table.find(lambda tag: tag.name == "tr" and "施工许可日期" in tag.text):
                        permission_detail['施工许可日期'] = tr.find(
                            'span', {"id": "Label3"}).text
                    if tr := table.find(lambda tag: tag.name == "tr" and "建设规模（建筑面积㎡）" in tag.text):
                        space_text = tr.find("span", {"id": "lblJsgm"}).text
                        reg = r'\d+(?:\.\d+)?'
                        if result := re.findall(reg, space_text):
                            permission_detail["建设规模（建筑面积㎡）"] = result[0]
                    if tr := table.find(lambda tag: tag.name == "tr" and "合同竣工日期" in tag.text):
                        permission_detail['合同开工日期'] = tr.find(
                            "span", {"id": "Label5"}).text
                    if tr := table.find(lambda tag: tag.name == "tr" and "合同竣工日期" in tag.text):
                        permission_detail['合同竣工日期'] = tr.find(
                            "span", {"id": "Label6"}).text
                        duration = arrow.get(
                            permission_detail['合同竣工日期']) - arrow.get(permission_detail['合同开工日期'])
                        permission_detail['理论竣工日期'] = (
                            arrow.get(permission_detail['施工许可日期']) + duration).format("YYYY/MM/DD")
                pass
            else:
                raise ValueError(f"无法识别的版本：{format_version}")
        return permission_detail

    def extract_project_detail(self, html_content):
        soup = BeautifulSoup(html_content, features="html.parser")
        quote_detail = {}
        if table := soup.find("table", {"class": "table"}):
            if trs := table.find_all("tr"):
                for tr in trs:
                    if tds := tr.find_all("td"):
                        quote_detail[tds[0].text] = tds[1].text.strip()
        return quote_detail

    def extract_post_param_from_response(self, response: Response):
        soup = BeautifulSoup(response.text, "html.parser")
        self.post_param['__VIEWSTATE'] = soup.find(
            "input", {"id": "__VIEWSTATE"})['value']
        self.post_param['__VIEWSTATEGENERATOR'] = soup.find(
            "input", {"id": "__VIEWSTATEGENERATOR"})['value']
        self.post_param['__EVENTVALIDATION'] = soup.find(
            "input", {"id": "__EVENTVALIDATION"})['value']
