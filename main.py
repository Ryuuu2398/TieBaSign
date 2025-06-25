# -*- coding:utf-8 -*-
import os
import requests
import hashlib
import time
import copy
import logging
import random
import html

import smtplib
from email.mime.text import MIMEText


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API_URL
LIKIE_URL = "http://c.tieba.baidu.com/c/f/forum/like"
TBS_URL = "http://tieba.baidu.com/dc/common/tbs"
SIGN_URL = "http://c.tieba.baidu.com/c/c/forum/sign"

ENV = os.environ

HEADERS = {
    'Host': 'tieba.baidu.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
}
SIGN_DATA = {
    '_client_type': '2',
    '_client_version': '9.7.8.0',
    '_phone_imei': '000000000000000',
    'model': 'MI+5',
    "net_type": "1",
}

# VARIABLE NAME
COOKIE = "Cookie"
BDUSS = "BDUSS"
EQUAL = r'='
EMPTY_STR = r''
TBS = 'tbs'
PAGE_NO = 'page_no'
ONE = '1'
TIMESTAMP = "timestamp"
DATA = 'data'
FID = 'fid'
SIGN_KEY = 'tiebaclient!!!'
UTF8 = "utf-8"
SIGN = "sign"
KW = "kw"

s = requests.Session()

class UserReport:
    """用户签到报告类"""
    def __init__(self, user_index):
        self.user_index = user_index  # 用户序号
        self.success_list = []       # 成功列表
        self.failed_list = []        # 失败列表（现在存储字典）
        self.total_bars = 0          # 总贴吧数量
        self.start_time = time.time() # 开始时间
        self.end_time = 0             # 结束时间
        
    def add_success(self, bar):
        """添加成功签到"""
        self.success_list.append(bar)
        
    def add_failed(self, bar, error_code, error_msg):
        """添加失败签到并记录错误信息"""
        self.failed_list.append({
            'bar': bar,
            'error_code': error_code,
            'error_msg': error_msg
        })
        
    def set_total(self, total):
        """设置总贴吧数量"""
        self.total_bars = total
        
    def complete(self):
        """标记完成"""
        self.end_time = time.time()
        
    def get_duration(self):
        """获取签到耗时"""
        return round(self.end_time - self.start_time, 2)
        
    def get_report(self):
        """获取报告字典"""
        return {
            "user_index": self.user_index,
            "success": self.success_list,
            "failed": self.failed_list,  # 现在包含错误信息
            "total": self.total_bars,
            "success_count": len(self.success_list),
            "failed_count": len(self.failed_list),
            "duration": self.get_duration()
        }


def get_tbs(bduss):
    logger.info("获取tbs开始")
    headers = copy.copy(HEADERS)
    headers.update({COOKIE: EMPTY_STR.join([BDUSS, EQUAL, bduss])})
    try:
        tbs = s.get(url=TBS_URL, headers=headers, timeout=5).json()[TBS]
    except Exception as e:
        logger.error("获取tbs出错" + str(e))
        logger.info("重新获取tbs开始")
        tbs = s.get(url=TBS_URL, headers=headers, timeout=5).json()[TBS]
    logger.info("获取tbs结束")
    return tbs


