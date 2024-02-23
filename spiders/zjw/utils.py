def uri_params(params, spider):
    return {**params, "location":getattr(spider, "location", "")}