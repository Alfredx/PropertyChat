# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ZjwShProjectItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    id = scrapy.Field() # id 网页上的id
    url = scrapy.Field() # 网址
    project_id = scrapy.Field() # 报建编号
    project_name = scrapy.Field() # 项目名称
    construction_unit = scrapy.Field() # 建设单位
    construction_location = scrapy.Field() # 建设地点
    total_investment = scrapy.Field() # 总投资(万元)
    project_category = scrapy.Field() # 项目分类
    area_in_plan = scrapy.Field() # 建设规模(建筑面积)
    # 报建受理部门
    permission_no = scrapy.Field() # 施工许可证号
    permission_issue_date = scrapy.Field() # 施工许可日期
    area = scrapy.Field() # 建设规模（建筑面积㎡）
    contract_duration = scrapy.Field() # 合同工期(日历天)
    completion_date = scrapy.Field() # 理论竣工日期
    contract_start_date = scrapy.Field() # 合同开工日期
    contract_completion_date = scrapy.Field() # 合同竣工日期
    pass