def get_favorite(bduss):
    logger.info("获取关注的贴吧开始")
    # 客户端关注的贴吧
    returnData = {}
    i = 1
    data = {
        'BDUSS': bduss,
        '_client_type': '2',
        '_client_id': 'wappc_1534235498291_488',
        '_client_version': '9.7.8.0',
        '_phone_imei': '000000000000000',
        'from': '1008621y',
        'page_no': '1',
        'page_size': '200',
        'model': 'MI+5',
        'net_type': '1',
        'timestamp': str(int(time.time())),
        'vcode_tag': '11',
    }
    data = encodeData(data)
    try:
        res = s.post(url=LIKIE_URL, data=data, timeout=5).json()
    except Exception as e:
        logger.error("获取关注的贴吧出错" + str(e))
        return []
    logger.info("成功获取关注的贴吧第1页")
    returnData = res
    if 'forum_list' not in returnData:
        returnData['forum_list'] = []
    if res['forum_list'] == []:
        logger.error("获取关注的贴吧失败，未发现任何贴吧")
        return {'gconforum': [], 'non-gconforum': []}
    if 'non-gconforum' not in returnData['forum_list']:
        returnData['forum_list']['non-gconforum'] = []
    if 'gconforum' not in returnData['forum_list']:
        returnData['forum_list']['gconforum'] = []
    while 'has_more' in res and res['has_more'] == '1':
        i = i + 1
        data = {
            'BDUSS': bduss,
            '_client_type': '2',
            '_client_id': 'wappc_1534235498291_488',
            '_client_version': '9.7.8.0',
            '_phone_imei': '000000000000000',
            'from': '1008621y',
            'page_no': str(i),
            'page_size': '200',
            'model': 'MI+5',
            'net_type': '1',
            'timestamp': str(int(time.time())),
            'vcode_tag': '11',
        }
        data = encodeData(data)
        try:
            res = s.post(url=LIKIE_URL, data=data, timeout=5).json()
        except Exception as e:
            logger.error("获取关注的贴吧出错" + str(e))
            continue
        logger.info("成功获取关注的贴吧第{}页".format(i))
        if 'forum_list' not in res:
            continue
        if 'non-gconforum' in res['forum_list']:
            returnData['forum_list']['non-gconforum'].append(res['forum_list']['non-gconforum'])
        if 'gconforum' in res['forum_list']:
            returnData['forum_list']['gconforum'].append(res['forum_list']['gconforum'])

    t = []
    for i in returnData['forum_list']['non-gconforum']:
        if isinstance(i, list):
            for j in i:
                if isinstance(j, list):
                    for k in j:
                        t.append(k)
                else:
                    t.append(j)
        else:
            t.append(i)
    for i in returnData['forum_list']['gconforum']:
        if isinstance(i, list):
            for j in i:
                if isinstance(j, list):
                    for k in j:
                        t.append(k)
                else:
                    t.append(j)
        else:
            t.append(i)
    logger.info("获取关注的贴吧结束，共{}个贴吧".format(len(t)))
    return t


def encodeData(data):
    s = EMPTY_STR
    keys = data.keys()
    for i in sorted(keys):
        s += i + EQUAL + str(data[i])
    sign = hashlib.md5((s + SIGN_KEY).encode(UTF8)).hexdigest().upper()
    data.update({SIGN: str(sign)})
    return data


def client_sign(bduss, tbs, fid, kw):
    # 客户端签到
    logger.debug("开始签到贴吧：" + kw)
    data = copy.copy(SIGN_DATA)
    data.update({BDUSS: bduss, FID: fid, KW: kw, TBS: tbs, TIMESTAMP: str(int(time.time()))})
    data = encodeData(data)
    try:
        res = s.post(url=SIGN_URL, data=data, timeout=5).json()
    except Exception as e:
        logger.error("签到失败" + str(e))
        return {'error_code': 'network_error', 'error_msg': str(e)}
    return res

