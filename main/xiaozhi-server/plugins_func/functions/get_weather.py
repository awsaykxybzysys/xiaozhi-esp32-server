import requests
import json
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.utils.util import get_ip_info

TAG = __name__
logger = setup_logging()

GET_WEATHER_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": (
            "获取某个地点的实时天气信息，用户应提供一个位置，比如用户说西安天气，参数为：西安。"
            "如果用户说的是省份，默认用省会城市。如果用户说的不是省份或城市而是一个地名，默认用该地所在省份的省会城市。"
            "如果用户没有指明地点，说‘天气怎么样’，‘今天天气如何’，location参数为空"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "地点名，例如西安。可选参数，如果不提供则不传",
                },
                "lang": {
                    "type": "string",
                    "description": "返回用户使用的语言code，例如zh_CN/zh_HK/en_US/ja_JP等，默认zh_CN",
                },
            },
            "required": ["lang"],
        },
    },
}

# 天气代码映射表 - 基于和风天气API
WEATHER_CODE_MAP = {
    "100": "晴",
    "101": "多云",
    "102": "少云",
    "103": "晴间多云",
    "104": "阴",
    "150": "晴",
    "151": "多云",
    "152": "少云",
    "153": "晴间多云",
    "300": "阵雨",
    "301": "强阵雨",
    "302": "雷阵雨",
    "303": "强雷阵雨",
    "304": "雷阵雨伴有冰雹",
    "305": "小雨",
    "306": "中雨",
    "307": "大雨",
    "308": "极端降雨",
    "309": "毛毛雨/细雨",
    "310": "暴雨",
    "311": "大暴雨",
    "312": "特大暴雨",
    "313": "冻雨",
    "314": "小到中雨",
    "315": "中到大雨",
    "316": "大到暴雨",
    "317": "暴雨到大暴雨",
    "318": "大暴雨到特大暴雨",
    "350": "阵雨",
    "351": "强阵雨",
    "399": "雨",
    "400": "小雪",
    "401": "中雪",
    "402": "大雪",
    "403": "暴雪",
    "404": "雨夹雪",
    "405": "雨雪天气",
    "406": "阵雨夹雪",
    "407": "阵雪",
    "408": "小到中雪",
    "409": "中到大雪",
    "410": "大到暴雪",
    "456": "阵雨夹雪",
    "457": "阵雪",
    "499": "雪",
    "500": "薄雾",
    "501": "雾",
    "502": "霾",
    "503": "扬沙",
    "504": "浮尘",
    "507": "沙尘暴",
    "508": "强沙尘暴",
    "509": "浓雾",
    "510": "强浓雾",
    "511": "中度霾",
    "512": "重度霾",
    "513": "严重霾",
    "514": "大雾",
    "515": "特强浓雾",
    "900": "热",
    "901": "冷",
    "999": "未知",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    )
}