def send_summary_email(user_reports):
    """发送汇总邮件报告"""
    if ('HOST' not in ENV or 'FROM' not in ENV or 'TO' not in ENV or 'AUTH' not in ENV):
        logger.error("未配置邮箱")
        return
        
    HOST = ENV['HOST']
    FROM = ENV['FROM']
    TO = ENV['TO'].split('#')
    AUTH = ENV['AUTH']
    
    # 计算总体统计
    total_users = len(user_reports)
    total_bars = sum(report.total_bars for report in user_reports)
    total_success = sum(len(report.success_list) for report in user_reports)
    total_failed = sum(len(report.failed_list) for report in user_reports)
    success_rate = round(total_success / total_bars * 100, 2) if total_bars > 0 else 0
    
    # 邮件主题
    date_str = time.strftime('%Y-%m-%d', time.localtime())
    subject = f"百度贴吧自动签到汇总报告 ({date_str}) - {total_users}用户 {total_bars}贴吧 成功率:{success_rate}%"
    
    # 构建HTML邮件内容
    body = """
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #4a86e8;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .summary {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .user-report {
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
            background-color: #ffffff;
        }
        .user-header {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #1a73e8;
        }
        .section {
            margin-bottom: 15px;
        }
        .section-title {
            font-weight: bold;
            margin-bottom: 5px;
            color: #5f6368;
        }
        .success-bar, .failed-bar {
            padding: 5px 10px;
            margin: 2px;
            border-radius: 3px;
            display: inline-block;
        }
        .success-bar {
            background-color: #e6f4ea;
            border: 1px solid #34a853;
            color: #34a853;
        }
        .failed-bar {
            background-color: #fce8e6;
            border: 1px solid #ea4335;
            color: #ea4335;
        }
        .stats {
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
            font-size: 14px;
        }
        .stat-item {
            padding: 5px 10px;
            border-radius: 3px;
        }
        .success-stat {
            background-color: #e6f4ea;
            color: #34a853;
        }
        .failed-stat {
            background-color: #fce8e6;
            color: #ea4335;
        }
        .time-stat {
            background-color: #e8f0fe;
            color: #1a73e8;
        }
        hr {
            border: 0;
            height: 1px;
            background: #e0e0e0;
            margin: 20px 0;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            color: #70757a;
            font-size: 12px;
        }
        .error-details {
            font-size: 12px;
            color: #777;
            margin-left: 10px;
        }
    </style>
    </head>
    <body>
    """
    
    # 添加标题和总体摘要
    body += f"""
    <div class="header">
        <h2>百度贴吧自动签到汇总报告</h2>
        <div>日期: {date_str}</div>
    </div>
    
    <div class="summary">
        <div class="section">
            <div class="section-title">总体统计</div>
            <div>用户数量: {total_users}</div>
            <div>贴吧总数: {total_bars}</div>
            <div>签到成功: <span style="color:#34a853">{total_success}</span></div>
            <div>签到失败: <span style="color:#ea4335">{total_failed}</span></div>
            <div>成功率: <span style="color:#1a73e8">{success_rate}%</span></div>
        </div>
    </div>
    """
    
    # 添加每个用户的报告
    for report in user_reports:
        user_data = report.get_report()
        body += f"""
        <div class="user-report">
            <div class="user-header">用户 #{user_data['user_index']+1} 签到报告</div>
            
            <div class="stats">
                <div class="stat-item success-stat">成功: {user_data['success_count']}</div>
                <div class="stat-item failed-stat">失败: {user_data['failed_count']}</div>
                <div class="stat-item time-stat">耗时: {user_data['duration']}秒</div>
            </div>
            
            <div class="section">
                <div class="section-title">签到成功的贴吧 ({user_data['success_count']})</div>
                <div>
        """
        
        # 添加成功的贴吧
        for bar in user_data['success']:
            body += f"<span class='success-bar'>{bar['name']}</span>"
        
        body += f"""
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">签到失败的贴吧 ({user_data['failed_count']})</div>
                <div>
        """
        
        # 添加失败的贴吧
        for item in user_data['failed']:
            bar_name = item['bar']['name']
            error_code = item['error_code']
            error_msg = html.escape(item['error_msg'])  # 转义HTML特殊字符
            body += f"""
            <div style="margin-bottom: 5px;">
                <span class='failed-bar'>{bar_name}</span>
                <span class="error-details">(错误代码: {error_code}, 原因: {error_msg})</span>
            </div>
            """
        
        body += """
                </div>
            </div>
        </div>
        """
    
    # 添加页脚
    body += f"""
    <hr>
    <div class="footer">
        百度贴吧自动签到服务 | 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}
    </div>
    </body>
    </html>
    """
    
    # 创建邮件
    msg = MIMEText(body, 'html', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = FROM
    msg['To'] = ", ".join(TO)
    
    try:
        # 建立 SMTP、SSL 连接
        smtp = smtplib.SMTP_SSL(HOST, 465)
        # 登录邮箱账号
        smtp.login(FROM, AUTH)
        # 发送邮件
        smtp.sendmail(FROM, TO, msg.as_string())
        logger.info('汇总邮件发送成功')
        smtp.quit()
    except Exception as e:
        logger.error('发送汇总邮件失败: ' + str(e))

def main():
    if ('BDUSS' not in ENV):
        logger.error("未配置BDUSS")
        return
    
    BDUSS_LIST = ENV['BDUSS'].split('#')
    all_user_reports = []  # 存储所有用户的报告
    
    for user_index, bduss in enumerate(BDUSS_LIST):
        logger.info(f"开始签到第{user_index+1}个用户 (共{len(BDUSS_LIST)}个用户)")
        user_report = UserReport(user_index)  # 创建用户报告
        
        try:
            tbs = get_tbs(bduss)
            favorites = get_favorite(bduss)
            user_report.set_total(len(favorites))
            
            follow = copy.copy(favorites)
            
            for t in range(3):  # 最多重试3次
                current_failed = []   # 存储本轮失败的贴吧
                for bar in follow:
                    time.sleep(random.randint(1, 3))  # 减少等待时间
                    res = client_sign(bduss, tbs, bar["id"], bar["name"])
                    error_code = res.get('error_code')
                    error_msg = res.get('error_msg')
                    
                    if error_code == '0':
                        user_report.add_success(bar)
                        logger.info(f"{bar['name']}: 签到成功({error_code}) - {error_msg}")
                    elif error_code == '160002':  # 已经签过
                        user_report.add_success(bar)
                        logger.info(f"{bar['name']}: 签到成功({error_code}) - {error_msg}")
                    elif error_code == '340006':  # 贴吧被封禁
                        user_report.add_failed(bar, error_code, error_msg)
                        logger.info(f"{bar['name']}: 签到失败({error_code}) - {error_msg}")
                    else:
                        current_failed.append(bar)
                        logger.error(f"{bar['name']}: 签到失败({error_code}) - {error_msg}")
                
                if not current_failed:
                    logger.info(f"第{user_index+1}个用户所有贴吧签到完成")
                    break
                
                logger.warning(f"第{user_index+1}个用户有{len(current_failed)}个贴吧签到失败，准备重试 (第{t+1}次重试)")
                follow = copy.copy(current_failed)
                time.sleep(random.randint(300, 600))
                tbs = get_tbs(bduss)  # 重新获取tbs
            
            # 重试后仍然失败的贴吧
            for bar in current_failed:
                res = client_sign(bduss, tbs, bar["id"], bar["name"])
                error_code = res.get('error_code') or 'unknown'
                error_msg = res.get('error_msg') or '未知错误'
                user_report.add_failed(bar, error_code, error_msg)
                logger.error(f"重试后仍失败: {bar['name']} (错误代码: {error_code}, 原因: {error_msg})")
            
            user_report.complete()
            
            # 记录用户报告
            all_user_reports.append(user_report)
            logger.info(f"完成第{user_index+1}个用户签到: 成功{user_report.get_report()['success_count']}个, 失败{user_report.get_report()['failed_count']}个, 耗时{user_report.get_duration()}秒")
        
        except Exception as e:
            logger.error(f"处理第{user_index+1}个用户时发生错误: {str(e)}")
            # 即使出错也添加到报告
            user_report.complete()
            all_user_reports.append(user_report)
    
    # 所有用户签到完成后发送汇总报告
    logger.info(f"所有用户签到完成，共{len(all_user_reports)}个用户")
    send_summary_email(all_user_reports)
    logger.info("程序执行完毕")

if __name__ == '__main__':
    main()