def get_city_location_id(location, api_key, api_host):
    """
    根据城市名称获取LocationID
    """
    # 尝试不同的API地址格式
    api_urls = [
        f"https://{api_host}/v2/city/lookup",
        f"https://{api_host}/geo/v2/city/lookup",  # 备用地址
    ]
    
    params = {
        "key": api_key,
        "location": location,
        "lang": "zh"
    }
    
    for url in api_urls:
        try:
            logger.bind(tag=TAG).info(f"尝试API地址: {url}")
            response = requests.get(url, params=params, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == "200" and data.get("location"):
                logger.bind(tag=TAG).info(f"成功获取城市ID: {data['location'][0]['id']}")
                return data["location"][0]["id"]
            else:
                logger.bind(tag=TAG).warning(f"API返回错误: {data.get('code', 'unknown')} - {data.get('message', '')}")
                
        except requests.RequestException as e:
            logger.bind(tag=TAG).warning(f"请求失败 {url}: {str(e)}")
            continue
    
    logger.bind(tag=TAG).error(f"所有API地址都失败，无法获取城市ID: {location}")
    return None


def get_current_weather(location_id, api_key, api_host, lang="zh"):
    """
    获取实时天气数据
    """
    # 尝试不同的API地址格式
    api_urls = [
        f"https://{api_host}/v7/weather/now",
        f"https://{api_host}/weather/now",  # 备用地址
    ]
    
    params = {
        "key": api_key,
        "location": location_id,
        "lang": lang,
        "unit": "m"  # 公制单位
    }
    
    for url in api_urls:
        try:
            logger.bind(tag=TAG).info(f"尝试天气API地址: {url}")
            response = requests.get(url, params=params, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == "200":
                logger.bind(tag=TAG).info("成功获取天气数据")
                return data
            else:
                logger.bind(tag=TAG).warning(f"天气API返回错误: {data.get('code', 'unknown')} - {data.get('message', '')}")
                
        except requests.RequestException as e:
            logger.bind(tag=TAG).warning(f"天气请求失败 {url}: {str(e)}")
            continue
    
    logger.bind(tag=TAG).error(f"所有天气API地址都失败，无法获取天气数据")
    return None


def format_weather_report(weather_data, city_name):
    """
    格式化天气报告
    """
    if not weather_data or not weather_data.get("now"):
        return "获取天气数据失败"
    
    now = weather_data["now"]
    
    # 获取天气描述
    weather_text = now.get("text", "未知")
    weather_icon = now.get("icon", "")
    
    # 构建天气报告
    report = f" {city_name}\n\n"
    report += f"当前天气: {weather_text}\n"
    report += f"温度: {now.get('temp', 'N/A')}°C\n"
    
    # 风向风力
    wind_dir = now.get("windDir", "")
    wind_scale = now.get("windScale", "")
    wind_speed = now.get("windSpeed", "")
    if wind_dir and wind_scale:
        report += f"风向风力: {wind_dir} {wind_scale}级\n"
    
    # 湿度
    humidity = now.get("humidity", "")
    if humidity:
        report += f"相对湿度: {humidity}%\n"
    
    # 大气压强
    pressure = now.get("pressure", "")
    if pressure:
        report += f"大气压强: {pressure}百帕\n"
    
    # 能见度
    visibility = now.get("vis", "")
    if visibility:
        report += f"能见度: {visibility}公里\n"
    
    # 降水量
    precip = now.get("precip", "")
    if precip and float(precip) > 0:
        report += f"过去1小时降水量: {precip}毫米\n"
    
    # 云量
    cloud = now.get("cloud", "")
    if cloud:
        report += f"云量: {cloud}%\n"
    
    # 露点温度
    dew = now.get("dew", "")
    if dew:
        report += f"露点温度: {dew}°C\n"
    
    # 数据更新时间
    obs_time = now.get("obsTime", "")
    if obs_time:
        report += f"\n数据观测时间: {obs_time}"
    
    return report


@register_function("get_weather", GET_WEATHER_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def get_weather(conn, location: str = None, lang: str = "zh_CN"):
    """
    获取天气信息的主函数
    """
    from core.utils.cache.manager import cache_manager, CacheType
    
    # 获取配置
    api_host = conn.config["plugins"]["get_weather"].get(
        "api_host", "devapi.qweather.com"
    )
    api_key = conn.config["plugins"]["get_weather"].get(
        "api_key", "537948a93841445ead850b2621ecf3df"
    )
    default_location = conn.config["plugins"]["get_weather"].get(
        "default_location", "北京"
    )
    client_ip = conn.client_ip
    
    # 确定查询位置
    if not location:
        # 通过客户端IP解析城市
        if client_ip:
            # 先从缓存获取IP对应的城市信息
            cached_ip_info = cache_manager.get(CacheType.IP_INFO, client_ip)
            if cached_ip_info:
                location = cached_ip_info.get("city")
            else:
                # 缓存未命中，调用API获取
                ip_info = get_ip_info(client_ip, logger)
                if ip_info:
                    cache_manager.set(CacheType.IP_INFO, client_ip, ip_info)
                    location = ip_info.get("city")
            
            if not location:
                location = default_location
        else:
            # 若无IP，使用默认位置
            location = default_location
    
    # 设置语言代码
    lang_code = "zh" if lang.startswith("zh") else "en"
    
    # 尝试从缓存获取天气报告
    weather_cache_key = f"qweather_{location}_{lang_code}"
    cached_weather_report = cache_manager.get(CacheType.WEATHER, weather_cache_key)
    if cached_weather_report:
        return ActionResponse(Action.REQLLM, cached_weather_report, None)
    
    # 获取城市LocationID
    location_id = get_city_location_id(location, api_key, api_host)
    if not location_id:
        return ActionResponse(
            Action.REQLLM, 
            f"未找到城市 '{location}' 的信息，请确认地点名称是否正确", 
            None
        )
    
    # 获取实时天气数据
    weather_data = get_current_weather(location_id, api_key, api_host, lang_code)
    if not weather_data:
        return ActionResponse(
            Action.REQLLM, 
            "获取天气数据失败，请稍后重试", 
            None
        )
    
    # 获取城市名称（从API返回数据中提取）
    city_name = location  # 使用用户输入的城市名
    if weather_data.get("location"):
        city_name = weather_data["location"].get("name", location)
    
    # 格式化天气报告
    weather_report = format_weather_report(weather_data, city_name)
    
    # 缓存天气报告（缓存10分钟）
    cache_manager.set(CacheType.WEATHER, weather_cache_key, weather_report, ttl=600)
    
    return ActionResponse(Action.REQLLM, weather_report, None)
